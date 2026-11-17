#!/usr/bin/env python3
"""Conservative timestamp-candidate detection from heterogeneous data dictionaries.

Source-native types are the primary structural evidence, not inferred event
semantics. Null source_type in legacy datasets leaves status UNKNOWN rather than
silently rejecting a column. Does not classify actual/planned/storage times.
"""
from __future__ import annotations
import json,re
from pathlib import Path

# Parse the leading SQL type token; modifiers such as (0), NOT NULL and
# WITH/WITHOUT TIME ZONE are not part of the base type.
_TEMPORAL_BASE_TYPES = {
    "DATE", "TIME", "TIMETZ", "TIMESTAMP", "TIMESTAMPTZ",
    "DATETIME", "DATETIME2", "DATETIMEOFFSET", "SMALLDATETIME",
}

def temporal_type(source_type):
    if source_type is None or not str(source_type).strip():
        return None
    # SQL Server examples: [datetime] NOT NULL / [datetime2](7).
    # PostgreSQL examples: TIMESTAMP(0), timestamp without time zone.
    declaration = str(source_type).strip()
    match = re.match(r"^\\[?([A-Za-z_][A-Za-z_0-9]*)\\]?", declaration)
    if match is None:
        return None
    return match.group(1).upper() in _TEMPORAL_BASE_TYPES

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
