#!/usr/bin/env python3
"""Check migrated synthetic HospitalFlow SQLite, Data Dictionary, and Gold logs."""
from pathlib import Path
import csv,json,sqlite3
P=Path(__file__).resolve().parent
db=sqlite3.connect("file:"+str(P/"input/database.sqlite")+"?mode=ro",uri=True)
assert db.execute("PRAGMA integrity_check").fetchone()[0]=="ok"
assert not list(db.execute("PRAGMA foreign_key_check"))
tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
assert len(tables)==12
assert "patient_profile" not in tables and "transfers" in tables
columns=lambda t:{r[1] for r in db.execute('PRAGMA table_info("'+t+'")')}
assert {"subject_id","gender","anchor_age","anchor_year","anchor_year_group","dod"}<=columns("patients")
assert {"admittime","dischtime","deathtime","edregtime","edouttime"}<=columns("admissions")
assert "discharge_authorized_at" not in columns("admissions")
assert {"subject_id","hadm_id","transfer_id","eventtype","careunit","intime","outtime"}==columns("transfers")
assert db.execute("SELECT COUNT(*) FROM transfers").fetchone()[0]==38
assert db.execute("SELECT COUNT(*) FROM transfers WHERE eventtype='transfer'").fetchone()[0]==10
dd=json.loads((P/"input/data_dictionary.json").read_text())
for table in dd["tables"]:
    assert table["table"] in tables,table["table"]
    assert {c["name"] for c in table["columns"]}==columns(table["table"]),table["table"]
gold=[json.loads(x) for x in (P/"private/gold.jsonl").read_text().splitlines() if x]
verified=0
for g in gold:
    if g.get("answerability")!="answerable":continue
    id=g["question_id"]
    sql=(P/"private/gold_sql"/(id+".sql")).read_text()
    actual=[["" if v is None else str(v) for v in row] for row in db.execute(sql)]
    with (P/"private/gold_logs"/(id+".csv")).open(newline="") as f:
        reader=csv.reader(f);assert next(reader)==["event_id","case_id","activity","timestamp"]
        expected=list(reader)
    assert actual==expected,(id,len(actual),len(expected))
    assert len(actual)==g["event_count"],id
    verified+=1
assert verified==42
assert all(x["activity"] not in ("Patient Profile Verified","Discharge Authorized")
    for x in [json.loads(x) for x in (P/"private/canonical_history.jsonl").read_text().splitlines() if x])
assert len([x for x in (P/"private/canonical_history.jsonl").read_text().splitlines() if x])==627
identity=json.loads((P/"private/identity_gold.json").read_text())
assert identity["expected_group_count"]==11
assert identity["physical_object_count"]==12
assert identity["pair_count"]==66
assert identity["expected_decision_counts"]=={"MERGE":1,"SEPARATE":65,"UNRESOLVED":0}
print(json.dumps({"database":"ok","tables":len(tables),"transfers":38,
 "gold_sql_csv_pairs":verified,"canonical_events":627,"object_types":11}))
db.close()
