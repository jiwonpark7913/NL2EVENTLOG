"""Exact key profiling for Object Type and attribution discovery."""

from __future__ import annotations
from pathlib import Path
from typing import Any
from src.common.database_io import connect_readonly, quote_identifier
from src.eeg.evidence_graph_models import Table


def _tuple_expression(columns: list[str]) -> str:
    """PURPOSE: Render an ordered SQLite key projection.
    INPUT: One nonempty physical column group.
    OUTPUT: Comma-separated quoted identifiers.
    """
    if not columns:
        raise ValueError("Key columns must not be empty")
    return ", ".join(quote_identifier(column) for column in columns)


def profile_keys(db_path: Path, tables: list[Table]) -> list[dict[str, Any]]:
    """PURPOSE: Measure declared PK/UNIQUE keys exactly without unsafe prefix sampling.
    INPUT: Read-only SQLite DB and loaded physical tables.
    OUTPUT: Stable key records with null, distinct, uniqueness and format evidence.
    """
    connection = connect_readonly(db_path)
    records: list[dict[str, Any]] = []
    try:
        for table in sorted(tables, key=lambda item: item.name):
            groups: list[tuple[str, list[str]]] = []
            if table.primary_key:
                groups.append(("pk", list(table.primary_key)))
            groups.extend(("ak", list(key)) for key in table.unique_keys
                          if list(key) != list(table.primary_key))
            for kind, columns in groups:
                projection = _tuple_expression(columns)
                source = quote_identifier(table.name)
                row_count = int(connection.execute(f"SELECT COUNT(*) FROM {source}").fetchone()[0])
                null_predicate = " OR ".join(
                    f"{quote_identifier(column)} IS NULL" for column in columns)
                null_count = int(connection.execute(
                    f"SELECT COUNT(*) FROM {source} WHERE {null_predicate}").fetchone()[0])
                distinct_count = int(connection.execute(
                    f"SELECT COUNT(*) FROM (SELECT DISTINCT {projection} FROM {source} "
                    f"WHERE NOT ({null_predicate}))").fetchone()[0])
                sample = connection.execute(
                    f"SELECT {projection} FROM {source} WHERE NOT ({null_predicate}) "
                    f"ORDER BY {projection} LIMIT 32").fetchall()
                values = [value for row in sample for value in row]
                records.append({
                    "id": f"K:{table.name}:{'+'.join(columns)}", "table": table.name,
                    "kind": kind, "columns": columns, "row_count": row_count,
                    "null_count": null_count, "distinct_count": distinct_count,
                    "unique": null_count == 0 and distinct_count == row_count,
                    "small_int": bool(values) and all(
                        isinstance(value, int) and abs(value) < 10000 for value in values),
                    "format_sig": sorted({type(value).__name__ for value in values}),
                    "sampling": {"mode": "exact_counts_deterministic_prefix_display_only",
                                 "approval_uses_sample": False, "display_sample_size": len(sample)},
                })
        return records
    finally:
        connection.close()
