#!/usr/bin/env python3
"""Rebuild the complete Olist CSV snapshot as a read-only SQLite database.

Only published business records are imported. Entity Types, event definitions,
case mappings, SQL gold, and request labels are NOT added to the model input.
"""
from __future__ import annotations
import argparse
import csv
import gzip
import hashlib
import json
import shutil
import sqlite3
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "source" / "upstream_files.json"
TABLES = ["customers", "sellers", "products", "geolocation",
          "product_category_name_translation", "orders", "order_items",
          "order_payments", "order_reviews"]
PKEYS = {
    "customers": ["customer_id"],
    "sellers": ["seller_id"],
    "products": ["product_id"],
    "orders": ["order_id"],
    "order_items": ["order_id", "order_item_id"],
    "order_payments": ["order_id", "payment_sequential"],
    "product_category_name_translation": ["product_category_name"],
    # review_id is NOT guaranteed unique; geolocation zip prefix is not unique.
    "order_reviews": [],
    "geolocation": [],
}
FKEYS = {
    "orders": [(["customer_id"], "customers", ["customer_id"])],
    "order_items": [
        (["order_id"], "orders", ["order_id"]),
        (["product_id"], "products", ["product_id"]),
        (["seller_id"], "sellers", ["seller_id"]),
    ],
    "order_payments": [(["order_id"], "orders", ["order_id"])],
    "order_reviews": [(["order_id"], "orders", ["order_id"])],
}
INT_COLS = {
    "order_item_id", "payment_sequential", "payment_installments", "review_score",
    "product_name_lenght", "product_description_lenght", "product_photos_qty",
    "product_weight_g", "product_length_cm", "product_height_cm", "product_width_cm",
}
DEC_COLS = {"price", "freight_value", "payment_value",
            "geolocation_lat", "geolocation_lng"}
TABLE_DESC = {
    "customers": "Customer identifier and location; customer_unique_id identifies a customer across orders.",
    "sellers": "Seller identifier and location.",
    "products": "Products, their categories, and product dimensions.",
    "geolocation": "Geographic records at ZIP-code-prefix level; multiple records can share a prefix.",
    "product_category_name_translation": "Portuguese-to-English product category labels.",
    "orders": "Order status and recorded ordering, approval, carrier handoff and delivery times.",
    "order_items": "Ordered items, product and seller references, shipping deadline, price and freight.",
    "order_payments": "Payment details per order and payment sequence; this table has no payment occurrence timestamp.",
    "order_reviews": "Review content, survey-creation time and response time; review_id alone need not be unique.",
}
COL_DESC = {
    "customer_id": "Order-specific customer identifier.",
    "customer_unique_id": "Identifier that can repeat across customer records for the same individual.",
    "order_id": "Order identifier.",
    "order_item_id": "Item sequence within the order.",
    "order_status": "Current order status, not a timestamped status transition history.",
    "order_purchase_timestamp": "Timestamp of purchase/order placement.",
    "order_approved_at": "Recorded order approval timestamp.",
    "order_delivered_carrier_date": "Timestamp the order was handed to the carrier.",
    "order_delivered_customer_date": "Timestamp the order was delivered to the customer.",
    "order_estimated_delivery_date": "Planned delivery date, not the actual delivery event.",
    "shipping_limit_date": "Seller shipping deadline; a planned time, not carrier handoff.",
    "payment_sequential": "Payment sequence within the order.",
    "payment_type": "Payment method or category.",
    "payment_installments": "Installment count.",
    "payment_value": "Payment monetary amount.",
    "review_id": "Review identifier; uniqueness is not assumed.",
    "review_creation_date": "Date the review survey was created/sent.",
    "review_answer_timestamp": "Timestamp of the review answer.",
    "geolocation_zip_code_prefix": "Postal prefix; not unique in the source records.",
    "product_category_name": "Product category in Portuguese.",
    "product_category_name_english": "English category translation.",
}
def q(s):
    return '"' + s.replace('"', '""') + '"'

