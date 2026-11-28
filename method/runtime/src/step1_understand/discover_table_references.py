"""Exact declared, inferred and polymorphic reference diagnostics."""

from __future__ import annotations
from collections import defaultdict
from pathlib import Path
from typing import Any
import re
import sqlite3
from src.common.graph_identifiers import relation_id
from src.common.database_io import connect_readonly, quote_identifier
from src.eeg.evidence_graph_models import Table


def _tokens(value: str) -> set[str]:
    """PURPOSE: Normalize identifier semantics for conservative reference discovery.
    INPUT: Physical name or Data Dictionary definition.
    OUTPUT: Lowercase non-generic alphanumeric tokens.
    """
    generic = {"id", "key", "no", "number", "identifier", "identity", "the", "or"}
    return {token for token in re.findall(r"[a-z0-9]+", str(value).casefold())
            if token not in generic}


def _column_dictionary(dd: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    """PURPOSE: Index public column definitions without consulting evaluation Gold.
    INPUT: Normalized Data Dictionary.
    OUTPUT: Mapping keyed by physical table and column.
    """
    if dd.get("columns"):
        return {(column["table"], column["column"]): column
                for column in dd.get("columns", [])}
    return {(table["table"], column["name"]): column
            for table in dd.get("tables", []) for column in table.get("columns", [])}


def _values(connection: sqlite3.Connection, table: str, columns: list[str]) -> set[tuple[Any, ...]]:
    """PURPOSE: Read an exact non-null composite-key domain for final reference approval.
    INPUT: Read-only connection, table and ordered columns.
    OUTPUT: Tuple domain; NULL-containing keys are excluded.
    """
    projection = ", ".join(quote_identifier(column) for column in columns)
    predicate = " AND ".join(f"{quote_identifier(column)} IS NOT NULL" for column in columns)
    return set(connection.execute(
        f"SELECT DISTINCT {projection} FROM {quote_identifier(table)} WHERE {predicate}"))


def discover_references(db_path: Path, tables: list[Table], dd: dict[str, Any],
                        declared: list[dict[str, Any]], *, inclusion_threshold: float = 0.95,
                        member_share: float = 0.05, max_members: int = 3) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """PURPOSE: Enrich declared references and discover exact inferred/polymorphic candidates.
    INPUT: DB/schema/DD, declared relations and configurable discovery thresholds.
    OUTPUT: Reference edges plus diagnostics; ambiguous polymorphic values never auto-resolve.
    """
    columns_dd = _column_dictionary(dd)
    discriminator_specs = {
        (str(item.get("source_table")), str(item.get("source_column"))): item
        for item in dd.get("polymorphic_references", [])
        if item.get("source_table") and item.get("source_column")
    }
    table_by_name = {table.name: table for table in tables}
    target_keys = []
    seen_target_keys = set()
    for table in tables:
        groups = ([('pk', table.primary_key)] if table.primary_key else []) + [
            ('ak', key) for key in table.unique_keys]
        for key_kind, key in groups:
            identity = (table.name, tuple(key))
            if key and identity not in seen_target_keys:
                target_keys.append((table.name, list(key), key_kind))
                seen_target_keys.add(identity)
    declared_shapes = {(item["child_table"], tuple(left for left, _ in item["columns"]),
                        item["parent_table"], tuple(right for _, right in item["columns"]))
                       for item in declared if item.get("declared", True)}
    references = []
    for item in declared:
        record = dict(item)
        is_declared = item.get("declared", True)
        record.update({"kind": "declared" if is_declared else "inferred_ref",
                       "declared": is_declared,
                       "validation_status": "valid"})
        child = table_by_name[item['child_table']]
        columns = [left for left, _ in item['columns']]
        record['child_key_unique'] = bool(is_declared and any(
            len(key) == len(columns) and set(key) == set(columns)
            for key in [child.primary_key, *child.unique_keys]))
        references.append(record)
    diagnostics: list[dict[str, Any]] = []
    connection = connect_readonly(db_path)
    try:
        domains = {(table, tuple(columns)): _values(connection, table, columns)
                   for table, columns, _ in target_keys}
        for child in sorted(tables, key=lambda item: item.name):
            declared_child_columns = {left for relation in declared
                                      if relation.get("declared", True)
                                      if relation["child_table"] == child.name
                                      for left, _ in relation["columns"]}
            for column in child.columns:
                if column.name in declared_child_columns or column.name in child.primary_key:
                    continue
                definition = columns_dd.get((child.name, column.name), {})
                semantic = " ".join((column.name, definition.get("definition", ""),
                                     str(definition.get("representation_class", ""))))
                if not (re.search(r"\b(references?|refers? to)\b", semantic, re.I) or "identifier" in semantic.casefold() or
                        re.search(r"(?:^|_)(?:id|key|no|number)$", column.name, re.I)):
                    continue
                source_values = _values(connection, child.name, [column.name])
                if not source_values:
                    continue
                source_tokens = _tokens(semantic)
                matches = []
                for parent, key_columns, key_kind in target_keys:
                    if parent == child.name or len(key_columns) != 1:
                        continue
                    shape = (child.name, (column.name,), parent, tuple(key_columns))
                    if shape in declared_shapes:
                        continue
                    target_semantic = parent + " " + key_columns[0] + " " + str(
                        columns_dd.get((parent, key_columns[0]), {}).get("definition", ""))
                    semantic_support = bool(source_tokens & _tokens(target_semantic))
                    overlap = source_values & domains[(parent, tuple(key_columns))]
                    if not overlap:
                        continue
                    matches.append({"table": parent, "columns": key_columns,
                                    "key_kind": key_kind,
                                    "values": overlap, "semantic_support": semantic_support,
                                    "coverage": len(overlap) / len(source_values)})
                strong = [item for item in matches
                          if item["coverage"] >= inclusion_threshold and item["semantic_support"]]
                if len(strong) == 1:
                    target = strong[0]
                    pairs = [(column.name, target["columns"][0])]
                    references.append({
                        "id": relation_id(child.name, pairs, target["table"]),
                        "child": f"O:{child.name}", "parent": f"O:{target['table']}",
                        "child_table": child.name, "parent_table": target["table"],
                        "columns": [[left, right] for left, right in pairs],
                        "cardinality": "N:1", "kind": "inferred_ref", "declared": False,
                        "candidate_status": "exact_verified", "validation_status": "valid",
                        "reference_evidence": {
                            "status": "supported" if re.search(
                                r"\b(references?|refers? to)\b", definition.get("definition", ""), re.I)
                                and re.search(r"(?<!\w)" + re.escape(target['table']) + r"(?!\w)",
                                              definition.get("definition", ""), re.I) else "candidate",
                            "source": "dictionary_reference_definition",
                            "quote": definition.get("definition", ""),
                            "source_table": child.name, "source_columns": [column.name],
                            "target_table": target['table'], "target_columns": target['columns'],
                            "exact_inclusion": target['coverage'],
                            "matched_distinct": len(target['values']),
                            "source_distinct": len(source_values),
                            "denominator": "distinct_non_null_source_tuples",
                            "null_policy": "exclude_null_containing_tuples",
                            "threshold": inclusion_threshold},
                        "evidence": [{"kind": "stat", "name": "exact_inclusion",
                                      "value": target["coverage"]},
                                     {"kind": "dd", "quote": definition.get("definition", "")}],
                    })
                    continue
                members = [item for item in matches
                           if item["key_kind"] == "pk"
                           if item["semantic_support"] and
                           len(item["values"]) / len(source_values) >= member_share]
                members = sorted(members, key=lambda item: (-len(item["values"]), item["table"]))[:max_members]
                union = set().union(*(item["values"] for item in members)) if members else set()
                if len(members) < 2 or len(union) / len(source_values) < inclusion_threshold:
                    continue
                counts = defaultdict(int)
                for member in members:
                    for value in member["values"]:
                        counts[value] += 1
                ambiguous = {value for value, count in counts.items() if count > 1}
                unmatched = source_values - union
                discriminator = None
                discriminator_spec = discriminator_specs.get((child.name, column.name))
                if discriminator_spec:
                    discriminator_column = discriminator_spec.get("discriminator_column")
                    mapping = discriminator_spec.get("mapping", {})
                    table_mapping = {
                        str(tag): (value.get("table") if isinstance(value, dict) else value)
                        for tag, value in mapping.items()
                    }
                    valid_member_tables = {item["table"] for item in members}
                    if (discriminator_column in {item.name for item in child.columns} and
                            set(table_mapping.values()) <= valid_member_tables):
                        projection = (f"SELECT DISTINCT {quote_identifier(column.name)}, "
                                      f"{quote_identifier(discriminator_column)} FROM "
                                      f"{quote_identifier(child.name)} WHERE "
                                      f"{quote_identifier(column.name)} IS NOT NULL")
                        rows = connection.execute(projection).fetchall()
                        unresolved_rows = 0
                        for raw_value, tag in rows:
                            target_table = table_mapping.get(str(tag))
                            target_table_key_id = next((item for item in members
                                                  if item["table"] == target_table), None)
                            if (target_table_key_id is None or
                                    (raw_value,) not in target_table_key_id["values"]):
                                unresolved_rows += 1
                        if unresolved_rows == 0:
                            ambiguous = set()
                            discriminator = {
                                "column": discriminator_column,
                                "mapping": table_mapping,
                                "validated_distinct_rows": len(rows),
                                "unresolved_distinct_rows": 0,
                            }
                stem = re.sub(r"(?:_?(?:id|key|no|number))$", "", column.name, flags=re.I)
                discriminator_hints = [item.name for item in child.columns
                                       if item.name != column.name and
                                       re.search(r"(?:type|table|class|kind)$", item.name, re.I) and
                                       (not stem or stem.casefold() in item.name.casefold())]
                generic = bool(any("table" in item.casefold() for item in discriminator_hints)
                               and discriminator is None)
                reference_id = ("R:generic:" if generic else "R:poly:") + child.name + "." + column.name
                record = {
                    "id": reference_id,
                    "kind": "generic_reference" if generic else "polymorphic_ref",
                    "declared": False,
                    "child": f"O:{child.name}", "child_table": child.name,
                    "source_columns": [column.name],
                    "members": [{"object_id": f"O:{item['table']}", "table": item["table"],
                                 "key_columns": item["columns"],
                                 "matched_distinct": len(item["values"]),
                                 "member_share": len(item["values"]) / len(source_values)}
                                for item in members],
                    "resolution": {"resolved_distinct": len(union - ambiguous),
                                   "ambiguous_distinct": len(ambiguous),
                                   "unmatched_distinct": len(unmatched),
                                   "typed_identity": True,
                                   "discriminator": discriminator},
                    "validation_status": "warning" if generic else "ambiguous" if ambiguous else "valid",
                    "automatic_attribution": False if generic else not ambiguous,
                    "thresholds": {"inclusion": inclusion_threshold,
                                   "member_share": member_share, "max_members": max_members},
                    "evidence": [{"kind": "dd", "quote": definition.get("definition", "")},
                                 {"kind": "schema", "name": "discriminator_hints",
                                  "value": discriminator_hints},
                                 {"kind": "stat", "name": "exact_union_coverage",
                                  "value": len(union) / len(source_values)}],
                }
                references.append(record)
                diagnostics.append(record)
                references = [item for item in references if not (
                    item.get("kind") == "inferred_ref" and item.get("child_table") == child.name
                    and any(pair[0] == column.name for pair in item.get("columns", [])))]
        return sorted({item["id"]: item for item in references}.values(), key=lambda item: item["id"]), sorted(
            diagnostics, key=lambda item: item["id"])
    finally:
        connection.close()
