"""Evidence-aware classification of verified child->parent Table references (threshold-based observations)."""

from __future__ import annotations
from collections import defaultdict
from heapq import heappop, heappush
from pathlib import Path
from typing import Any
import re
import sqlite3
from src.common.database_io import connect_readonly, quote_identifier
from src.step1_understand.detect_and_normalize_timestamps import name_tokens, normalization_sql
PART_WORDS = re.compile(
    r"\b(component of|part of|belongs to|derived from|"
    r"parent\s+as[ -]rolled(?:\s+material|\s+plate)?)\b", re.I)
SAME_WORDS = re.compile(r"\b(same business (?:entity|instance)|same object identity)\b", re.I)
INDEPENDENT_WORDS = re.compile(r"\b(distinct|separate|independent lifecycle|different object)\b", re.I)
START_TERMS = {"start", "started", "begin", "began", "from", "intime", "admittime", "admit",
               "admission", "arrival", "arrived", "registration", "registered", "open"}
END_TERMS = {"end", "ended", "finish", "finished", "to", "outtime", "dischtime", "discharge",
             "departure", "departed", "closed", "close", "completion", "completed"}


def _dictionary_text(dd: dict[str, Any], table: str, columns: list[str]) -> str:
    """PURPOSE: Gather attributable public DD text for one relation endpoint.
    INPUT: Normalized DD, table and physical columns.
    OUTPUT: Concatenated table/column definitions without generated assertions.
    """
    item = next((value for value in dd.get("tables", []) if value.get("table") == table), {})
    if dd.get("columns"):
        selected = [column.get("definition", "") for column in dd.get("columns", [])
                    if column.get("table") == table and column.get("column") in columns]
    else:
        selected = [column.get("definition", "") for column in item.get("columns", [])
                    if column.get("name") in columns]
    return " ".join([item.get("definition", ""), *selected]).strip()


def _column_text(dd: dict[str, Any], table: str, column: str) -> str:
    """PURPOSE: Resolve one normalized DD column definition for interval-role scoring.
    INPUT: Normalized dictionary and physical table/column.
    OUTPUT: Original definition text or an empty string.
    """
    return str(next((item.get("definition", "") for item in dd.get("columns", [])
                     if item.get("table") == table and item.get("column") == column), ""))


def _interval_role_score(unit: dict[str, Any], dd: dict[str, Any], terms: set[str]) -> int:
    """PURPOSE: Rank an already-approved TimestampUnit as an interval endpoint.
    INPUT: TimestampUnit, normalized DD and controlled start/end term set.
    OUTPUT: Integer score; zero means no endpoint evidence.
    """
    columns = list(unit.get("columns", []))
    name_evidence = {token for column in columns for token in name_tokens(column)}
    definition_evidence = {token for column in columns
                           for token in name_tokens(_column_text(dd, unit["table"], column))}
    return 4 * len(name_evidence & terms) + len(definition_evidence & terms)


def _table_interval(table: str, timestamps: list[dict[str, Any]],
                    dd: dict[str, Any]) -> dict[str, Any] | None:
    """PURPOSE: Select one unambiguous start/end pair from discovered TimestampUnits.
    INPUT: Table, accepted timestamp inventory and normalized DD.
    OUTPUT: Pair with evidence, or None when either endpoint is absent/ambiguous.
    """
    units = [item for item in timestamps
             if item.get("table") == table and item.get("source") in {"column", "composite"}]
    scored_start = sorted(((_interval_role_score(item, dd, START_TERMS), item["ts_id"], item)
                           for item in units), key=lambda item: (-item[0], item[1]))
    scored_end = sorted(((_interval_role_score(item, dd, END_TERMS), item["ts_id"], item)
                         for item in units), key=lambda item: (-item[0], item[1]))
    if not scored_start or not scored_end or scored_start[0][0] <= 0 or scored_end[0][0] <= 0:
        return None
    if len(scored_start) > 1 and scored_start[0][0] == scored_start[1][0]:
        return None
    if len(scored_end) > 1 and scored_end[0][0] == scored_end[1][0]:
        return None
    start, end = scored_start[0][2], scored_end[0][2]
    if start["ts_id"] == end["ts_id"]:
        return None
    return {"start": start, "end": end,
            "selection_evidence": {"start_score": scored_start[0][0],
                                   "end_score": scored_end[0][0]}}


