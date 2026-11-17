#!/usr/bin/env python3
"""Project heterogeneous legacy data dictionaries to a common, evidence-first schema.

Keeps original JSON unchanged for backward compatibility. The projection is
generated under docs/ and is NOT a source of benchmark Gold annotations.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
NAMES=["adventureworks","mimic","hospitalflow","universityflow","plateflow","warehouseflow"]
VERSION="NL2EVENTLOG-DD-v1"
def normalize(dataset,raw):
 source_tables=raw.get("tables",[])
 if isinstance(source_tables,dict):
  tables=[dict(value,table=name) for name,value in source_tables.items()]
 else:tables=source_tables
 converted=[]
 for table in tables:
  name=table["table"]
  cols=[]
  for c in table.get("columns",[]):
   desc=c.get("definition") or c.get("description") or None
   refs=c.get("source_references") or ([c["definition_source"]] if c.get("definition_source") else [])
   cols.append({
    "metadata_id":c.get("metadata_id") or f"{dataset}.{name}.{c['name']}",
    "name":c["name"],"sql_type":c.get("sql_type") or c.get("type"),
    "source_type":c.get("source_type"),
    "definition":desc,
    "definition_source":c.get("definition_source"),
    "source_references":refs,
    "required":c.get("required"),
    "primary_key_position":c.get("primary_key_position"),
    "foreign_keys":c.get("foreign_keys",[]),
    "temporal_role":c.get("temporal_role"),
    "unit":c.get("unit"),
   })
  converted.append({
    "table":name,
    "metadata_id":table.get("metadata_id") or f"{dataset}.{name}",
    "definition":table.get("definition"),
    "documentation_url":table.get("documentation_url"),
    "source_schema":table.get("source_schema") or table.get("source_module"),
    "row_grain":table.get("row_grain"),
    "primary_key":table.get("primary_key"),
    "foreign_keys":table.get("foreign_keys",[]),
    "columns":cols})
 return {
  "dictionary_schema_version":VERSION,
  "name":raw.get("name") or raw.get("dataset") or dataset,
  "dataset_id":dataset,
  "language":raw.get("language","en"),
  "dbms":raw.get("dbms","SQLite"),
  "timezone":raw.get("timezone"),
  "documentation_sources":raw.get("documentation_sources",{}),
  "tables":converted,
  "note":"Lossless metadata intent, not full legacy-field fidelity: original dictionary is authoritative for unmapped fields. Missing definitions remain null."
 }
def main(dataset):
 src=ROOT/"datasets"/dataset/"input/data_dictionary.json"
 if not src.exists():raise FileNotFoundError(src)
 data=normalize(dataset,json.loads(src.read_text()))
 dest=src.parent.parent/"docs/data_dictionary.standard.json"
 dest.parent.mkdir(parents=True,exist_ok=True)
 dest.write_text(json.dumps(data,indent=2,ensure_ascii=False)+"\n")
 summary={"dataset":dataset,"tables":len(data["tables"]),"columns":sum(len(t["columns"]) for t in data["tables"]),
          "described":sum(bool(c["definition"]) for t in data["tables"] for c in t["columns"])}
 print(json.dumps(summary))
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--dataset",choices=NAMES)
 a=p.parse_args()
 for d in [a.dataset] if a.dataset else NAMES:main(d)
