"""Validate the published AirlineFlow inputs and authored reference logs."""
from collections import Counter
from pathlib import Path
from datetime import datetime
import csv
import hashlib
import json
import sqlite3

root = Path(__file__).resolve().parent
manifest = json.loads((root / "evaluation/variant_manifest.json").read_text())
current_requests = [json.loads(line) for line in (root / "evaluation/model_questions.jsonl").read_text().splitlines() if line.strip()]
registry = json.loads((root / "evaluation/query_registry.json").read_text())
assert current_requests == [{"question_id": q["question_id"], "text": q["question_en"]} for q in registry]
assert [q["question_id"] for q in current_requests] == [f"Q{i:02d}" for i in range(1, 13)]
for variant in manifest:
    assert variant["question_ids"] == [q["question_id"] for q in current_requests]
previous = {}
combinations = 0
for variant in manifest:
    db_path = root / variant["database_path"]
    dictionary_path = root / variant["dictionary_path"]
    for path, checksum in [(db_path, variant["database_sha256"]),
                           (dictionary_path, variant["dictionary_sha256"])]:
        assert hashlib.sha256(path.read_bytes()).hexdigest() == checksum, path
    connection = sqlite3.connect(f"{db_path.as_uri()}?mode=ro", uri=True)
    assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert not connection.execute("PRAGMA foreign_key_check").fetchall()
    names = [row[0] for row in connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    assert len(names) == variant["table_count"]
    current = {}
    for name in names:
        records = connection.execute(f'SELECT * FROM "{name}" ORDER BY 1').fetchall()
        assert len(records) == variant["table_rows"][name]
        current[name] = records
        if name in previous:
            assert records == previous[name], (variant["variant_id"], name)
    previous = current
    for question_id in variant["legacy_question_ids"]:
        query = (root / "private" / f"{question_id}.sql").read_text()
        actual = Counter(connection.execute(query).fetchall())
        with (root / "private" / f"{question_id}_events.csv").open(
                encoding="utf-8-sig", newline="") as stream:
            expected = Counter((r["case_id"], r["activity"], r["timestamp"])
                               for r in csv.DictReader(stream))
        assert actual == expected, (variant["variant_id"], question_id)
        combinations += 1
    for turn, inbound, outbound, handling_start, ready in current["turnarounds"]:
        def movement(flight, kind):
            return connection.execute(
                "SELECT value_at FROM movement_reports WHERE flight_id=? AND kind=?",
                (flight, kind)).fetchone()[0]
        assert movement(inbound, "LAND") < movement(inbound, "IN") <= handling_start
        assert handling_start < ready <= movement(outbound, "OUT") < movement(outbound, "AIR")
    for started, finished, posted in connection.execute(
            "SELECT started_at, finished_at, posted_at FROM handling_jobs"):
        assert started <= finished <= posted
    if "flight_dispatch" in names:
        matching = connection.execute("""
            SELECT count(*) FROM turnarounds t
            JOIN flight_dispatch i ON i.flight_id=t.inbound_id
            JOIN flight_dispatch o ON o.flight_id=t.outbound_id
            WHERE i.tail_id=o.tail_id AND i.destination=o.origin
        """).fetchone()[0]
        assert matching == 48
    if "passengers" in names:
        for birth_date, in connection.execute("SELECT date_of_birth FROM passengers"):
            datetime.strptime(birth_date, "%Y-%m-%d")
    connection.close()
print(f"PASS: {len(manifest)} variants, {combinations} legacy reference comparisons, "
      "checksums, keys, nested records, current question registry and temporal consistency.")