def _qualified_time_sql(unit: dict[str, Any], alias: str) -> str:
    """PURPOSE: Reuse timestamp normalization while qualifying its physical columns.
    INPUT: Accepted TimestampUnit and trusted SQL alias.
    OUTPUT: SQLite expression safe to embed in a joined relation probe.
    """
    expression = normalization_sql(unit)
    for column in sorted(unit.get("columns", []), key=len, reverse=True):
        quoted = quote_identifier(column)
        expression = expression.replace(quoted, f"{alias}.{quoted}")
    return expression


def _key_expression(alias: str, columns: list[str]) -> str:
    """PURPOSE: Serialize a physical composite key without lossy concatenation.
    INPUT: Trusted SQL alias and ordered column names.
    OUTPUT: SQLite json_array expression.
    """
    return "json_array(" + ",".join(
        f"{alias}.{quote_identifier(column)}" for column in columns) + ")"


def _join_condition(reference: dict[str, Any], child_alias: str = "c",
                    parent_alias: str = "p") -> str:
    """PURPOSE: Compile one verified reference into a deterministic equality join.
    INPUT: Reference column pairs and aliases.
    OUTPUT: Conjunctive SQLite join condition.
    """
    return " AND ".join(
        f"{child_alias}.{quote_identifier(left)}={parent_alias}.{quote_identifier(right)}"
        for left, right in reference.get("columns", []))


def profile_structural_evidence(connection: sqlite3.Connection, reference: dict[str, Any],
                                table_keys: list[dict[str, Any]], *, child_ref_threshold: float,
                                multi_parent_threshold: float) -> dict[str, Any]:
    """PURPOSE: Measure direction, coverage and multiplicity for one child-to-parent reference.
    INPUT: Read-only DB, verified reference, Table + representative Key records and acceptance thresholds.
    OUTPUT: Auditable statistics plus a structural pass flag.
    """
    child_table, parent_table = reference["child_table"], reference["parent_table"]
    child_table_key = next((item for item in table_keys if item.get("table") == child_table), None)
    parent_table_key = next((item for item in table_keys if item.get("table") == parent_table), None)
    child_key = list((child_table_key or {}).get("pk", []))
    parent_key = list((parent_table_key or {}).get("pk", []))
    child_ref = [left for left, _ in reference.get("columns", [])]
    parent_ref = [right for _, right in reference.get("columns", [])]
    base = {"child_key": child_key, "parent_key": parent_key,
            "child_reference": child_ref, "parent_reference": parent_ref,
            "child_ref_coverage": 0.0, "parent_child_coverage": 0.0,
            "multi_parent_ratio": 1.0, "max_children_per_parent": 0,
            "mean_children_per_parent": 0.0, "passed": False}
    if not child_key or not parent_key or not reference.get("columns"):
        return {**base, "status": "unavailable", "reason": "missing_object_key_or_reference"}
    child_q, parent_q = quote_identifier(child_table), quote_identifier(parent_table)
    condition = _join_condition(reference)
    non_null = " AND ".join(f"c.{quote_identifier(column)} IS NOT NULL" for column in child_ref)
    child_total = int(connection.execute(f"SELECT COUNT(*) FROM {child_q}").fetchone()[0])
    matched = int(connection.execute(
        f"SELECT COUNT(DISTINCT {_key_expression('c', child_key)}) "
        f"FROM {child_q} c JOIN {parent_q} p ON {condition}"
        + (f" WHERE {non_null}" if non_null else "")).fetchone()[0])
    parent_total = int(connection.execute(f"SELECT COUNT(*) FROM {parent_q}").fetchone()[0])
    parents_with_children = int(connection.execute(
        f"SELECT COUNT(DISTINCT {_key_expression('p', parent_key)}) FROM {child_q} c "
        f"JOIN {parent_q} p ON {condition}").fetchone()[0])
    rows = connection.execute(
        f"SELECT {_key_expression('c', child_key)}, {_key_expression('p', parent_key)} "
        f"FROM {child_q} c JOIN {parent_q} p ON {condition}").fetchall()
    child_parents: dict[str, set[str]] = defaultdict(set)
    parent_children: dict[str, set[str]] = defaultdict(set)
    for child, parent in rows:
        child_parents[child].add(parent)
        parent_children[parent].add(child)
    multi_parent = sum(len(values) > 1 for values in child_parents.values())
    multi_parent_ratio = multi_parent / len(child_parents) if child_parents else 0.0
    child_counts = [len(values) for values in parent_children.values()]
    coverage = matched / child_total if child_total else 0.0
    base.update({
        "child_rows": child_total, "matched_child_rows": matched,
        "child_ref_coverage": coverage,
        "parent_child_coverage": parents_with_children / parent_total if parent_total else 0.0,
        "multi_parent_ratio": multi_parent_ratio,
        "max_children_per_parent": max(child_counts, default=0),
        "mean_children_per_parent": sum(child_counts) / len(child_counts) if child_counts else 0.0,
        "passed": coverage >= child_ref_threshold and multi_parent_ratio <= multi_parent_threshold,
        "status": "assessed",
        "thresholds": {"child_ref_coverage": child_ref_threshold,
                       "multi_parent_ratio": multi_parent_threshold},
    })
    return base


