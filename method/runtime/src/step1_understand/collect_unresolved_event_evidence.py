"""Index unresolved event evidence separately from executable definitions."""

from collections import defaultdict

from src.common.data_dictionary import dictionary_indexes
from src.step1_understand.detect_and_normalize_timestamps import documented_action_clock, occurrence_time_policy
from src.step1_understand.carrier_timestamp_binding import carrier_clock_relationship

VERSION = "unresolved-event-evidence-v2"


def collect_unresolved_event_evidence(native, dictionary):
    """PURPOSE: Retain observed unresolved values and bounded unconfirmed column evidence.
    INPUT: Native EEG and public dictionary. OUTPUT: Metadata index with independent clock and value status.
    """
    indexes = dictionary_indexes(dictionary)
    clocks = {unit["ts_id"]: unit for unit in native["timestamps"]}
    matrix = native.get("carrier_timestamp_matrix", [])
    documented_pairs = {(r["table"], r["carrier"], r["ts_id"]) for r in matrix if r["status"] == "supported"}
    actual_clocks = defaultdict(set)
    for unit in clocks.values():
        if unit.get("semantic_role") == "business_occurrence" and occurrence_time_policy(unit)["eligible"]:
            actual_clocks[unit["table"]].add(unit["ts_id"])
    pairs = []
    for row in matrix:
        if row["status"] != "unresolved":
            continue
        table, column = row["table"], row["carrier"]
        unit = clocks[row["ts_id"]]
        carrier_doc = indexes["columns"].get((table, column), {})
        clock_doc = indexes["columns"].get((table, unit["columns"][0]), {})
        # Test whether the documented clock applies under a raw selector, independently of a business label.
        raw = {"kind": "value", "column": column, "value": row["value"]}
        literal = {"status": "supported", "code_meaning": str(row["value"])}
        physical = carrier_clock_relationship(
            unit, clock_doc, carrier_doc, raw, literal, {"support_count": row["timed_rows"]})
        endpoint = physical["status"] == "supported" and physical["reason"] == "documented_actual_action_endpoint"
        row_action = None
        if (not endpoint and row["value_semantics_status"] == "unresolved" and row["timed_rows"] > 0
                and actual_clocks[table] == {row["ts_id"]} and unit.get("role_status") == "supported"
                and len(unit["columns"]) == 1 and not unit.get("json_path")
                and (table, column, row["ts_id"]) in documented_pairs):
            row_action = documented_action_clock(clock_doc.get("definition", ""))
        cites = [{"id": doc["id"], "quote": doc["definition"]} for doc in (carrier_doc, clock_doc)
                 if doc.get("id") and doc.get("definition")]
        pairs.append({**row, "raw_clock_validated": bool(endpoint or row_action),
                      "raw_clock_phase": physical["phase"] if endpoint else None,
                      "raw_clock_action": row_action, "public_evidence": cites})
    carriers = [{"table": table["table"], "column_id": item["column_id"],
                 "distinct_count": item["distinct_count"], "sample_values": item["sample_values"][:5],
                 "timestamp_unit_ids": table["timestamp_unit_ids"], "reasons": item["review_reasons"]}
                for table in native.get("event_interpretation_candidates", [])
                for item in table["carrier_candidates"]
                if not item["generated_binding_candidates"] and item["semantic_evidence_status"] == "unresolved"]
    return {"version": VERSION, "pairs": pairs, "unconfirmed_carriers": carriers}
