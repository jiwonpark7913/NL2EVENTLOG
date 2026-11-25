"""Construct all four AirlineFlow variants from the canonical synthetic records.

No existing SQLite files, migration scripts, or network access are required.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def quote(name):
    return '"' + name.replace('"', '""') + '"'


def manifest(root):
    return json.loads((root / "evaluation/variant_manifest.json").read_text(encoding="utf-8"))


def copy_asset(relative, output):
    target = output / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / relative, target)


def create_database(path, schema, records, expected):
    with sqlite3.connect(path) as db:
        db.execute("PRAGMA foreign_keys=ON")
        db.executescript(schema.read_text(encoding="utf-8"))
        # DDL declares parent tables before their children.
        names = [r[0] for r in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY rowid"
        )]
        if set(names) != set(expected):
            raise ValueError(f"Unexpected tables in {schema}: {names}")
        for name in names:
            table = records[name]
            columns = [r[1] for r in db.execute(f"PRAGMA table_info({quote(name)})")]
            if columns != table["columns"] or len(table["rows"]) != expected[name]:
                raise ValueError(f"Source/schema mismatch: {name}")
            placeholders = ",".join("?" for _ in columns)
            column_list = ",".join(map(quote, columns))
            db.executemany(
                f"INSERT INTO {quote(name)} ({column_list}) VALUES ({placeholders})",
                table["rows"],
            )
        if db.execute("PRAGMA integrity_check").fetchone() != ("ok",):
            raise ValueError(f"SQLite integrity check failed: {path}")
        if db.execute("PRAGMA foreign_key_check").fetchall():
            raise ValueError(f"Foreign key check failed: {path}")


def verify(root):
    subprocess.run([sys.executable, str(root / "verify.py")], check=True)


def build(output):
    output = output.resolve()
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise ValueError(f"Output must be an empty directory: {output}")
    output.mkdir(parents=True, exist_ok=True)
    variants = manifest(ROOT)
    records = json.loads((ROOT / "source/records.json").read_text(encoding="utf-8"))
    if set(records) != set(variants[-1]["table_rows"]):
        raise ValueError("Source must contain the complete L20 schema")
    for relative in ("README.md", "generate.py", "verify.py", "source/records.json"):
        copy_asset(relative, output)
    for directory in ("docs", "private"):
        shutil.copytree(ROOT / directory, output / directory)
    for relative in ("model_questions.jsonl", "query_registry.json", "legacy_model_questions.jsonl"):
        copy_asset(f"evaluation/{relative}", output)
    for variant in variants:
        database = variant["database_path"]
        dictionary = variant["dictionary_path"]
        schema = str(Path(database).with_name("schema.sql"))
        erd = f"variants/{variant['variant_id']}/docs/schema.svg"
        for relative in (schema, dictionary, erd):
            copy_asset(relative, output)
        create_database(output / database, output / schema, records, variant["table_rows"])
        variant["database_sha256"] = digest(output / database)
        variant["dictionary_sha256"] = digest(output / dictionary)
    (output / "evaluation/variant_manifest.json").write_text(
        json.dumps(variants, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    verify(output)
    print(f"Built {len(variants)} AirlineFlow variants at {output}")


def database_contents(path):
    with sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True) as db:
        schema = db.execute(
            "SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name"
        ).fetchall()
        schema = [(kind, name, table, " ".join(sql.split()) if sql else None)
                  for kind, name, table, sql in schema]
        tables = {
            name: db.execute(f"SELECT * FROM {quote(name)} ORDER BY 1").fetchall()
            for kind, name, _, _ in schema if kind == "table"
        }
        return schema, tables


def check_reproduction():
    verify(ROOT)
    with tempfile.TemporaryDirectory(prefix="airlineflow-") as directory:
        output = Path(directory)
        build(output)
        for variant in manifest(ROOT):
            relative = variant["database_path"]
            if database_contents(ROOT / relative) != database_contents(output / relative):
                raise ValueError(f"Reproduction mismatch: {variant['variant_id']}")
            if digest(ROOT / variant["dictionary_path"]) != digest(output / variant["dictionary_path"]):
                raise ValueError(f"Dictionary mismatch: {variant['variant_id']}")
            print(f"PASS: {variant['variant_id']} — schema and all {variant['row_count']} rows")
    print("PASS: all four variants reproduce the published logical database contents.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--output", type=Path, help="Empty directory for a fresh dataset build")
    mode.add_argument("--check", action="store_true", help="Rebuild and compare with published inputs")
    args = parser.parse_args()
    if args.check:
        check_reproduction()
    else:
        build(args.output)


if __name__ == "__main__":
    main()
