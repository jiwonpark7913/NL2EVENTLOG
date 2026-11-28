"""Declared FK relations and child-to-parent attribution paths."""

from __future__ import annotations
from collections import defaultdict, deque
from pathlib import Path
from typing import Any
import re
from src.common.data_dictionary import dictionary_indexes
from src.common.graph_identifiers import table_key_id, relation_id
from src.common.database_io import connect_readonly, quote_identifier
from src.eeg.evidence_graph_models import Table, representative_key


def _identifier_tokens(value: str) -> set[str]:
    """PURPOSE: Produce conservative semantic tokens for undeclared identifier matching.
    INPUT: Physical table or column name.
    OUTPUT: Lowercase tokens with generic key suffixes removed.
    """
    return {token for token in re.findall(r"[a-z0-9]+", value.casefold())
            if token not in {"id", "key", "no", "number", "code"}}


def build_relations(db_path: Path, tables: list[Table], dd: dict[str, Any], key_profiles=None) -> list[dict[str, Any]]:
    """PURPOSE: Create only declared PK–FK edges and measure child uniqueness.
    INPUT: DB, physical tables and optional documented relation descriptions.
    OUTPUT: Child-to-parent relation records with cardinality evidence.
    """
    object_tables = {table.name for table in tables if representative_key(table, key_profiles) is not None}
    dd_relations = {(item["child"], tuple(item["child_columns"]), item["parent"], tuple(item["parent_columns"])): item
                    for item in dd.get("relations", [])}
    connection = connect_readonly(db_path)
    result = []
    try:
        for table in tables:
            if table.name not in object_tables:
                continue
            for fk in table.foreign_keys:
                if fk["parent_table"] not in object_tables:
                    continue
                pairs = list(fk["columns"])
                columns = [left for left, _ in pairs]
                qt = quote_identifier(table.name)
                select = ", ".join(quote_identifier(item) for item in columns)
                where = " AND ".join(f"{quote_identifier(item)} IS NOT NULL" for item in columns)
                rows = int(connection.execute(f"SELECT COUNT(*) FROM {qt} WHERE {where}").fetchone()[0])
                distinct = int(connection.execute(f"SELECT COUNT(*) FROM (SELECT DISTINCT {select} FROM {qt} WHERE {where})").fetchone()[0])
                documented = dd_relations.get((table.name, tuple(columns), fk["parent_table"], tuple(right for _, right in pairs)))
                evidence = [{"kind":"stat","name":"child_rows","value":rows},
                            {"kind":"stat","name":"distinct_fk","value":distinct},
                            {"kind":"rule","id":"R4.declared_fk","outcome":"accepted"}]
                if documented:
                    evidence.insert(0, {"kind":"dd","ref":documented["id"],"quote":documented.get("description","")})
                result.append({"id": relation_id(table.name, pairs, fk["parent_table"]),
                    "child": table_key_id(table.name), "parent": table_key_id(fk["parent_table"]),
                    "child_table": table.name, "parent_table": fk["parent_table"],
                    "columns": [[left, right] for left, right in pairs],
                    "cardinality": "1:1" if rows == distinct else "N:1", "evidence": evidence})
        declared_shapes = {(item["child_table"], tuple(left for left, _ in item["columns"]),
                            item["parent_table"], tuple(right for _, right in item["columns"]))
                           for item in result}
        declared_child_columns = {
            (item["child_table"], left)
            for item in result if item.get("declared", True)
            for left, _ in item["columns"]
        }
        dd_columns = dictionary_indexes(dd)["columns"]
        for child in tables:
            for column in child.columns:
                # A declared FK fixes the meaning of its child column. Local identifier
                # values can overlap across independent parent tables, so proposing a
                # second value-overlap parent here creates a false attribution path.
                if (column.name in child.primary_key or
                        (child.name, column.name) in declared_child_columns):
                    continue
                column_dd = dd_columns.get((child.name, column.name), {})
                identifier_like = ("identifier" in str(column_dd.get("representation_class", "")).casefold()
                                   or bool(_identifier_tokens(column.name)) and
                                   any(token in column.name.casefold() for token in ("id", "key", "no")))
                if not identifier_like:
                    continue
                child_tokens = _identifier_tokens(column.name)
                child_values = {row[0] for row in connection.execute(
                    f"SELECT DISTINCT {quote_identifier(column.name)} FROM {quote_identifier(child.name)} "
                    f"WHERE {quote_identifier(column.name)} IS NOT NULL")}
                if not child_values:
                    continue
                for parent in tables:
                    if parent.name == child.name or len(parent.primary_key) != 1:
                        continue
                    parent_column = parent.primary_key[0]
                    shape = (child.name, (column.name,), parent.name, (parent_column,))
                    if shape in declared_shapes:
                        continue
                    parent_tokens = _identifier_tokens(parent_column)
                    if not child_tokens.intersection(parent_tokens):
                        continue
                    parent_values = {row[0] for row in connection.execute(
                        f"SELECT DISTINCT {quote_identifier(parent_column)} FROM {quote_identifier(parent.name)} "
                        f"WHERE {quote_identifier(parent_column)} IS NOT NULL")}
                    overlap = child_values.intersection(parent_values)
                    child_coverage = len(overlap) / len(child_values)
                    parent_coverage = len(overlap) / len(parent_values) if parent_values else 0.0
                    if not overlap or child_coverage < 0.95:
                        continue
                    rows = int(connection.execute(
                        f"SELECT COUNT(*) FROM {quote_identifier(child.name)} WHERE "
                        f"{quote_identifier(column.name)} IS NOT NULL").fetchone()[0])
                    distinct = len(child_values)
                    pairs = [(column.name, parent_column)]
                    result.append({
                        "id": relation_id(child.name, pairs, parent.name),
                        "child": table_key_id(child.name), "parent": table_key_id(parent.name),
                        "child_table": child.name, "parent_table": parent.name,
                        "columns": [[column.name, parent_column]],
                        "cardinality": "1:1" if rows == distinct else "N:1",
                        "candidate_status": "verified_value_overlap", "declared": False,
                        "evidence": [
                            {"kind": "stat", "name": "exact_inclusion", "value": child_coverage},
                            {"kind": "stat", "name": "overlap_distinct", "value": len(overlap)},
                            {"kind": "stat", "name": "child_coverage", "value": child_coverage},
                            {"kind": "stat", "name": "parent_coverage", "value": parent_coverage},
                            {"kind": "rule", "id": "R4.value_inclusion", "outcome": "accepted"},
                        ],
                    })
        return sorted(result, key=lambda item: item["id"])
    finally:
        connection.close()


