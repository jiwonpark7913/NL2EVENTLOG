"""Print request statistics from the released registry (standard library only)."""
import csv, json
from collections import Counter
from pathlib import Path

root = Path(__file__).resolve().parents[1]
with (root / "evaluation/query_registry.csv").open(encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))
test = [r for r in rows if r["EXPERIMENT"] != "Pilot"]
manifest = json.loads((root / "evaluation/variant_manifest.json").read_text())
out = {
    "requests": len(rows),
    "pilot": len(rows) - len(test),
    "test": len(test),
    "conditions": sum(len(v["question_ids"]) for v in manifest),
    "distinct_test_gold": len({r["GOLD GROUP ID"] for r in test}),
    "test_family_count": len({r["FAMILY ID"] for r in test}),
    "reference_event_rows": sum(int(r["EXPECTED EVENT COUNT"]) for r in rows),
    "test_event_rows": sum(int(r["EXPECTED EVENT COUNT"]) for r in test),
    "by_group": Counter(r["EXPERIMENT"] for r in rows),
}
for name, column in [
    ("test_case", "CASE ENTITY"), ("test_activity_count", "ACT COUNT"),
    ("test_source_count", "EVENT SOURCE COUNT"),
    ("test_logical_depth", "LOGICAL ATTRIBUTION DEPTH"),
    ("test_max_sql_join_depth", "MAX TOTAL JOIN DEPTH"),
    ("test_encoding", "EVENT ENCODING"),
]:
    out[name] = Counter(r[column] for r in test)
out["test_explicitness"] = Counter(r["CASE MODE"] + " / " + r["REQUEST MODE"] for r in test)
out["variants"] = {}
for v in manifest:
    dd = json.loads((root / v["dictionary_path"]).read_text())
    out["variants"][v["variant_id"]] = {
        "tables": v["table_count"],
        "columns": sum(len(t["columns"]) for t in dd.values()),
        "rows": v["row_count"],
    }
print(json.dumps(out, indent=2, sort_keys=True))
