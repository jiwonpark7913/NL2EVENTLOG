#!/usr/bin/env python3
"""Conservative timestamp-candidate detection from heterogeneous data dictionaries.

Source-native types are the primary structural evidence, not inferred event
semantics. Null source_type in legacy datasets leaves status UNKNOWN rather than
silently rejecting a column. Does not classify actual/planned/storage times.
"""
from __future__ import annotations
import json,re
from pathlib import Path

_TEMPORAL=re.compile(r"\b(?:timestamp(?:tz)?|timestamptz|datetime(?:2|offset)?|smalldatetime|date|time(?:tz)?|timetz)\b",re.I)
def temporal_type(source_type):
    if not source_type:return None
    normalized=str(source_type).replace("WITH TIME ZONE","").replace("WITHOUT TIME ZONE","")
    return bool(_TEMPORAL.search(normalized))
def columns(dictionary):
    source=dictionary["tables"]
    return [(name,t,c) for name,t in source.items() for c in t.get("columns",[])] if isinstance(source,dict) else [
        (t["table"],t,c) for t in source for c in t.get("columns",[])]
def detect(dictionary):
    output=[]
    for name,table,col in columns(dictionary):
        original=col.get("source_type")
        actual=col.get("sql_type") or col.get("type")
        native=temporal_type(original)
        physical=temporal_type(actual)
        if native is True:
            status="candidate";evidence="source_type"
        elif native is False:
            status="not_native_temporal";evidence="source_type"
        elif physical is True:
            status="candidate";evidence="sql_type"
        else:
            status="unknown";evidence="missing_source_type"
        output.append({"table":name,"column":col["name"],"status":status,
                       "evidence":evidence,"source_type":original,"sql_type":actual,
                       "definition":col.get("definition") or col.get("description")})
    return output
if __name__=="__main__":
 import argparse
 p=argparse.ArgumentParser();p.add_argument("dictionary",type=Path)
 a=p.parse_args()
 for entry in detect(json.loads(a.dictionary.read_text())):
    if entry["status"]=="candidate":print(json.dumps(entry))
