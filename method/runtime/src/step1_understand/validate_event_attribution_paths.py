"""Forward-only executable case paths, plus separate structural bridge/rollup inventories."""

from __future__ import annotations
from src.common.attribution_policy import MAX_ATTRIBUTION_HOPS, bounded_hops
from collections import defaultdict, deque
from pathlib import Path
from typing import Any
import json
import sqlite3
from src.common.attribution_policy import attribution_adjacency, database_path_issues, POLICY, reference_path_row_states, documented_reference_roles, role_source_scope_sql
from src.common.graph_identifiers import path_id, rollup_id
from src.common.normalize_relation_assessments import rollup_parent_table_key_id, rollup_record
from src.common.database_io import connect_readonly, quote_identifier


def discover_bridges(objects: list[dict[str, Any]], references: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """PURPOSE: Detect structural M:N bridge tables without treating them as identity concepts.
    INPUT: Physical Objects and reference edges.
    OUTPUT: Composite-key tables with at least two distinct declared FK targets.
    """
    object_by_table = {item["table"]: item for item in objects}
    by_child: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for reference in references:
        if reference.get("kind") == "declared":
            by_child[reference["child_table"]].append(reference)
    bridges = []
    for table, edges in sorted(by_child.items()):
        obj = object_by_table.get(table)
        targets = {edge["parent_table"] for edge in edges}
        fk_columns = {left for edge in edges for left, _ in edge.get("columns", [])}
        if not obj or len(targets) < 2 or len(obj.get("pk", [])) < 2:
            continue
        bridges.append({
            "table": table, "object_id": obj["id"], "pk": list(obj["pk"]),
            "fk_edge_ids": sorted(edge["id"] for edge in edges),
            "target_tables": sorted(targets),
            "pk_covers_foreign_keys": set(obj["pk"]) <= fk_columns,
            "validation_status": "valid" if set(obj["pk"]) <= fk_columns else "ambiguous",
            "evidence": [{"kind": "schema", "name": "composite_pk_fk_bridge",
                          "value": len(edges)}],
        })
    return bridges


def _adjacency(references: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """PURPOSE: Expose verified functional reference steps without merging distinct FK roles.
    INPUT: Native reference inventory. OUTPUT: Forward and UNIQUE-reverse attribution adjacency.
    """
    return attribution_adjacency(references)


def _simple_paths(adjacency: dict[str, list[dict[str, Any]]], source: str,
                  target: str, max_hops: int) -> list[list[dict[str, Any]]]:
    """PURPOSE: Enumerate every simple forward table path.
    INPUT: Oriented adjacency, source/target tables and optional legacy depth argument.
    OUTPUT: Ordered paths; a table can occur only once per path.
    """
    max_hops = bounded_hops(max_hops)
    if source == target:
        return [[]]
    predecessors = defaultdict(set)
    for origin, steps in adjacency.items():
        for step in steps:
            predecessors[step["right_table"]].add(origin)
    reachable = {target}
    frontier = [target]
    while frontier:
        for origin in predecessors[frontier.pop()] - reachable:
            reachable.add(origin)
            frontier.append(origin)
    if source not in reachable:
        return []
    found: list[list[dict[str, Any]]] = []
    queue = deque([(source, [], {source})])
    while queue:
        table, path, visited = queue.popleft()
        for edge in sorted(adjacency.get(table, []),
                           key=lambda item: (item["right_table"], item["relationship_id"])):
            nxt = edge["right_table"]
            if nxt in visited or nxt not in reachable:
                continue
            candidate = [*path, edge]
            if nxt == target:
                found.append(candidate)
            else:
                queue.append((nxt, candidate, visited | {nxt}))
    return sorted(found, key=lambda item: (len(item), [edge["relationship_id"] for edge in item]))


def _binding_predicate(binding: dict[str, Any], alias: str = "s0") -> tuple[str, list[Any]]:
    """PURPOSE: Restrict path validation to physical rows represented by one binding.
    INPUT: Native activity binding and SQL source alias.
    OUTPUT: Parameterized predicate and values.
    """
    clauses, parameters = [], []
    alpha = binding.get("alpha", {})
    if alpha.get("kind") == "value":
        clauses.append(f"{alias}.{quote_identifier(alpha['column'])}=?")
        parameters.append(alpha.get("value"))
    time_source = binding.get("occurrence_time_source", {})
    columns = time_source.get("columns", [])
    if time_source.get("json_path") and columns:
        clauses.append(f"json_extract({alias}.{quote_identifier(columns[0])}, ?) IS NOT NULL")
        parameters.append(time_source["json_path"])
    else:
        clauses.extend(f"{alias}.{quote_identifier(column)} IS NOT NULL" for column in columns)
    if documented := binding.get("documented_source_conditions"):
        from src.step3_execute.compile_event_log_sql import _condition
        clauses.extend(_condition({"source_condition": term}, alias=alias) for term in documented)
    return (" AND ".join(clauses) or "1=1"), parameters


def _json_key(alias: str, columns: list[str], *, type_tag: str | None = None) -> str:
    """PURPOSE: Serialize composite and typed case keys without lossy concatenation.
    INPUT: SQL alias, ordered physical columns and optional type tag.
    OUTPUT: SQLite json_array expression.
    """
    values = [f"{alias}.{quote_identifier(column)}" for column in columns]
    if type_tag is not None:
        values.insert(0, json.dumps(type_tag))
    return "json_array(" + ",".join(values) + ")"


def _validate_path(connection: sqlite3.Connection, binding: dict[str, Any],
                   source_key: list[str], target_table: str, target_key: list[str],
                   joins: list[dict[str, Any]], *, type_tag: str | None,
                   allow_many: bool, role_scope=None) -> tuple[dict[str, Any], str, list[Any]]:
    """PURPOSE: Execute a generated case map and measure source-to-case multiplicity.
    INPUT: DB, binding/key metadata, oriented joins, typed-key tag and M:N policy.
    OUTPUT: Validation metrics, deterministic parameterized map SQL and parameters. Rows whose
    reference is NULL along this path are reported and excluded from this path's proof; non-NULL
    unmatched, ambiguous or duplicated rows fail it, and a path with no attributable row never passes.
    """
    aliases = {binding["table"]: "s0"}
    from_sql = f"FROM {quote_identifier(binding['table'])} s0"
    current_alias = "s0"
    for index, edge in enumerate(joins, 1):
        alias = f"j{index}"
        condition = " AND ".join(
            f"{current_alias}.{quote_identifier(left)}={alias}.{quote_identifier(right)}"
            for left, right in zip(edge["left_columns"], edge["right_columns"]))
        from_sql += f" JOIN {quote_identifier(edge['right_table'])} {alias} ON {condition}"
        aliases[edge["right_table"]] = alias
        current_alias = alias
    target_alias = aliases.get(target_table, "s0")
    event_expr = _json_key("s0", source_key)
    case_expr = _json_key(target_alias, target_key, type_tag=type_tag)
    predicate, parameters = _binding_predicate(binding)
    total_source_rows = None
    if role_scope is not None:
        total_source_rows = connection.execute(
            f"SELECT COUNT(*) FROM {quote_identifier(binding['table'])} s0 WHERE {predicate}",
            parameters).fetchone()[0]
        predicate = f"({predicate}) AND {role_source_scope_sql(role_scope)}"
    map_sql = (f"SELECT {event_expr} AS source_event_id, {case_expr} AS case_id "
               f"{from_sql} WHERE {predicate}")
    rows = connection.execute(map_sql, parameters).fetchall()
    pairs = set(rows)
    per_source: dict[str, set[str]] = defaultdict(set)
    for event, case in pairs:
        per_source[event].add(case)
    states = reference_path_row_states(connection, binding["table"], joins, target_key,
                                       predicate=predicate, parameters=parameters,
                                       row_key_columns=source_key)
    ambiguous = sum(len(cases) > 1 for cases in per_source.values())
    attributable = states["scope_rows"] - states["null_reference_rows"]
    metrics = {
        "sql_executable": True, "source_rows": states["scope_rows"],
        "null_reference_rows": states["null_reference_rows"],
        "attributable_source_rows": attributable,
        "matched_source_rows": len(per_source),
        "unmatched_source_rows": states["unmatched_reference_rows"],
        "zero_case_source_rows": states["scope_rows"] - len(per_source),
        "ambiguous_source_rows": ambiguous,
        "duplicate_source_case_pairs": len(rows) - len(pairs),
        "projected_pairs": len(pairs), "max_cases_per_source": max(
            (len(cases) for cases in per_source.values()), default=0),
        "attribution_policy": "many_cases_allowed" if allow_many else "single_case_required",
        "null_policy": "null_reference_not_attributable_via_this_path",
    }
    if total_source_rows is not None:
        metrics.update(all_source_rows=total_source_rows,
                       out_of_role_source_rows=total_source_rows-states['scope_rows'])
    metrics["passed"] = (attributable > 0 and metrics["unmatched_source_rows"] == 0 and
                         metrics["duplicate_source_case_pairs"] == 0 and
                         (allow_many or ambiguous == 0))
    return metrics, map_sql, parameters


def enumerate_attribution_paths(db_path: Path, bindings: list[dict[str, Any]],
                                objects: list[dict[str, Any]], concepts: list[dict[str, Any]],
                                references: list[dict[str, Any]], bridges: list[dict[str, Any]],
                                rollups: list[dict[str, Any]] | None = None,
                                *, max_hops: int = MAX_ATTRIBUTION_HOPS,
                                dictionary: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """PURPOSE: Enumerate source-local and functional declared-reference case paths.
    INPUT: DBU physical/logical graph and legacy depth argument.
    OUTPUT: Event-to-concept path records with executable case maps and provenance. Status is valid
    (observed proof), rule_confirmed_no_occurrences (no in-scope row; supported identification rule on
    the same path), no_attributable_rows, invalid or ambiguous; 0/0 is never an observed success.
    """
    max_hops = bounded_hops(max_hops)
    object_by_id = {item["id"]: item for item in objects}
    object_by_table = {item["table"]: item for item in objects}
    adjacency = _adjacency(references)
    rollups = rollups or []
    paths: list[dict[str, Any]] = []
    joins_by_endpoint = {}
    validation_by_scope = {}
    connection = connect_readonly(db_path)
    try:
        adjacency = {table: [e for e in edges if not database_path_issues(connection, [e])]
                     for table, edges in adjacency.items()}
        reference_roles = documented_reference_roles(adjacency, dictionary or {})
        for binding in sorted(bindings, key=lambda item: item["id"]):
            source_object = object_by_table.get(binding["table"])
            if not source_object:
                continue
            for concept in concepts:
                provider_ids = ({m['representation_id'] for m in concept['population']['maps']}
                                if concept.get('population') else set(concept.get('members', [])))
                for member_id in sorted(provider_ids):
                    target = object_by_id[member_id]
                    endpoints = (binding["table"], target["table"])
                    if endpoints not in joins_by_endpoint:
                        groups = {}
                        for joins in _simple_paths(adjacency, *endpoints, max_hops):
                            shape = tuple((edge['left_table'], tuple(edge['left_columns']),
                                           edge['right_table'], tuple(edge['right_columns']),
                                           edge['direction'], edge['declared'],
                                           edge['relationship_id'] if edge['relationship_id'] in reference_roles else None)
                                          for edge in joins)
                            groups.setdefault(shape, []).append(joins)
                        joins_by_endpoint[endpoints] = list(groups.values())
                    documented = {tuple(edge['relationship_id'] for edge in rule.get('joins', []))
                                  for rule in concept.get('identification_rules', [])
                                  if rule.get('status') == 'supported'
                                  and rule.get('source', {}).get('table') == binding['table']
                                  and rule.get('canonical_table') == target['table']}
                    groups = [sorted(group, key=lambda joins: (
                        tuple(edge['relationship_id'] for edge in joins) not in documented,
                        [edge['relationship_id'] for edge in joins]))
                              for group in joins_by_endpoint[endpoints]]
                    for joins, *provenance in sorted(groups, key=lambda group: (
                            tuple(edge['relationship_id'] for edge in group[0]) not in documented,
                            not any(edge['relationship_id'] in reference_roles for edge in group[0]),
                            sum(not edge['declared'] for edge in group[0]), len(group[0]))):
                        # Scope the first role on a source-local path, before counting unmatched rows.
                        role_hop = next((i for i, hop in enumerate(joins)
                            if hop['direction'] == 'parent_to_child'
                            and hop['relationship_id'] in reference_roles
                            and all(edge['direction'] == 'child_to_parent' and edge['declared']
                                    for edge in joins[:i])), None)
                        role_edge = reference_roles[joins[role_hop]['relationship_id']] if role_hop is not None else None
                        role_scope = ({'kind': 'reference_role', 'prefix': joins[:role_hop],
                                       'step': role_edge['step'], 'alternatives': role_edge['alternatives']}
                                      if role_edge else None)
                        case_role = (reference_roles.get(joins[-1]['relationship_id'])
                                     if joins and joins[-1]['direction'] == 'child_to_parent' else None)
                        allow_many = False
                        semantic_status = "valid"
                        kind = "own" if not joins else "reference"
                        type_tag = target["table"] if concept["kind"] == "supertype" else None
                        predicate, parameters = _binding_predicate(binding)
                        scope_key = json.dumps([endpoints, source_object["pk"], target["pk"],
                                                 predicate, [(type(v).__name__, repr(v)) for v in parameters],
                                                 type_tag, role_scope,
                                                 [(edge["relationship_id"], edge["direction"]) for edge in joins]],
                                                sort_keys=True, default=str)
                        if scope_key not in validation_by_scope:
                            validation_by_scope[scope_key] = _validate_path(
                                connection, binding, source_object["pk"], target["table"], target["pk"],
                                joins, type_tag=type_tag, allow_many=allow_many, role_scope=role_scope)
                        raw_validation, map_sql, map_parameters = validation_by_scope[scope_key]
                        validation = dict(raw_validation)
                        status = ("ambiguous" if semantic_status == "ambiguous" else
                                  semantic_status if validation["passed"] else
                                  "no_attributable_rows" if validation["attributable_source_rows"] == 0
                                  else "invalid")
                        if role_scope and validation['zero_case_source_rows']:
                            status = 'invalid'
                            validation['passed'] = False
                        edge_ids = [edge["relationship_id"] for edge in joins]
                        selected_rollups = [
                            rollup["id"] for rollup in rollups
                            if rollup_parent_table_key_id(rollup) == target["id"] and
                            all(any(
                                edge["relationship_id"] == step["relationship_id"] and
                                edge["left_table"] == step["left_table"] and
                                edge["right_table"] == step["right_table"] and
                                edge["direction"] == "child_to_parent"
                                for edge in joins)
                                for step in rollup.get("joins", []))]
                        if selected_rollups and kind == "reference":
                            kind = "rollup"
                        identifier = path_id(binding["id"], concept["id"],
                                             [*edge_ids, target["id"]])
                        identification_rules = [rule for rule in concept.get('identification_rules', [])
                            if rule.get('status') == 'supported' and rule.get('source', {}).get('table') == binding['table']
                            and rule.get('canonical_table') == target['table']
                            and [e['relationship_id'] for e in rule.get('joins', [])] == edge_ids]
                        reason = ('role_path_has_unmapped_events'
                                  if role_scope and validation['zero_case_source_rows'] else None)
                        if status == "no_attributable_rows" and validation["source_rows"] == 0:
                            # Nothing occurred, so nothing was observed. A supported whole-Table identification
                            # rule on this exact path still fixes where an occurrence would be attributed.
                            if identification_rules:
                                status = "rule_confirmed_no_occurrences"
                                validation["observation_status"] = "no_in_scope_rows"
                                validation["rule_basis"] = "supported_identification_rule_on_same_path"
                            else:
                                reason = "no_in_scope_source_rows_and_unconfirmed_rule"
                        elif status == "no_attributable_rows":
                            reason = "all_references_null_on_path"
                        paths.append({
                            "identification_rule_ids": sorted(rule['id'] for rule in identification_rules),
                            "entity_subject_rule_ids": sorted(rule['id'] for rule in identification_rules
                                if rule.get('representation_role') in {'primary_subject','additional_attributes','alternate_identifier','event_subject'}),
                            "id": identifier, 'event_definition_id': binding["id"], "kind": kind,
                            "from_table": binding["table"], "to": concept["id"],
                            'target_table_key_id': target["id"], "edge_ids": edge_ids,
                            "joins": joins, "rollup_ids": selected_rollups,
                            **({"equivalent_reference_chains": [[edge['relationship_id'] for edge in variant]
                                                                 for variant in provenance]} if provenance else {}),
                            "attribution_policy": POLICY,
                            "case_map": {"id": "CM:" + identifier.split(":", 1)[1],
                                         'source_event_definition_id': binding["id"],
                                         "source_event_key_columns": list(source_object["pk"]),
                                         "source_object_type": source_object["id"],
                                         "target_concept_id": concept["id"],
                                         "case_key_fields": concept["case_key"]["fields"],
                                         "map_sql": map_sql,
                                         "map_parameters": map_parameters,
                                         "cardinality": "M:N" if allow_many else "N:1",
                                         "provenance_edge_ids": edge_ids,
                                         "validation": validation},
                            "cardinality": "M:N" if allow_many else "N:1",
                            "validation_status": status,
                            **({"role_validation": {"reference": role_edge, "status": "pass"}} if role_edge else {}),
                            **({"role_scope": role_scope} if role_scope else {}),
                            **({"case_role": case_role} if case_role else {}),
                            **({"reason_code": reason} if reason else {}),
                            "evidence": [{"kind": "reference_path", "edge_ids": edge_ids},
                                         {"kind": "case_map_validation", **validation}],
                        })
        return sorted(paths, key=lambda item: item["id"])
    finally:
        connection.close()


def build_rollups(table_keys: list[dict[str, Any]], relation_records: list[dict[str, Any]],
                  references: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """PURPOSE: Turn rollup-eligible Table references (valid part_of) into opt-in rollup candidates.
    INPUT: Table + Key records, internal relation records and executable structural references.
    OUTPUT: Child-to-parent candidates naming child/parent Tables and their table_key_id; no
            lifecycle membership or row-level attribution success is implied.
    """
    refs = {item["id"]: item for item in references}
    result = []
    for relation in relation_records:
        if relation.get("kind") != "part_of" or relation.get("validation_status") != "valid":
            continue
        reference = refs.get(relation["reference_id"])
        if not reference or reference.get("kind") not in {"declared", "inferred_ref"}:
            continue
        identifier = rollup_id(relation["left"], relation["right"], [reference["id"]])
        result.append({
            **rollup_record(identifier, relation, reference), "edge_ids": [reference["id"]],
            "joins": [{"relationship_id": reference["id"],
                       "left_table": reference["child_table"],
                       "left_columns": [item[0] for item in reference["columns"]],
                       "right_table": reference["parent_table"],
                       "right_columns": [item[1] for item in reference["columns"]],
                       "direction": "child_to_parent"}],
            "depth": 1, "rollup_eligible": True, "selection_policy": "query_conditioned",
            "validation_status": "valid", "evidence": list(relation.get("evidence", [])),
        })
    return sorted(result, key=lambda item: item["id"])


def attach_concept_paths(bindings: list[dict[str, Any]], paths: list[dict[str, Any]]) -> None:
    """PURPOSE: Attach compact concept-path references to native bindings in place.
    INPUT: Native bindings and fully validated attribution paths.
    OUTPUT: None; physical legacy paths remain unchanged.
    """
    by_binding: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for path in paths:
        by_binding[path['event_definition_id']].append(path)
    for binding in bindings:
        binding["concept_paths"] = sorted(by_binding.get(binding["id"], []),
                                          key=lambda item: item["id"])
