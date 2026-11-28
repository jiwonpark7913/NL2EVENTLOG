"""Bounded SQL profiling for ES-relevant slots."""

from __future__ import annotations
from pathlib import Path
from typing import Any
import json
import re
from src.common.database_io import connect_readonly, quote_identifier
from src.eeg.evidence_graph_models import Table
BUSINESS_ATTRIBUTE_WORDS = {
    "status", "state", "type", "category", "class", "kind", "name", "title", "label",
    "description", "role", "channel", "method", "reason", "purpose", "product", "service",
}


def _safe_value(value: Any) -> Any:
    """PURPOSE: Keep profile samples JSON serializable and bounded.
    INPUT: Arbitrary SQLite scalar.
    OUTPUT: Scalar or bounded hexadecimal/text representation.
    """
    if isinstance(value, bytes):
        return value[:64].hex()
    if isinstance(value, str):
        return value[:500]
    return value


def profile_tables(db_path: Path, tables: list[Table], sample_size: int) -> dict[str, Any]:
    """PURPOSE: Compute deterministic column statistics in SQL without loading full tables.
    INPUT: Read-only DB, physical schema and per-column sample bound.
    OUTPUT: Table/column profiles including FK repetition evidence.
    """
    connection = connect_readonly(db_path)
    profiles: dict[str, Any] = {}
    try:
        for table in tables:
            qt = quote_identifier(table.name)
            row_count = int(connection.execute(f"SELECT COUNT(*) FROM {qt}").fetchone()[0])
            order = ", ".join(quote_identifier(key) for key in table.primary_key) or "rowid"
            columns = {}
            for column in table.columns:
                qc = quote_identifier(column.name)
                null_count, distinct_count = connection.execute(
                    f"SELECT SUM({qc} IS NULL), COUNT(DISTINCT {qc}) FROM {qt}").fetchone()
                storage = {str(kind): int(count) for kind, count in connection.execute(
                    f"SELECT typeof({qc}), COUNT(*) FROM {qt} GROUP BY typeof({qc}) ORDER BY typeof({qc})")}
                first = [_safe_value(row[0]) for row in connection.execute(
                    f"SELECT {qc} FROM {qt} WHERE {qc} IS NOT NULL ORDER BY {order} LIMIT ?", (sample_size,))]
                frequent = [{"value": _safe_value(value), "count": int(count)} for value, count in connection.execute(
                    f"SELECT {qc}, COUNT(*) AS n FROM {qt} WHERE {qc} IS NOT NULL "
                    f"GROUP BY {qc} ORDER BY n DESC, CAST({qc} AS TEXT) LIMIT ?", (sample_size,))]
                columns[column.name] = {
                    "row_count": row_count, "null_count": int(null_count or 0),
                    "distinct_count": int(distinct_count or 0), "storage_types": storage,
                    "sample_values": first, "frequent_values": frequent,
                }
            fk_repeat = {}
            for fk in table.foreign_keys:
                child = [left for left, _ in fk["columns"]]
                expressions = ", ".join(quote_identifier(item) for item in child)
                if len(child) == 1:
                    distinct = connection.execute(
                        f"SELECT COUNT(DISTINCT {expressions}) FROM {qt} WHERE {expressions} IS NOT NULL").fetchone()[0]
                else:
                    distinct = connection.execute(
                        f"SELECT COUNT(*) FROM (SELECT DISTINCT {expressions} FROM {qt})").fetchone()[0]
                nonnull = connection.execute(
                    f"SELECT COUNT(*) FROM {qt} WHERE " + " AND ".join(
                        f"{quote_identifier(item)} IS NOT NULL" for item in child)).fetchone()[0]
                fk_repeat["+".join(child)] = int(nonnull) > int(distinct)
            profiles[table.name] = {"row_count": row_count, "columns": columns, "fk_repeat": fk_repeat}
        return profiles
    finally:
        connection.close()


def business_value_evidence(db_path: Path, tables: list[Table], dd: dict[str, Any],
                            profiles: dict[str, Any], sample_size: int) -> list[dict[str, Any]]:
    """PURPOSE: Expose bounded, row-coherent business attributes as supplementary semantic evidence.
    INPUT: Read-only DB, physical schema, normalized DD, existing profiles and per-table row bound.
    OUTPUT: Citable table-scoped evidence; identifiers/timestamps and raw rows outside the bound are excluded.
    """
    column_dd = {(item["table"], item["column"]): item for item in dd.get("columns", [])}
    records = []
    connection = connect_readonly(db_path)
    try:
        for table in tables:
            key_columns = set(table.primary_key)
            key_columns.update(column for key in table.unique_keys for column in key)
            key_columns.update(left for foreign in table.foreign_keys for left, _ in foreign.get("columns", []))
            candidates = []
            for column in table.columns:
                profile = profiles.get(table.name, {}).get("columns", {}).get(column.name, {})
                dictionary = column_dd.get((table.name, column.name), {})
                words = set(re.findall(
                    r"[a-z]+", (column.name + " " + str(dictionary.get("readable_name", "")) + " " +
                                str(dictionary.get("definition", ""))).casefold()))
                temporal = bool(words & {"time", "timestamp", "date", "datetime", "occurred", "recorded"})
                textual = "TEXT" in column.declared_type.upper() or "CHAR" in column.declared_type.upper()
                if (column.name not in key_columns and textual and not temporal and
                        words & BUSINESS_ATTRIBUTE_WORDS and profile.get("distinct_count", 0) > 0):
                    candidates.append(column.name)
            candidates = candidates[:6]
            if not candidates:
                continue
            projection = ", ".join(quote_identifier(column) for column in candidates)
            nonempty = " OR ".join(f"{quote_identifier(column)} IS NOT NULL" for column in candidates)
            order = ", ".join(quote_identifier(key) for key in table.primary_key) or "rowid"
            rows = connection.execute(
                f"SELECT {projection} FROM {quote_identifier(table.name)} WHERE {nonempty} "
                f"ORDER BY {order} LIMIT ?", (sample_size,)).fetchall()
            row_values = [[_safe_value(value) for value in row] for row in rows]
            frequencies = {column: profiles[table.name]["columns"][column].get("frequent_values", [])[:sample_size]
                           for column in candidates}
            payload = {"columns": candidates, "rows": row_values, "frequent_values": frequencies,
                       "row_coherent": True, "sample_limit": sample_size, "truncated": len(rows) == sample_size}
            records.append({"id": f"V:{table.name}:business_values", "table": table.name,
                            "field": "observed_business_values", "evidence_kind": "observed_value",
                            "text": json.dumps(payload, ensure_ascii=False, sort_keys=True),
                            "scope": "supplementary_semantic_evidence_not_identity_or_grouping_proof"})
        return records
    finally:
        connection.close()
