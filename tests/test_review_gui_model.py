"""Tests for pure EEG reviewer functions; fixture graphs are not runtime results."""
from __future__ import annotations
import sqlite3, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools/review_gui"))
from model import (adapt_native_graph, base_sql_type, readonly_preview,
                   reviewer_patch, table_catalog, temporal_candidates, validate_graph)

def test_temporal_type_parser_and_fallback():
    """PURPOSE: Cover modifiers, brackets, NULL and missing source type. INPUT: Type variants. OUTPUT: Correct structural detection."""
    assert [base_sql_type(x) for x in ("timestamp(6)","[datetime2](7)","TIMESTAMPTZ",None)]==["TIMESTAMP","DATETIME2","TIMESTAMPTZ",None]
    table={"columns":[{"name":"planned","source_type":None,"sql_type":"DATETIME"},{"name":"note","sql_type":"TEXT"}]}
    assert [x["name"] for x in temporal_candidates(table)]==["planned"]

def test_dictionary_layouts():
    """PURPOSE: Verify both legacy layouts. INPUT: Object/array tables. OUTPUT: Same normalized table name."""
    assert table_catalog({"tables":{"x":{"columns":[]}}})[0]["table"]=="x"
    assert table_catalog({"tables":[{"table":"x"}]})[0]["table"]=="x"

def test_readonly_sqlite_and_unknown_table(tmp_path):
    """PURPOSE: Prove paginated immutable reads and identifier allow-listing. INPUT: Tiny SQLite fixture. OUTPUT: Rows/no DB mutation."""
    db=tmp_path/"fixture.sqlite"; con=sqlite3.connect(db); con.execute('CREATE TABLE "odd name"(id INTEGER PRIMARY KEY, value TEXT)'); con.executemany('INSERT INTO "odd name" VALUES(?,?)',[(1,"a"),(2,"b")]); con.commit(); con.close()
    assert readonly_preview(db,"odd name",limit=1,offset=1)==[{"id":2,"value":"b"}]
    try: readonly_preview(db,'odd name"; DELETE FROM "odd name')
    except ValueError: pass
    assert sqlite3.connect(db).execute('SELECT count(*) FROM "odd name"').fetchone()[0]==2

def test_actual_runtime_adapter_many_to_many_and_patch():
    """PURPOSE: Validate a clearly fake native export including two attributions. INPUT: Test-only native graph. OUTPUT: Valid graph and immutable review patch."""
    native={"dataset":"fixture","tables":[{"table":"events"}],"concepts":[{"id":"et:a","name":"A","member_tables":["events"]},{"id":"et:b","name":"B","member_tables":["events"]}],"bindings":[{"id":"event:x","table":"events","alpha":{"name":"created"},"occurrence_time_source":{"time_role":"recording"}}],"binding_object_associations":[{"id":"attr:a","binding_id":"event:x","concept_id":"et:a","validation_status":"valid"},{"id":"attr:b","binding_id":"event:x","concept_id":"et:b","validation_status":"valid"}]}
    graph=adapt_native_graph(native); assert validate_graph(graph) is None
    assert len([n for n in graph["nodes"] if n["type"]=="attribution_rule"])==2
    patch=reviewer_patch(graph,"fixture","r1",[{"target_id":"event:x","decision":"uncertain"}],"2026-11-18T00:00:00Z")
    assert patch["graph_sha256"] and graph["native_graph"]==native

def test_empty_case_population_is_preserved():
    """PURPOSE: Ensure adapter retains native empty populations. INPUT: Entity Type with zero cases. OUTPUT: Evidence remains inspectable."""
    native={"dataset":"fixture","tables":[],"concepts":[{"id":"et:empty","name":"Empty","population":{"count":0}}],"bindings":[]}
    graph=adapt_native_graph(native)
    assert graph["nodes"][0]["evidence"]["population"]["count"]==0
