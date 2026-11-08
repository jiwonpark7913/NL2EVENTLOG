#!/usr/bin/env python3
"""Introduce context-dependent, abbreviated physical activity codes without changing business events.

Runs as a deterministic one-time migration; validates every pre-existing Gold SQL/CSV
against the migrated SQLite database before replacing any input or Gold file.
Generated data is a benchmark artifact, not evidence of real ERP data.
"""
import argparse
import csv
import io
import json
import re
import shutil
import sqlite3
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# Code namespaces are distinct: A denotes different actions in different contexts.
CONFIG = {
    "warehouseflow": [
        ("goods_movement", "movement_code", "MOVEMENT", {"IN": "I", "OUT": "O"}),
        ("request_action", "action_code", "REQUEST", {"CHECK": "A", "HOLD": "H", "RELEASE": "R"}),
        ("warehouse_task_history", "task_code", "TASK", {"PUTAWAY": "A", "PICK": "K", "PACK": "B"}),
        ("handling_history", "handling_code", "HANDLING", {"UNLOAD": "U", "LOAD": "L"}),
    ],
    "plateflow": [
        ("furnace_operation_history", "operation_code", "FURNACE", {"CH": "C", "HT": "A", "DS": "D"}),
        ("rolling_operation_history", "phase_code", "ROLLING", {"RR": "R", "FR": "F"}),
        ("finishing_operation_history", "operation_code", "FINISHING", {"LEV": "L", "HT": "A", "SF": "S"}),
    ],
    "hospitalflow": [
        ("order_history", "action", None, {"ENTERED": "E", "REVIEWED": "R", "CANCELLED": "C"}),
    ],
}
CODE_TABLE = {"warehouseflow": ("work_code", "code_family"), "plateflow": ("process_code", "process_group")}

def qi(value):
    return '"' + value.replace('"', '""') + '"'

def rewrite_sql(sql, config):
    """Change selector literals only, preserving semantic activity labels and IDs."""
    for table, column, namespace, mapping in config:
        for old, new in mapping.items():
            # Condition-specific substitutions; DO NOT rename labels in SELECT clauses.
            pattern = r"(\b" + re.escape(column) + r"\b\s*(?:=|==)\\s*')"+re.escape(old)+r"(')"
            sql = re.sub(pattern,lambda m:m.group(1)+new+m.group(2),sql,flags=re.I)
            pattern_reverse=r"('"+re.escape(old)+r"'\s*=\s*(?:\w+\.)?"+re.escape(column)+r"\b)"
            sql = re.sub(pattern_reverse,lambda m:m.group(0).replace("'"+old+"'","'"+new+"'"),sql,flags=re.I)
    return sql

def rewrite_es(node, config):
    if isinstance(node, dict):
        return {k:(rewrite_sql(v,config) if k in ("compiled_sql","event_sql","sql","row_filter") and isinstance(v,str) else rewrite_es(v,config)) for k,v in node.items()}
    if isinstance(node,list): return [rewrite_es(v,config) for v in node]
    return node

def query_result(con, sql):
    return sorted(tuple("" if value is None else str(value) for value in row) for row in con.execute(sql))

def test_gold(con,base,config):
    results=[]
    for file in sorted((base/"private/gold_sql").glob("*.sql")):
        original=file.read_text()
        updated=rewrite_sql(original,config)
        name=file.stem
        csv_path=base/"private/gold_logs"/(name+".csv")
        if not csv_path.exists():
            continue  # Unsupported question, checked through Gold metadata instead.
        with csv_path.open(newline="",encoding="utf-8-sig") as f:
            reader=csv.reader(f)
            header=next(reader,None)
            if header != ["event_id","case_id","activity","timestamp"]:
                raise AssertionError(f"{csv_path}: unexpected headers {header}")
            wanted=sorted(tuple(row) for row in reader)
        actual=query_result(con,updated)
        if wanted!=actual:
            raise AssertionError(f"Gold mismatch: {base.name}/{name}; expected {len(wanted)} rows, SQL returned {len(actual)}")
        results.append((file,updated,len(wanted)))
    if not results: raise AssertionError(f"No Gold SQL checked for {base.name}")
    return results

