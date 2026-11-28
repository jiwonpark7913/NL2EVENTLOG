"""Deterministic table encoding classification."""

from __future__ import annotations
from typing import Any
from src.eeg.evidence_graph_models import Table


def classify_tables(tables: list[Table], timestamps: list[dict[str, Any]],
                    dd: dict[str, Any] | None = None) -> dict[str, dict[str, Any]]:
    """PURPOSE: Record the data-only timestamp gate before carrier discovery finalizes encoding.
    INPUT: Physical tables and accepted timestamp units; DD is ignored for compatibility.
    OUTPUT: Per-table preliminary status, timestamp IDs and explicit encoding rule trace.
    """
    by_table: dict[str, list[str]] = {table.name: [] for table in tables}
    for unit in timestamps:
        by_table.setdefault(unit["table"], []).append(unit["ts_id"])
    result = {}
    for table in tables:
        ids = sorted(by_table[table.name])
        if not ids:
            status, encoding = "not_event_table", None
        else:
            status, encoding = "encoding_pending_carrier_discovery", None
        result[table.name] = {"table": table.name, "status": status, "encoding": encoding,
                              "ts_ids": ids, "activity_columns": [], "trace": f"TR:{table.name}",
                              "encoding_rule": {
                                  "source": "observed_data_only",
                                  "timestamp_unit_count": len(ids),
                                  "carrier_count": None,
                                  "rule": "no_timestamp" if not ids else "await_carrier_discovery"}}
    return result
