"""Regress lossless clock projection and timezone-aware ordering."""

from contextlib import closing
from pathlib import Path
import sqlite3

from src.common.data_dictionary import normalize_dictionary
from src.common.timestamp_policy import event_time_order
from src.step1_understand.detect_and_normalize_timestamps import detect_timestamps
from src.step1_understand.eeg_configuration import DbuConfig
from src.step1_understand.project_runtime_evidence_graph import _timestamp_candidate
from src.step3_execute.compile_event_log_sql import _timestamp, _timestamp_component_fields
from src.step3_execute.repair.summarize_event_log_behavior import build_process_summary


def projected_clock(db, binding):
    """PURPOSE: Run compiler clock projections on SQLite. INPUT: DB and ES binding. OUTPUT: Export fields per row."""
    components = _timestamp_component_fields(binding, "s")
    fields = ", ".join(f"{sql} AS {name}" for name, sql in components.items())
    db.row_factory = sqlite3.Row
    return [dict(row) for row in db.execute(f"SELECT {_timestamp(binding, 's')} AS timestamp, {fields} FROM events s")]


def test_raw_clock_and_source_zone_preserved():
    """PURPOSE: Preserve naive and offset values verbatim. INPUT: Mixed clocks. OUTPUT: Original TEXT and row zone."""
    values = ["2025-01-01 10:10:10.000000000", "2025-01-01T09:01:02.123456789+09:00", "2025-01-01T01:00:00Z"]
    with closing(sqlite3.connect(":memory:")) as db:
        db.execute("CREATE TABLE events (stamp TEXT)")
        db.executemany("INSERT INTO events VALUES (?)", [(x,) for x in values])
        rows = projected_clock(db, {"kind": "direct", "column": "stamp", "timezone": "America/New_York"})
        assert [r["timestamp"] for r in rows] == values
        assert [r["timestamp_raw_value"] for r in rows] == values
        assert [r["timestamp_timezone"] for r in rows] == ["America/New_York", "+09:00", "Z"]
        old = projected_clock(db, {"kind": "direct", "column": "stamp", "timezone": "UTC",
                                   "native_timezone": "assumed_utc"})
        assert old[0]["timestamp_timezone"] is None


def test_preserve_epoch_json_number_and_split_clock_components():
    """PURPOSE: Keep integer nanoseconds and JSON numeric precision. INPUT: Physical records. OUTPUT: Raw exports."""
    with closing(sqlite3.connect(":memory:")) as db:
        db.execute("CREATE TABLE events (epoch INTEGER, payload TEXT, day TEXT, clock TEXT)")
        token = "1735689600000000000.12345678"
        db.execute("INSERT INTO events VALUES (?,?,?,?)",
                   (1735689600000000001, '{"clock":'+token+'}', "20250101", "01:02:03.123456789+09:00"))
        epoch = projected_clock(db, {"kind": "direct", "column": "epoch", "detected_format": "epoch_ns"})[0]
        assert epoch["timestamp"] == 1735689600000000001
        assert epoch["timestamp_timezone"] is None
        assert event_time_order(epoch)[0] == 0
        payload = projected_clock(db, {"kind":"json_path", "column":"payload", "json_path":"$.clock",
                                       "detected_format":"epoch_ns"})[0]
        assert payload["timestamp"] == payload["timestamp_raw_value"] == token
        assert event_time_order(payload) < event_time_order(epoch)
        split = projected_clock(db, {"kind":"date_clock", "date_column":"day", "clock_column":"clock"})[0]
        assert split["timestamp"] == '["20250101","01:02:03.123456789+09:00"]'
        assert split["timestamp_day"] == "20250101"
        assert split["timestamp_clock"] == "01:02:03.123456789+09:00"
        assert split["timestamp_timezone"] == "+09:00"
        assert event_time_order(split)[0] == 0


def test_absolute_order_keeps_nanoseconds_and_does_not_conflate_clock_domains():
    """PURPOSE: Order comparable instants. INPUT: Named, offset, ambiguous and naive clocks. OUTPUT: True DFG order."""
    events = [
        {"activity":"later", "timestamp":"2025-01-01T01:00:00.000000002Z"},
        {"activity":"earlier", "timestamp":"2025-01-01T10:00:00.000000001+09:00"},
        {"activity":"first", "timestamp":"2024-12-31 19:00:00", "timestamp_timezone":"America/New_York"},
    ]
    assert [r["activity"] for r in sorted(events, key=event_time_order)] == ["first", "earlier", "later"]
    report = build_process_summary([dict(r, case_id="A") for r in events], query_id="test")
    assert [r["activities"] for r in report["trace_variants_top_n"]] == [["first", "earlier", "later"]]
    report = build_process_summary([dict(events[0], case_id="A"),
                                    {"case_id":"A", "timestamp":"2025-01-01 00:00:00", "activity":"local"}],
                                   query_id="test")
    assert not report["dfg_edges"] and report["incomparable_clock_case_count"] == 1
    assert event_time_order({"timestamp":"2025-11-02 01:30:00", "timestamp_timezone":"America/New_York"})[0] == 2


def test_timezone_flows_from_dictionary_to_event_binding(tmp_path):
    """PURPOSE: Verify scoped DD into compiled clocks. INPUT: Three declared zones. OUTPUT: Column, table and DB precedence."""
    db_path = tmp_path / "test.sqlite"
    with closing(sqlite3.connect(db_path)) as db, db:
        db.execute("CREATE TABLE events (id INTEGER PRIMARY KEY, arrived_at TEXT, ended_at TEXT)")
        db.execute("CREATE TABLE approvals (id INTEGER PRIMARY KEY, approved_at TEXT)")
        db.execute("INSERT INTO events VALUES (1,'2025-01-01 01:00:00','2025-01-01 02:00:00')")
        db.execute("INSERT INTO approvals VALUES (1,'2025-01-01 02:00:00')")
    raw = {"timezone":"UTC", "tables":[{"name":"events","time_zone":"Europe/Paris", "columns":[
        {"name":"arrived_at","timezone":"Asia/Tokyo","description":"Actual arrival timestamp."},
        {"name":"ended_at","description":"Actual end timestamp."}]},
        {"name":"approvals","columns":[{"name":"approved_at","description":"Actual approval timestamp."}]}]}
    from src.common.database_io import load_inputs
    dd_path = Path(tmp_path) / "dictionary.json"
    import json
    dd_path.write_text(json.dumps(raw))
    tables, dd, _ = load_inputs(db_path, dd_path)
    from src.step1_understand.profile_table_values import profile_tables
    profiles = profile_tables(db_path, tables, 5)
    units, _ = detect_timestamps(db_path, tables, profiles, dd, DbuConfig())
    assert {(u["table"],u["columns"][0]): _timestamp_candidate(u)["timezone"] for u in units} == {
        ("events","arrived_at"):"Asia/Tokyo", ("events","ended_at"):"Europe/Paris", ("approvals","approved_at"):"UTC"}
    assert normalize_dictionary({"timezone":"unknown"})["timezone"] is None