def transform(base, output):
    name=base.name
    config=CONFIG[name]
    db=base/"input/database.sqlite"
    dest=output/"database.sqlite"
    shutil.copyfile(db,dest)
    con=sqlite3.connect(dest)
    con.execute("PRAGMA foreign_keys=OFF")
    # Run in a single transaction. All code-table and record changes are coordinated.
    for table,column,namespace,mapping in config:
        for old,new in mapping.items():
            count=con.execute(f"SELECT COUNT(*) FROM {qi(table)} WHERE {qi(column)}=?",(old,)).fetchone()[0]
            if count:
                con.execute(f"UPDATE {qi(table)} SET {qi(column)}=? WHERE {qi(column)}=?",(new,old))
            elif con.execute(f"SELECT COUNT(*) FROM {qi(table)} WHERE {qi(column)}=?",(new,)).fetchone()[0]==0:
                raise AssertionError(f"{name}: missing source code {table}.{column}={old}")
        if name in CODE_TABLE:
            codes,group=CODE_TABLE[name]
            for old,new in mapping.items():
                con.execute(f"UPDATE {qi(codes)} SET code=? WHERE {qi(group)}=? AND code=?",(new,namespace,old))
    if list(con.execute("PRAGMA foreign_key_check")):
        raise AssertionError(name+": foreign key violations after code migration")
    if con.execute("PRAGMA integrity_check").fetchone()[0]!="ok":
        raise AssertionError(name+": SQLite integrity check failed")
    con.commit()
    results=test_gold(con,base,config)
    con.close()
    dictionary=json.loads((base/"input/data_dictionary.json").read_text())
    for table,column,namespace,mapping in config:
        dd_table=next(t for t in dictionary["tables"] if t["table"]==table)
        dd_col=next(c for c in dd_table["columns"] if c["name"]==column)
        # This is ordinary business-code documentation, not the Gold Event Specification.
        explanations = []
        for old,new in mapping.items():
            meaning=old.replace("_"," ").title()
            if name in CODE_TABLE:
                entry=next(e for e in dictionary["code_values"] if e["code"]==old and e.get(CODE_TABLE[name][1])==namespace)
                meaning=entry["meaning"]
                entry["code"]=new
            explanations.append(f"{new} = {meaning}")
        dd_col["code_meanings"]={new:next((e["meaning"] for e in dictionary.get("code_values",[]) if e.get("code")==new and e.get(CODE_TABLE.get(name,("", ""))[1])==namespace),old.replace("_"," ").title()) for old,new in mapping.items()}
        dd_col["definition"]="Physical business-action code in "+(namespace+" context" if namespace else table)+"; "+ "; ".join(explanations)+". Recorded occurrence time is given by the corresponding event timestamp; the code alone is not proof of occurrence."
    dictionary.setdefault("business_rules",[]).append("Business-action codes are namespace-specific. Identical physical codes in different business contexts can mean different actions. Use the code's business definition or referenced code table; do not infer meaning from the raw code alone.")
    (output/"data_dictionary.json").write_text(json.dumps(dictionary,indent=2,ensure_ascii=False)+"\n")
    for file,sql,count in results:
        dest=output/"gold_sql"/file.name
        dest.parent.mkdir(exist_ok=True)
        dest.write_text(sql)
    gold_file=base/"private/gold.jsonl"
    if gold_file.exists() and gold_file.stat().st_size:
        modified=[]
        for line in gold_file.read_text().splitlines():
            if line.strip(): modified.append(rewrite_es(json.loads(line),config))
        (output/"gold.jsonl").write_text("".join(json.dumps(x,ensure_ascii=False)+"\n" for x in modified))
    return {"dataset":name,"gold_sql_validated":len(results),"gold_rows_validated":sum(row[2] for row in results),
            "physical_code_groups":len(config),"existing_gold_event_labels":"unchanged"}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--apply",action="store_true")
    args=parser.parse_args()
    report=[]
    with tempfile.TemporaryDirectory() as temp:
        root=Path(temp)
        for name in CONFIG:
            base=ROOT/"datasets"/name
            target=root/name
            target.mkdir()
            report.append(transform(base,target))
        if args.apply:
            for name in CONFIG:
                base=ROOT/"datasets"/name
                target=root/name
                shutil.copy2(target/"database.sqlite",base/"input/database.sqlite")
                shutil.copy2(target/"data_dictionary.json",base/"input/data_dictionary.json")
                for sql in (target/"gold_sql").glob("*.sql"):
                    shutil.copy2(sql,base/"private/gold_sql"/sql.name)
                if (target/"gold.jsonl").exists():
                    shutil.copy2(target/"gold.jsonl",base/"private/gold.jsonl")
            (ROOT/"docs/system/activity_semantics_migration_report.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({"applied":args.apply,"results":report},indent=2))

if __name__=="__main__": main()
