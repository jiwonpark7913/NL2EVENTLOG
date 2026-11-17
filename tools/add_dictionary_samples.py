#!/usr/bin/env python3
"""Add deterministic, DB-backed sample_values (up to 3) to benchmark dictionaries.

The serializer writes only sample_values arrays inline. Other JSON is indented.
Never fabricate samples; absent SQLite => empty list or error with --require-db.
Source is the local read-only model input database; no Gold is accessed.
"""
from __future__ import annotations
import argparse,json,re,sqlite3
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
NAMES=["adventureworks","mimic","hospitalflow","universityflow","plateflow","warehouseflow","bpi2019_ocel","order_management_ocel"]
MAX_ROWS=5000
MAX_LENGTH=80
SENSITIVE=re.compile(r"(?:free.?text|comment|note|narrative|description_text|password|email|telephone|phone_number|address)",re.I)
INLINE=re.compile(r'("sample_values": )\[\s*((?:(?:"(?:\\.|[^"\\])*"|[-+0-9.eE]+|true|false|null)\s*,?\s*){0,3})\]',re.S)

def identifier(name):
    return '"'+name.replace('"','""')+'"'

def rows_and_columns(dd):
    ts=dd.get("tables",[])
    if isinstance(ts,dict):
        return [(t,v["columns"]) for t,v in ts.items()]
    return [(t["table"],t["columns"]) for t in ts]

def add_samples(dd,db,max_rows=MAX_ROWS):
    conn=sqlite3.connect(f"file:{db}?mode=ro",uri=True)
    conn.row_factory=sqlite3.Row
    present={r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    counts={"columns":0,"sampled":0,"with_values":0,"skipped_sensitive":0,"missing_tables":[]}
    for table,cols in rows_and_columns(dd):
        if table not in present:
            counts["missing_tables"].append(table)
            continue
        valid={r[1] for r in conn.execute("PRAGMA table_info("+identifier(table)+")")}
        candidate=[c for c in cols if c["name"] in valid]
        seen={c["name"]:set() for c in candidate}
        values={c["name"]:[] for c in candidate}
        safe=[c for c in candidate if not SENSITIVE.search(c["name"])]
        for row in conn.execute("SELECT * FROM "+identifier(table)+" ORDER BY rowid LIMIT ?",(max_rows,)):
            for col in safe:
                name=col["name"]
                if len(values[name])>=3:continue
                v=row[name]
                if v is None or isinstance(v,bytes):continue
                if not isinstance(v,(int,float,str)):v=str(v)
                if isinstance(v,str) and (not v.strip() or len(v)>MAX_LENGTH):continue
                key=(type(v).__name__,v)
                if key not in seen[name]:
                    seen[name].add(key);values[name].append(v)
            if all(len(values[c["name"]])>=3 for c in safe):break
        for col in cols:
            if "name" not in col:continue
            counts["columns"]+=1
            if SENSITIVE.search(col["name"]):counts["skipped_sensitive"]+=1
            col["sample_values"]=values.get(col["name"],[])
            if col["sample_values"]:counts["with_values"]+=1
            counts["sampled"]+=len(col["sample_values"])
    conn.close()
    return counts

def write_dictionary(path,dd):
    # JSON remains standard, preserving indentation everywhere except sample_values.
    data=json.dumps(dd,indent=2,ensure_ascii=False)
    def compact(m):
        values=json.loads("["+m.group(2)+"]")
        return m.group(1)+json.dumps(values,ensure_ascii=False,separators=(", ",": "))
    data=INLINE.sub(compact,data)
    path.write_text(data+"\n",encoding="utf-8")
    assert json.loads(path.read_text())==dd
    assert all("\n" not in json.dumps(c["sample_values"],ensure_ascii=False) for _,cs in rows_and_columns(dd) for c in cs)

def main(path,db=None,require_db=False):
    dd=json.loads(path.read_text(encoding="utf-8"))
    found=db and db.exists()
    if require_db and not found:raise FileNotFoundError(f"Real SQLite required: {db}")
    stats={"status":"db-backed" if found else "no-db-unpopulated"}
    if found:
        stats.update(add_samples(dd,db))
    else:
        for _,cols in rows_and_columns(dd):
            for col in cols:col["sample_values"]=[]
    write_dictionary(path,dd)
    print(json.dumps({"dictionary":str(path),"database":str(db) if db else None,**stats}))
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--dataset",choices=NAMES,required=True)
    p.add_argument("--dictionary",type=Path)
    p.add_argument("--database",type=Path)
    p.add_argument("--require-db",action="store_true")
    args=p.parse_args()
    folder=ROOT/"datasets"/args.dataset/"input"
    main(args.dictionary or folder/"data_dictionary.json",
         args.database or folder/"database.sqlite",args.require_db)
