"""Deterministic, Gold-free process diagnostics for extracted Event Logs."""

from __future__ import annotations
from collections import Counter, defaultdict
from src.common.timestamp_policy import event_time_order
from typing import Any


def _case_key(value: Any) -> str | None:
    """PURPOSE: Normalize a case identifier without changing its semantic components.
    INPUT: Scalar/list case identifier.
    OUTPUT: Stable text, or null when no attribution exists.
    """
    if value is None or value == "":
        return None
    if isinstance(value, (list, tuple)):
        return "[" + ",".join(str(item) for item in value) + "]"
    return str(value)


def _event_identity(row: dict[str, Any]) -> tuple[Any, ...] | None:
    """PURPOSE: Derive a source occurrence identity for duplicate diagnostics.
    INPUT: Event row with event/source provenance fields.
    OUTPUT: Hashable identity, or null when provenance is insufficient.
    """
    event_id = row.get("event_id") or row.get("occurrence_key")
    if event_id not in (None, ""):
        return ("event_id", str(event_id))
    source_timestamp_column = row.get("source_timestamp_column", row.get("source_field"))
    source = (row.get("source_table"), row.get("source_key"), source_timestamp_column,
              row.get("source_timestamp_path"), tuple(row.get("source_timestamp_component_columns") or []))
    if any(value not in (None, "") for value in source):
        return ("source", *(str(value or "") for value in source))
    return None