def attach_paths(bindings: list[dict[str, Any]], relations: list[dict[str, Any]], objects: list[dict[str, Any]], max_hops: int) -> None:
    """PURPOSE: Attach every simple 0..k child-to-parent path to each binding in place.
    INPUT: Binding list, declared relations, Objects and hop limit.
    OUTPUT: None; each binding receives sorted path records.
    """
    object_by_table = {item["table"]: item["id"] for item in objects}
    outgoing: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for relation in relations:
        outgoing[relation["child_table"]].append(relation)
    for binding in bindings:
        paths = []
        if binding["table"] in object_by_table:
            paths.append({"to": object_by_table[binding["table"]], "edges": [], "cardinality": "1:1"})
        queue = deque([(binding["table"], [], {binding["table"]})])
        while queue:
            table, edges, visited = queue.popleft()
            for relation in sorted(outgoing.get(table, []), key=lambda item: item["id"]):
                parent = relation["parent_table"]
                if parent in visited:
                    continue
                next_edges = edges + [relation["id"]]
                paths.append({"to": object_by_table[parent], "edges": next_edges,
                              "cardinality": "N:1" if any(
                                  next(item for item in relations if item["id"] == edge)["cardinality"] == "N:1"
                                  for edge in next_edges) else "1:1"})
                queue.append((parent, next_edges, visited | {parent}))
        binding["paths"] = sorted(paths, key=lambda item: (len(item["edges"]), item["to"], item["edges"]))