def json_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def git_blob_sha(content):
    return hashlib.sha1(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest()

def sources(cache, manifest):
    cache.mkdir(parents=True, exist_ok=True)
    base = ("https://raw.githubusercontent.com/" + manifest["mirror_repository"] +
            "/" + manifest["mirror_commit"] + "/" + manifest["mirror_prefix"])
    for spec in manifest["files"]:
        path = cache / spec["filename"]
        if not path.exists():
            with urllib.request.urlopen(base + spec["filename"], timeout=180) as response:
                path.write_bytes(response.read())
        if git_blob_sha(path.read_bytes()) != spec["git_blob_sha"]:
            raise RuntimeError("Source blob hash mismatch: " + spec["filename"])
    return {x["table"]: x for x in manifest["files"]}

def sql_type(col):
    return "INTEGER" if col in INT_COLS else "TEXT"

def csv_type(col):
    if col in INT_COLS: return "integer"
    if col in DEC_COLS: return "decimal"
    if "timestamp" in col or col.endswith("_date") or col == "shipping_limit_date":
        return "datetime"
    return "text"

def ddl(spec):
    name, cols = spec["table"], spec["columns"]
    pk = PKEYS[name]
    parts = [q(c) + " " + sql_type(c) + (" NOT NULL" if c in pk else "") for c in cols]
    if pk:
        parts.append("PRIMARY KEY (" + ", ".join(map(q, pk)) + ")")
    for children, parent, parents in FKEYS.get(name, []):
        parts.append("FOREIGN KEY (" + ", ".join(map(q, children)) + ") REFERENCES " +
                     q(parent) + " (" + ", ".join(map(q, parents)) + ")")
    return "CREATE TABLE " + q(name) + " (\n  " + ",\n  ".join(parts) + "\n)"

def load_csv(conn, path, spec):
    name, cols = spec["table"], spec["columns"]
    count = 0
    sql = ("INSERT INTO " + q(name) + " (" + ", ".join(map(q, cols)) + ") VALUES (" +
           ", ".join("?" for _ in cols) + ")")
    with gzip.open(path, "rt", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != cols:
            raise ValueError("CSV columns do not match pinned headers for " + name +
                             ": " + repr(reader.fieldnames))
        batch = []
        for record in reader:
            row = []
            for col in cols:
                v = record[col]
                if v is None:
                    raise ValueError("Malformed source row in " + name)
                row.append(None if v == "" else int(v) if col in INT_COLS else v)
            batch.append(row)
            count += 1
            if len(batch) >= 5000:
                conn.executemany(sql, batch)
                batch.clear()
        if batch: conn.executemany(sql, batch)
    if count != spec["expected_rows"]:
        raise ValueError(f"Source row count mismatch in {name}: {count}")
    print(name, count, flush=True)
    return count

def make_dictionary(conn, specs, ddls):
    data = {
        "name": "Olist Brazilian E-Commerce Public Dataset",
        "language": "en",
        "dbms": "SQLite",
        "description": "Unmodified Olist business records from the published nine-file CSV release. "
                       "SQLite keys and references are source-structure interpretations, "
                       "not upstream SQL DDL. The dictionary excludes author gold labels.",
        "tables": [],
    }
    for name in TABLES:
        spec = specs[name]
        pk = PKEYS[name]
        fks = [{
            "name": "FK_" + name + "_" + parent + "_" + "_".join(children),
            "columns": children, "referenced_table": parent,
            "referenced_columns": parents
        } for children, parent, parents in FKEYS.get(name, [])]
        columns = []
        for col in spec["columns"]:
            sample = [r[0] for r in conn.execute(
                "SELECT DISTINCT " + q(col) + " FROM " + q(name) +
                " WHERE " + q(col) + " IS NOT NULL LIMIT 3")]
            columns.append({
                "name": col, "source_type": csv_type(col),
                "source_declaration": "CSV header; no upstream DDL",
                "sql_type": sql_type(col), "computed": False,
                "required": col in pk,
                "definition": COL_DESC.get(col, col.replace("_", " ") + "."),
                "foreign_keys": [{"table": parent, "column": parents[children.index(col)]}
                                 for children, parent, parents in FKEYS.get(name, [])
                                 if col in children],
                "primary_key_position": pk.index(col) + 1 if col in pk else 0,
                "default": None, "sample_values": sample
            })
        data["tables"].append({
            "table": name, "source_schema": "olist",
            "definition": TABLE_DESC.get(name, "Source CSV table."),
            "source_file": spec["filename"].removesuffix(".gz"),
            "columns": columns, "primary_key": pk,
            "foreign_keys": fks,
            "sql_definition": ddls[name],
        })
    return data

def build(cache):
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    specs = sources(cache, manifest)
    if set(specs) != set(TABLES):
        raise ValueError("Expected all nine Olist CSV files")
    input_dir = HERE / "input"
    input_dir.mkdir(exist_ok=True)
    tmp = input_dir / "database.sqlite.building"
    if tmp.exists(): tmp.unlink()
    conn = sqlite3.connect(tmp)
    conn.execute("PRAGMA page_size=4096")
    conn.execute("PRAGMA journal_mode=DELETE")
    conn.execute("PRAGMA foreign_keys=ON")
    ddls = {}
    try:
        # Import parent tables before children while enforcing the declared references.
        for name in TABLES:
            ddls[name] = ddl(specs[name])
            conn.execute(ddls[name])
        counts = {}
        for name in TABLES:
            counts[name] = load_csv(conn, cache / specs[name]["filename"], specs[name])
        conn.commit()
        issues = conn.execute("PRAGMA foreign_key_check").fetchall()
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok" or issues:
            raise RuntimeError(f"SQLite checks failed: {integrity}, FK violations: {issues[:5]}")
        if sum(counts.values()) != manifest["expected_total_rows"]:
            raise RuntimeError("Unexpected total row count")
        data = make_dictionary(conn, specs, ddls)
        conn.close()
        dest = input_dir / "database.sqlite"
        tmp.replace(dest)
        dictionary_path = input_dir / "data_dictionary.json"
        json_write(dictionary_path, data)
        eval_dir = HERE / "evaluation"
        eval_dir.mkdir(exist_ok=True)
        (eval_dir / "schema.sql").write_text(
            "\n\n".join(ddls[name] + ";" for name in TABLES) + "\n",
            encoding="utf-8")
        provenance = {
            "official_url": manifest["official_url"],
            "mirror_repository": manifest["mirror_repository"],
            "mirror_commit": manifest["mirror_commit"],
            "license": manifest["license"],
            "table_count": len(TABLES),
            "column_count": sum(len(s["columns"]) for s in specs.values()),
            "row_count": sum(counts.values()),
            "row_counts": counts,
            "foreign_key_count": sum(map(len, FKEYS.values())),
            "sqlite_integrity": integrity,
            "foreign_key_violations": len(issues),
            "sqlite_sha256": hashlib.sha256(dest.read_bytes()).hexdigest(),
            "dictionary_sha256": hashlib.sha256(dictionary_path.read_bytes()).hexdigest(),
            "original_csv_git_blob_hashes": {x["filename"]: x["git_blob_sha"]
                                              for x in manifest["files"]},
        }
        json_write(HERE / "source" / "provenance.json", provenance)
        from diagram import generate
        generate(data, counts)
        # A portable compressed snapshot; the uncompressed DB is reconstructed
        # by gzip extraction or build.py and excluded from Git to avoid >100 MB blobs.
        gz = input_dir / "database.sqlite.gz"
        with dest.open("rb") as source, gzip.open(gz, "wb", compresslevel=9) as out:
            shutil.copyfileobj(source, out, length=1024 * 1024)
        print(json.dumps({"tables": len(TABLES), "rows": sum(counts.values()),
                          "sqlite_bytes": dest.stat().st_size,
                          "gzip_bytes": gz.stat().st_size}, indent=2))
    except Exception:
        conn.close()
        tmp.unlink(missing_ok=True)
        raise

if __name__ == "__main__":
    arg = argparse.ArgumentParser()
    arg.add_argument("--cache", type=Path, default=Path("/tmp/olist-source"))
    ns = arg.parse_args()
    build(ns.cache)