def _sibling_overlap_ratio(rows: list[tuple[str, str, float, float, float, float]]) -> float | None:
    """PURPOSE: Measure overlapping child intervals within each parent efficiently.
    INPUT: Linked rows containing child/parent keys and normalized epoch boundaries.
    OUTPUT: Overlapping sibling-pair ratio, or None when no sibling pairs exist.
    """
    by_parent: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for _, parent, child_start, child_end, _, _ in rows:
        by_parent[parent].append((child_start, child_end))
    overlaps = total_pairs = 0
    for intervals in by_parent.values():
        total_pairs += len(intervals) * (len(intervals) - 1) // 2
        active: list[float] = []
        for start, end in sorted(intervals):
            while active and active[0] <= start:
                heappop(active)
            overlaps += len(active)
            heappush(active, end)
    return overlaps / total_pairs if total_pairs else None


def profile_temporal_evidence(connection: sqlite3.Connection, reference: dict[str, Any],
                              table_keys: list[dict[str, Any]], timestamps: list[dict[str, Any]],
                              dd: dict[str, Any],
                              *, containment_threshold: float, precedes_threshold: float,
                              tolerance_seconds: int) -> dict[str, Any]:
    """PURPOSE: Test whether linked child intervals lie within parent intervals.
    INPUT: Read-only DB, reference, representative Keys, accepted TimestampUnits, DD and thresholds.
    OUTPUT: Containment/precedence/overlap evidence; missing intervals are unavailable, not failed.
    """
    child_interval = _table_interval(reference["child_table"], timestamps, dd)
    parent_interval = _table_interval(reference["parent_table"], timestamps, dd)
    unavailable = {"status": "unavailable", "passed": None,
                   "tolerance_seconds": tolerance_seconds,
                   "interval_containment_ratio": None, "child_before_parent_ratio": None,
                   "sibling_overlap_ratio": None}
    if not child_interval or not parent_interval:
        return {**unavailable, "reason": "interval_endpoint_unavailable",
                "child_interval": None if not child_interval else [
                    child_interval["start"]["ts_id"], child_interval["end"]["ts_id"]],
                "parent_interval": None if not parent_interval else [
                    parent_interval["start"]["ts_id"], parent_interval["end"]["ts_id"]]}
    child_table_key = next((item for item in table_keys
                         if item.get("table") == reference["child_table"]), {})
    parent_table_key = next((item for item in table_keys
                          if item.get("table") == reference["parent_table"]), {})
    child_row_key = list(child_table_key.get("pk", []))
    parent_row_key = list(parent_table_key.get("pk", []))
    if not child_row_key or not parent_row_key:
        return {**unavailable, "reason": "object_key_unavailable",
                "child_interval": [child_interval["start"]["ts_id"], child_interval["end"]["ts_id"]],
                "parent_interval": [parent_interval["start"]["ts_id"], parent_interval["end"]["ts_id"]]}
    child_q = quote_identifier(reference["child_table"])
    parent_q = quote_identifier(reference["parent_table"])
    expressions = [
        _qualified_time_sql(child_interval["start"], "c"),
        _qualified_time_sql(child_interval["end"], "c"),
        _qualified_time_sql(parent_interval["start"], "p"),
        _qualified_time_sql(parent_interval["end"], "p"),
    ]
    epochs = [f"(julianday({expression})-2440587.5)*86400.0" for expression in expressions]
    sql = (f"SELECT {_key_expression('c', child_row_key)}, "
           f"{_key_expression('p', parent_row_key)}, {', '.join(epochs)} "
           f"FROM {child_q} c JOIN {parent_q} p ON {_join_condition(reference)}")
    raw_rows = connection.execute(sql).fetchall()
    rows = [tuple(row) for row in raw_rows if all(value is not None for value in row[2:])]
    if not rows:
        return {**unavailable, "reason": "no_complete_linked_intervals",
                "child_interval": [child_interval["start"]["ts_id"], child_interval["end"]["ts_id"]],
                "parent_interval": [parent_interval["start"]["ts_id"], parent_interval["end"]["ts_id"]]}
    contained = sum(parent_start - tolerance_seconds <= child_start and
                    child_end <= parent_end + tolerance_seconds
                    for _, _, child_start, child_end, parent_start, parent_end in rows)
    before = sum(child_end < parent_start - tolerance_seconds
                 for _, _, _, child_end, parent_start, _ in rows)
    containment_ratio, before_ratio = contained / len(rows), before / len(rows)
    passed = containment_ratio >= containment_threshold
    return {
        "status": "passed" if passed else "failed", "passed": passed,
        "child_interval": [child_interval["start"]["ts_id"], child_interval["end"]["ts_id"]],
        "parent_interval": [parent_interval["start"]["ts_id"], parent_interval["end"]["ts_id"]],
        "linked_complete_intervals": len(rows),
        "interval_containment_ratio": containment_ratio,
        "child_before_parent_ratio": before_ratio,
        "sibling_overlap_ratio": _sibling_overlap_ratio(rows),
        "temporal_relation": "temporal_precedes" if before_ratio >= precedes_threshold else None,
        "tolerance_seconds": tolerance_seconds,
        "thresholds": {"interval_containment_ratio": containment_threshold,
                       "child_before_parent_ratio": precedes_threshold},
    }


