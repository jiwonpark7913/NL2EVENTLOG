"""Select uncertain event interpretations for bounded table-local model review."""

from __future__ import annotations
from pathlib import Path
from typing import Any
import hashlib
import sqlite3
from src.eeg.evidence_graph_models import Table
from src.common.database_io import quote_identifier
from src.step1_understand.interpret_event_definitions import measure_value_clocks
from src.common.database_io import connect_readonly


def database_content_digest(path: Path) -> str:
    """PURPOSE: Invalidate cached semantic reviews when database bytes change.
    INPUT: Path to the read-only SQLite snapshot.
    OUTPUT: Streaming SHA-256 digest; does not modify the source database.
    """
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def table_uncertainties(table: Table, state: dict[str, Any], trace: dict[str, Any],
                        bindings: list[dict[str, Any]],
                        timestamps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """PURPOSE: List what public evidence left undecided for one table, after deterministic
    interpretation. Settled outcomes (supported events, documented non-occurrence clocks,
    rejected non-carriers) are not uncertainties.
    INPUT: Table, temporal state, carrier trace, current bindings (with activity semantics) and units.
    OUTPUT: Stable records {kind, id, reason}; an empty list means no review call.
    """
    if not state.get("ts_ids"):
        return []
    local_units = {item["ts_id"]: item for item in timestamps if item["ts_id"] in state["ts_ids"]}
    local = [b for b in bindings if b.get("table") == table.name]
    supported_times = {b.get("ts_id") for b in local if b.get("interpretation_status") == "supported"}
    from src.common.event_clock import NON_OCCURRENCE_ROLES
    settled_non_occurrence = NON_OCCURRENCE_ROLES
    result = []
    for ts_id, unit in sorted(local_units.items()):
        role, status = unit.get("semantic_role", "unknown"), unit.get("role_status", "unknown")
        if ts_id in supported_times or (role in settled_non_occurrence and status == "supported"):
            continue
        if status != "supported" or role == "unknown":
            result.append({"kind": "timestamp_unit", "id": ts_id,
                           "reason": "time_role_unresolved", "current_role": role})
    for binding in local:
        if binding.get("interpretation_status") == "supported":
            continue
        unit = local_units.get(binding.get("ts_id"), {})
        if unit.get("semantic_role") in settled_non_occurrence and unit.get("role_status") == "supported":
            continue
        semantics = binding.get("activity_semantics", {})
        reason = ("activity_meaning_" + semantics.get("status", "unresolved")
                  if semantics.get("status") != "supported" else
                  "occurrence_" + str(semantics.get("occurrence_reason", "unresolved")))
        if binding.get("timestamp_pairing", {}).get("status") == "candidate":
            reason = "value_timestamp_pairing_uncertain"
        result.append({"kind": "event_definition", "id": binding["id"], "reason": reason})
    evaluations = trace.get("activity_evaluations", [])
    accepted = [item for item in evaluations if item.get("accepted")]
    for item in evaluations:
        if item.get("plausible_carrier") and not item.get("accepted") and item.get(
                "evidence_status") != "rejected":
            result.append({"kind": "carrier_candidate", "id": item["column_id"],
                           "reason": "carrier_candidate_unconfirmed"})
    if len(accepted) > 1:
        result.append({"kind": "carrier_candidate", "id": table.id, "reason": "competing_carriers",
                       "columns": [item["column_id"] for item in accepted]})
    return result


def candidate_interpretation_inventory(db_path: Path, tables: list[Table],
                                       classifications: dict[str, dict[str, Any]],
                                       traces: dict[str, dict[str, Any]],
                                       timestamps: list[dict[str, Any]],
                                       profiles: dict[str, Any]) -> list[dict[str, Any]]:
    """PURPOSE: Preserve row and non-carrier alternatives before model review.
    INPUT: Read-only DB, temporal states, rule traces and value profiles.
    OUTPUT: Per-table candidate inventory; displayed pairings are bounded samples.
    """
    time_by_id = {item["ts_id"]: item for item in timestamps}
    result = []
    connection = connect_readonly(db_path)
    try:
        for table in sorted(tables, key=lambda item: item.name):
            state = classifications[table.name]
            if not state.get("ts_ids"):
                continue
            carriers = []
            for evaluation in traces[table.name].get("activity_evaluations", []):
                if not evaluation.get("plausible_carrier"):
                    continue
                column = evaluation["column"]
                profile = profiles[table.name]["columns"][column]
                sample = profile["frequent_values"][:8]
                units = [time_by_id[ts_id] for ts_id in state["ts_ids"]]
                pairings = [{
                    "value": observed["value"],
                    "status": "independent_clock_review",
                    "clock_support": measure_value_clocks(connection,table.name,column,observed["value"],units),
                } for observed in sample]
                observed_values = traces[table.name].get("observed_carrier_values", {}).get(column)
                carriers.append({
                    "observed_values": observed_values or [],
                    "observed_values_status": ("complete_non_null_domain" if observed_values is not None
                                               else "not_enumerated_carrier_unadmitted"),
                    "column_id": evaluation["column_id"],
                    "status": "candidate",
                    "generated_binding_candidates": bool(evaluation["accepted"]),
                    "semantic_evidence_status": evaluation.get("evidence_status", "unresolved"),
                    "distinct_count": profile["distinct_count"],
                    "sample_values": [item["value"] for item in sample],
                    "sample_is_full_domain": profile["distinct_count"] <= len(sample),
                    "sample_pairing_evidence": pairings,
                    "criteria": {key: evaluation.get(key) for key in ("C1", "C2", "C3", "C4")},
                    "review_reasons": evaluation.get("review_reasons", []),
                })
            result.append({
                "table": table.name, "timestamp_unit_ids": list(state["ts_ids"]),
                "carrier_candidates": carriers,
                "non_carrier_candidates": [{
                    "timestamp_unit_id": ts_id,
                    "semantic_role": time_by_id[ts_id].get("semantic_role", "unknown"),
                    "status": "candidate",
                } for ts_id in state["ts_ids"]],
            })
        return result
    finally:
        connection.close()


def direct_fk_neighbor_context(table: Table, tables: list[Table],
                               dd: dict[str, Any]) -> list[dict[str, Any]]:
    """PURPOSE: Supply one-hop FK schema context without expanding the review to distant tables.
    INPUT: Focal table, complete physical table inventory and normalized public dictionary.
    OUTPUT: Sorted direct-neighbor names, keys and dictionary definitions only.
    """
    names = set()
    edges: dict[str, list[dict[str, Any]]] = {}
    for candidate in tables:
        for fk in candidate.foreign_keys:
            parent = fk.get("parent_table")
            if candidate.name == table.name and parent:
                names.add(parent)
                edges.setdefault(parent, []).append({
                    "child_table": candidate.name, "parent_table": parent,
                    "columns": fk.get("columns", [])})
            if parent == table.name:
                names.add(candidate.name)
                edges.setdefault(candidate.name, []).append({
                    "child_table": candidate.name, "parent_table": parent,
                    "columns": fk.get("columns", [])})
    descriptions = {item["table"]: item for item in dd["tables"]}
    return [{"table": candidate.name, "primary_key": list(candidate.primary_key),
             "definition": descriptions.get(candidate.name, {}).get("definition", ""),
             "foreign_key_edges": edges.get(candidate.name, [])}
            for candidate in sorted(tables, key=lambda item: item.name)
            if candidate.name in names and candidate.name != table.name]


def representative_rows(db_path: Path, table: Table, candidate_columns: list[str],
                        timestamp_columns: list[str], limit: int = 8) -> list[dict[str, Any]]:
    """PURPOSE: Show bounded source rows that cover distinct candidate carrier values.
    INPUT: Read-only DB, physical table, candidate/time column names and maximum rows.
    OUTPUT: At most `limit` rows with only keyed, candidate and temporal fields.
    """
    if limit < 1:
        return []
    known = {column.name for column in table.columns}
    selected = [name for name in dict.fromkeys([
        *table.primary_key, *candidate_columns, *timestamp_columns]) if name in known][:16]
    if not selected:
        return []
    quoted_table = quote_identifier(table.name)
    projection = ", ".join(quote_identifier(name) for name in selected)
    order = ", ".join(quote_identifier(name) for name in table.primary_key if name in known)
    if not order:
        order = "rowid"
    connection = connect_readonly(db_path)
    connection.row_factory = sqlite3.Row
    try:
        rows: list[dict[str, Any]] = []
        seen: set[tuple[str, ...]] = set()
        for carrier in candidate_columns:
            if carrier not in selected:
                continue
            values = connection.execute(
                f"SELECT {quote_identifier(carrier)} FROM {quoted_table} "
                f"WHERE {quote_identifier(carrier)} IS NOT NULL "
                f"GROUP BY {quote_identifier(carrier)} "
                f"ORDER BY COUNT(*) DESC, {quote_identifier(carrier)} LIMIT ?", (limit,))
            for (value,) in values:
                row = connection.execute(
                    f"SELECT {projection} FROM {quoted_table} "
                    f"WHERE {quote_identifier(carrier)} = ? ORDER BY {order} LIMIT 1", (value,)).fetchone()
                if row is None:
                    continue
                record = {name: row[name] for name in selected}
                identity = tuple(str(record[name]) for name in (table.primary_key or selected))
                if identity not in seen:
                    rows.append(record)
                    seen.add(identity)
                if len(rows) >= limit:
                    return rows
        for row in connection.execute(
                f"SELECT {projection} FROM {quoted_table} ORDER BY {order} LIMIT ?", (limit,)):
            record = {name: row[name] for name in selected}
            identity = tuple(str(record[name]) for name in (table.primary_key or selected))
            if identity not in seen:
                rows.append(record)
                seen.add(identity)
            if len(rows) >= limit:
                break
        return rows
    finally:
        connection.close()


def validate_rebuilt_bindings(db_path: Path, table: Table,
                              bindings: list[dict[str, Any]],
                              timestamps: list[dict[str, Any]]) -> list[str]:
    """PURPOSE: Check a proposed table binding bundle before replacing the draft.
    INPUT: Read-only DB, focal schema, proposed bindings and discovered time units.
    OUTPUT: Structural/temporal violation codes; empty list permits atomic application.
    """
    errors = []
    known_columns = {column.name for column in table.columns}
    time_by_id = {item["ts_id"]: item for item in timestamps if item["table"] == table.name}
    ids = [item.get("id") for item in bindings]
    if not bindings:
        return ["empty_rebuilt_binding_bundle"]
    if len(ids) != len(set(ids)):
        errors.append('duplicate_event_definition_id')
    connection = connect_readonly(db_path)
    try:
        for binding in bindings:
            if binding.get("table") != table.name:
                errors.append("binding_from_other_table")
            ts_id = binding.get("ts_id")
            unit = time_by_id.get(ts_id)
            if unit is None:
                errors.append("unknown_or_foreign_timestamp")
            elif (binding.get("event_kind") == "business" and
                  unit.get("semantic_role") in {"scheduled_time", "ingestion_time"}):
                errors.append("business_event_uses_non_occurrence_time")
            alpha = binding.get("alpha", {})
            if alpha.get("kind") == "value":
                column = alpha.get("column")
                if column not in known_columns:
                    errors.append("unknown_carrier_column")
                    continue
                observed = connection.execute(
                    f"SELECT 1 FROM {quote_identifier(table.name)} "
                    f"WHERE {quote_identifier(column)} = ? LIMIT 1", (alpha.get("value"),)).fetchone()
                if observed is None:
                    errors.append("unobserved_carrier_value")
            elif alpha.get("kind") in {"table", "column"}:
                if not str(alpha.get("name") or "").strip():
                    errors.append("missing_table_activity_name")
            else:
                errors.append("unsupported_review_binding_kind")
        return sorted(set(errors))
    finally:
        connection.close()


def summarize_temporal_source_roles(tables: list[Table],
                                    timestamps: list[dict[str, Any]],
                                    bindings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """PURPOSE: Summarize observed temporal roles without asserting an activity occurred.
    INPUT: Physical tables, discovered time units and final candidate bindings.
    OUTPUT: Multi-label table summaries with the temporal units behind each label.
    """
    mapped = {"business_occurrence": "business", "scheduled_time": "planned",
              "ingestion_time": "technical"}
    result = []
    for table in sorted(tables, key=lambda item: item.name):
        local_times = [item for item in timestamps if item["table"] == table.name]
        roles: dict[str, set[str]] = {}
        for unit in local_times:
            role = mapped.get(unit.get("semantic_role"), "unknown")
            roles.setdefault(role, set()).add(unit["ts_id"])
        for binding in bindings:
            if binding.get("table") != table.name:
                continue
            kind = binding.get("event_kind")
            if kind in {"business", "planned", "technical", "unknown"}:
                roles.setdefault(kind, set()).add(binding["ts_id"])
        result.append({"table": table.name,
                       "roles": [{"role": role, "timestamp_unit_ids": sorted(ids)}
                                 for role, ids in sorted(roles.items())]})
    return result
