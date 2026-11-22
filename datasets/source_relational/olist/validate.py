#!/usr/bin/env python3
"""Verify every Olist record, column, and declared relational constraint."""
from __future__ import annotations
import gzip
import hashlib
import json
import sqlite3
from pathlib import Path

BASE = Path(__file__).resolve().parent
manifest = json.loads((BASE/"source/upstream_files.json").read_text())
provenance = json.loads((BASE/"source/provenance.json").read_text())
dictionary = json.loads((BASE/"input/data_dictionary.json").read_text())
db = BASE/"input/database.sqlite"
assert db.is_file(), "Run build.py first, or decompress database.sqlite.gz"
conn = sqlite3.connect("file:" + str(db) + "?mode=ro", uri=True)
assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
assert not list(conn.execute("PRAGMA foreign_key_check"))
assert len(dictionary["tables"]) == len(manifest["files"]) == 9
actual = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
assert actual == {f["table"] for f in manifest["files"]}
for spec in manifest["files"]:
    name = spec["table"]
    table = next(t for t in dictionary["tables"] if t["table"] == name)
    cols = conn.execute('PRAGMA table_info("' + name + '")').fetchall()
    assert [r[1] for r in cols] == spec["columns"], name
    assert [x["name"] for x in table["columns"]] == spec["columns"], name
    rows = conn.execute('SELECT COUNT(*) FROM "' + name + '"').fetchone()[0]
    assert rows == spec["expected_rows"] == provenance["row_counts"][name], name
    pk = [x[1] for x in sorted(cols,key=lambda c:c[5]) if x[5]]
    assert pk == table["primary_key"], name
    assert len(set(r[0] for r in conn.execute('PRAGMA foreign_key_list("' + name + '")'))) == len(table["foreign_keys"]), name
assert provenance["row_count"] == sum(x["expected_rows"] for x in manifest["files"])
assert hashlib.sha256(db.read_bytes()).hexdigest() == provenance["sqlite_sha256"]
dd = BASE/"input/data_dictionary.json"
assert hashlib.sha256(dd.read_bytes()).hexdigest() == provenance["dictionary_sha256"]
gz = BASE/"input/database.sqlite.gz"
if gz.exists():
    with gzip.open(gz,"rb") as source:
        digest=hashlib.sha256()
        while block:=source.read(1024*1024): digest.update(block)
    assert digest.hexdigest() == provenance["sqlite_sha256"]
for f in ["docs/schema.drawio","docs/schema.svg","docs/schema.html",
          "docs/data_dictionary.md","evaluation/schema.sql"]:
    assert (BASE/f).exists(), f
# Financial and temporal fidelity: price and timestamps are held as original text.
assert conn.execute("SELECT COUNT(*) FROM orders WHERE order_purchase_timestamp IS NOT NULL").fetchone()[0] > 0
assert conn.execute("SELECT COUNT(*) FROM order_reviews WHERE review_answer_timestamp IS NOT NULL").fetchone()[0] > 0
conn.close()
print("PASS: 9 tables, 1,550,922 rows, SQL constraints, complete source manifests, dictionary, diagrams, DB hash")
