#!/usr/bin/env python3
"""Validate four-domain semantic-code benchmark without LLM/API calls."""
import csv
import json
import sqlite3
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
EXPECT={
 "warehouseflow": [
   ("request_action","action_code","A","Check receiving request"),
   ("warehouse_task_history","task_code","A","Putaway work"),
 ],
 "plateflow": [
   ("furnace_operation_history","operation_code","A","Furnace heating"),
   ("finishing_operation_history","operation_code","A","Heat treatment"),
 ],
 "hospitalflow": [
   ("order_history","action","E","Order Entered"),
   ("order_history","action","R","Order Reviewed"),
 ],
 "universityflow": [
   ("assignment_grading","grading_kind","A","Assignment Graded"),
   ("assignment_grading","grading_kind","R","Assignment Regraded"),
 ],
}
SNAPSHOTS={
 "warehouseflow":("goods","category_code"),
 "plateflow":("dimension_inspection","result_code"),
 "hospitalflow":("patients","gender"),
 "universityflow":("registration","status"),
}

def check(name):
    base=ROOT/"datasets"/name
    db=base/"input/database.sqlite"
    con=sqlite3.connect(f"file:{db}?mode=ro",uri=True)
    assert con.execute("PRAGMA integrity_check").fetchone()[0]=="ok",name
    assert not list(con.execute("PRAGMA foreign_key_check")),name
    dd=json.loads((base/"input/data_dictionary.json").read_text())
    cases=[]
    for table,column,code,label in EXPECT[name]:
        physical=con.execute(f'SELECT COUNT(*) FROM "{table}" WHERE "{column}"=?',(code,)).fetchone()[0]
        assert physical>0,(name,table,column,code,"No records")
        field=next(c for t in dd["tables"] if t["table"]==table for c in t["columns"] if c["name"]==column)
        meaning=field.get("code_meanings",{}).get(code,"")
        assert meaning and (label.lower() in meaning.lower() or meaning.lower() in label.lower()),(table,column,meaning,label)
        cases.append(dict(table=table,column=column,code=code,meaning=meaning,records=physical))
    if name in ("warehouseflow","plateflow"):
        assert cases[0]["code"]==cases[1]["code"] and cases[0]["meaning"]!=cases[1]["meaning"],name
    t,c=SNAPSHOTS[name]
    assert con.execute("SELECT COUNT(*) FROM "+'"'+t+'"').fetchone()[0]>0
    labels=set()
    verified=0
    for sql in sorted((base/"private/gold_sql").glob("*.sql")):
        expected=base/"private/gold_logs"/(sql.stem+".csv")
        if not expected.exists():continue
        with expected.open(newline="",encoding="utf-8-sig") as f:
            reader=csv.reader(f)
            assert next(reader)==["event_id","case_id","activity","timestamp"]
            rows=sorted(map(tuple,reader))
        got=sorted(tuple("" if v is None else str(v) for v in rec) for rec in con.execute(sql.read_text()))
        assert got==rows,(name,sql.name,len(got),len(rows))
        labels.update(row[2] for row in rows)
        verified+=1
    assert verified>0
    con.close()
    return dict(dataset=name,code_cases=cases,snapshot_control=f"{t}.{c}",
                validated_gold_queries=verified,distinct_gold_labels=len(labels))
if __name__=="__main__":
    output=[check(name) for name in EXPECT]
    print(json.dumps(output,indent=2))