def classify_table_references(references: list[dict[str, Any]], dd: dict[str, Any], *,
                              db_path: Path | None = None,
                              table_keys: list[dict[str, Any]] | None = None,
                              timestamps: list[dict[str, Any]] | None = None,
                              child_ref_threshold: float = 0.95,
                              multi_parent_threshold: float = 0.01,
                              containment_threshold: float = 0.95,
                              precedes_threshold: float = 0.95,
                              tolerance_seconds: int = 3600,
                              include_identity_candidates: bool = True) -> list[dict[str, Any]]:
    """PURPOSE: Separate identity, part-of and reference using text, key and interval evidence.
    INPUT: Verified references/DD, optional physical probes and an explicit legacy identity-candidate switch.
    OUTPUT: Semantic relation records; only valid part_of records are roll-up eligible.
    """
    records: list[dict[str, Any]] = []
    connection = (connect_readonly(db_path)
                  if db_path is not None else None)
    try:
        for reference in references:
            if reference.get("kind") == "polymorphic_ref":
                for member in reference.get("members", []):
                    records.append({
                        "id": f"OR:supertype:{reference['id']}:{member['object_id']}",
                        "kind": "supertype_member", "left": member["object_id"],
                        "right": None, "reference_id": reference["id"],
                        "validation_status": reference.get("validation_status", "ambiguous"),
                        "evidence": list(reference.get("evidence", [])),
                    })
                continue
            if not reference.get("parent_table") or not reference.get("columns"):
                source_columns = list(reference.get("source_columns", []))
                text = _dictionary_text(dd, reference.get("child_table", ""), source_columns)
                records.append({
                    "id": "OR:" + reference["id"], "kind": "reference",
                    "left": reference.get("child"), "right": reference.get("parent"),
                    "reference_id": reference["id"],
                    "validation_status": reference.get("validation_status", "ambiguous"),
                    "structural_evidence": None, "temporal_evidence": None,
                    "text_evidence": {"part_of_phrase_found": False,
                                      "same_object_phrase_found": False,
                                      "independent_object_phrase_found": False},
                    "decision_reason": "unresolvable_reference_shape",
                    "conflicting": False, "temporal_relation": None,
                    "evidence": [*reference.get("evidence", []), {"kind": "dd", "quote": text}],
                    "identity_policy": "requires_explicit_same_entity_and_executable_1_to_1_map",
                })
                continue
            child_columns = [pair[0] for pair in reference.get("columns", [])]
            text = _dictionary_text(dd, reference["child_table"], child_columns)
            relation_text = " ".join([*child_columns, text]).replace("_", " ")
            part_phrase = bool(PART_WORDS.search(relation_text))
            same_phrase = bool(SAME_WORDS.search(text))
            independent_phrase = bool(INDEPENDENT_WORDS.search(text))
            structural = (profile_structural_evidence(
                connection, reference, table_keys or [],
                child_ref_threshold=child_ref_threshold,
                multi_parent_threshold=multi_parent_threshold)
                if connection is not None else None)
            temporal = (profile_temporal_evidence(
                connection, reference, table_keys or [], timestamps or [], dd,
                containment_threshold=containment_threshold,
                precedes_threshold=precedes_threshold,
                tolerance_seconds=tolerance_seconds)
                if connection is not None else None)
            conflict = False
            if same_phrase and not independent_phrase and reference.get("cardinality") == "1:1":
                if include_identity_candidates:
                    kind, status, reason = "identity", "candidate_semantic_review", "documented_identity"
                else:
                    kind, status, reason = "reference", "valid", "instance_identity_deferred_to_semantic_type"
            elif structural is None:
                kind = "part_of" if part_phrase else "reference"
                status = "valid"
                reason = "documented_part_of" if part_phrase else "reference_only"
            elif not structural["passed"]:
                kind, status, reason = "reference", "valid", "structural_failed"
                conflict = part_phrase
            elif temporal and temporal["status"] == "passed":
                kind, status, reason = "part_of", "valid", "structural+temporal"
            elif temporal and temporal["status"] == "unavailable" and part_phrase:
                kind, status, reason = "part_of", "valid", "structural+text"
            elif temporal and temporal["status"] == "unavailable":
                kind, status, reason = "candidate_part_of", "candidate", "structural_only"
            else:
                kind, status, reason = "reference", "valid", (
                    "temporal_precedes" if temporal and temporal.get("temporal_relation")
                    else "temporal_containment_failed")
                conflict = part_phrase
            records.append({
                "id": "OR:" + reference["id"], "kind": kind,
                "left": reference.get("child"), "right": reference.get("parent"),
                "reference_id": reference["id"], "validation_status": status,
                "structural_evidence": structural,
                "temporal_evidence": temporal,
                "text_evidence": {"part_of_phrase_found": part_phrase,
                                  "same_object_phrase_found": same_phrase,
                                  "independent_object_phrase_found": independent_phrase},
                "decision_reason": reason, "conflicting": conflict,
                "temporal_relation": (temporal or {}).get("temporal_relation"),
                "evidence": [*reference.get("evidence", []), {"kind": "dd", "quote": text}],
                "identity_policy": "requires_explicit_same_entity_and_executable_1_to_1_map",
            })
        return sorted(records, key=lambda item: item["id"])
    finally:
        if connection is not None:
            connection.close()