def build_process_summary(
        event_log: list[dict[str, Any]], *, query_id: str,
        target_object_type: str | None = None,
        requested_scope: dict[str, Any] | None = None,
        execution: dict[str, Any] | None = None,
        compiler_diagnostics: dict[str, Any] | None = None,
        top_n: int = 10, provenance_limit: int = 50) -> dict[str, Any]:
    """PURPOSE: Convert an Event Log into the bounded diagnostic schema from the protocol.
    INPUT: Gold-free rows, query/object/scope context, execution diagnostics and output caps.
    OUTPUT: JSON-safe activity, DFG, trace, attribution, time and provenance summary.
    """
    execution = execution or {"status": "success", "error_stage": None, "warnings": []}
    requested_scope = requested_scope or {
        "explicit_activities": [], "scope_cues": [], "is_multi_activity": None}
    compiler_diagnostics = compiler_diagnostics or {}
    normalized, invalid_times = [], []
    for index, row in enumerate(event_log):
        timestamp = row.get("occurrence_timestamp", row.get("timestamp"))
        time_key = event_time_order(row)
        if time_key[0] == 2:
            invalid_times.append({"index": index, "value": str(timestamp)})
        normalized.append({
            "case_id": _case_key(row.get("case_id")),
            "activity_id": str(row.get("activity_id") or row.get("canonical_activity_id") or
                               row.get("activity") or ""),
            "label": str(row.get("activity") or row.get("label") or ""),
            "timestamp": None if timestamp in (None, "") else str(timestamp),
            "time_key": time_key,
            "event_identity": _event_identity(row),
            "source_table": row.get("source_table"),
            "source_key": row.get("source_key"),
            "source_timestamp_column": row.get("source_timestamp_column", row.get("source_field")),
            "source_timestamp_path": row.get("source_timestamp_path"),
            "source_timestamp_component_columns": list(row.get("source_timestamp_component_columns") or []),
            "index": index,
        })
    activity_counts = Counter((row["activity_id"], row["label"]) for row in normalized)
    traces: dict[str, list[dict[str, Any]]] = defaultdict(list)
    unattributed = 0
    for row in normalized:
        if row["case_id"] is None:
            unattributed += 1
            continue
        traces[row["case_id"]].append(row)
    edges, starts, ends, variants = Counter(), Counter(), Counter(), Counter()
    equal_time_groups = []
    incomparable_cases = 0
    activity_cases: dict[str, set[str]] = defaultdict(set)
    for case_id, rows in traces.items():
        ordered = sorted(rows, key=lambda item: (
            item["time_key"], str(item["event_identity"] or ""), item["index"]))
        by_time = defaultdict(list)
        for row in ordered:
            if row["time_key"][0] < 2:
                by_time[row["time_key"]].append(row["timestamp"])
            activity_cases[row["label"]].add(case_id)
        for values in by_time.values():
            if len(values) > 1:
                equal_time_groups.append({"case_id": case_id, "timestamp": values[0],
                                          "event_count": len(values),
                                          "interpretation": "tie_order_is_deterministic_not_causal"})
        domains = {row["time_key"][:2] for row in ordered}
        if len(domains) != 1 or any(row["time_key"][0] >= 2 for row in ordered):
            incomparable_cases += 1
            continue
        labels = tuple(row["label"] for row in ordered)
        if labels:
            starts[labels[0]] += 1
            ends[labels[-1]] += 1
            edges.update(zip(labels, labels[1:]))
            variants[labels] += 1
    identities = Counter(row["event_identity"] for row in normalized
                         if row["event_identity"] is not None)
    duplicate_count = sum(count - 1 for count in identities.values() if count > 1)
    null_by_activity, totals_by_activity = Counter(), Counter()
    for row in normalized:
        totals_by_activity[row["label"]] += 1
        if row["timestamp"] is None:
            null_by_activity[row["label"]] += 1
    case_count = len(traces)
    variant_rows = [{"activities": list(trace), "count": count}
                    for trace, count in variants.most_common(top_n)]
    edge_rows = [{"source": left, "target": right, "count": count}
                 for (left, right), count in edges.most_common(top_n)]
    provenance = {}
    for row in normalized[:provenance_limit]:
        key = row["activity_id"] or row["label"]
        provenance.setdefault(key, []).append({
            "source_table": row["source_table"], "source_key": row["source_key"],
            "source_timestamp_column": row["source_timestamp_column"],
            "source_timestamp_path": row["source_timestamp_path"]})
    null_join = compiler_diagnostics.get("null_join_rate_by_path") or {}
    limitations = [
        "DFG edges describe observed order and are not normative process requirements.",
        "Equal timestamps are ordered by source identity and input index; that order is not causal.",
    ]
    if incomparable_cases:
        limitations.append("Cases with incomparable clock domains or invalid clocks are excluded from inferred order.")
    if len(edges) > top_n or len(variants) > top_n:
        limitations.append("DFG edges or trace variants were truncated to configured top-N.")
    if len(normalized) > provenance_limit:
        limitations.append("Source provenance examples were truncated.")
    if not event_log:
        limitations.append("No DFG was inferred because the initial log is empty or unavailable.")
    observed_labels = {row["label"].casefold() for row in normalized if row["label"]}
    explicit = [str(item) for item in requested_scope.get("explicit_activities", [])]
    missing_explicit = [item for item in explicit if item.casefold() not in observed_labels]
    diagnostic_signals = []
    if missing_explicit:
        diagnostic_signals.append({
            "type": "potential_under_extraction",
            "code": "query_explicit_activity_not_observed",
            "activities": missing_explicit,
            "interpretation": "signal_only_requires_semantic_and_graph_verification",
        })
    return {
        "query_id": query_id, "target_object_type": target_object_type,
        "requested_scope": requested_scope,
        "execution": {
            "status": execution.get("status", "success"),
            "error_stage": execution.get("error_stage"),
            "warnings": list(execution.get("warnings") or []),
        },
        "activity_counts": [
            {"activity_id": activity_id, "label": label, "count": count}
            for (activity_id, label), count in sorted(activity_counts.items())],
        "dfg_edges": edge_rows,
        "start_activity_counts": dict(sorted(starts.items())),
        "end_activity_counts": dict(sorted(ends.items())),
        "case_count": case_count, "event_count": len(normalized),
        "singleton_case_count": sum(len(rows) == 1 for rows in traces.values()),
        "singleton_ratio": (sum(len(rows) == 1 for rows in traces.values()) / case_count
                            if case_count else None),
        "trace_variants_top_n": variant_rows,
        "per_activity_case_coverage": {
            activity: len(cases) / case_count if case_count else None
            for activity, cases in sorted(activity_cases.items())},
        "unattributed_event_count": unattributed,
        "null_join_rate_by_path": null_join,
        "duplicate_event_key_count": duplicate_count,
        "timestamp_null_rate_by_activity": {
            activity: null_by_activity[activity] / total
            for activity, total in sorted(totals_by_activity.items())},
        "timestamp_order_anomalies": [*invalid_times, *equal_time_groups[:top_n]],
        "diagnostic_signals": diagnostic_signals,
        "source_event_provenance": provenance,
        "ordering_policy": "absolute_instant_or_local_wall_time_then_source_identity",
        "incomparable_clock_case_count": incomparable_cases,
        "truncation": {"top_n": top_n, "provenance_limit": provenance_limit,
                       "dfg_edges_truncated": len(edges) > top_n,
                       "variants_truncated": len(variants) > top_n},
        "limitations": limitations,
    }
