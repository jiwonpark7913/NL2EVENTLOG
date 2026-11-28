"""Candidate-constrained Process View selection over an Evidence Graph."""

from __future__ import annotations
from src.common.attribution_policy import MAX_ATTRIBUTION_HOPS, bounded_hops, DEFAULT_MAX_REVISIONS
from collections import defaultdict, deque
from src.common.attribution_policy import attribution_adjacency, path_issues, POLICY
from typing import Any
from src.common.schema_metadata import normalize


def _norm(value: Any) -> str:
    """PURPOSE: Normalize optional evidence text without assuming a non-null string.
    INPUT: Arbitrary scalar.
    OUTPUT: Repository-standard normalized text or an empty string.
    """
    return normalize(str(value)) if value not in (None, "") else ""


def _binding_text(binding: dict[str, Any], graph: dict[str, Any]) -> str:
    """PURPOSE: Compose bounded semantic evidence for one enumerated activity binding.
    INPUT: Runtime binding and graph with public Data Dictionary descriptions.
    OUTPUT: Search/model text; excludes Gold data and executable SQL.
    """
    parts = [binding.get("activity_label"), binding.get("activity"), binding.get("source_table"),
             binding.get("activity_column"), *binding.get("raw_values", []),
             *binding.get("alternative_labels", [])]
    semantics = binding.get("activity_semantics") or {}
    parts.extend([semantics.get("code_meaning"), semantics.get("event_label"),
                  *(e.get("text", "") for e in semantics.get("evidence", []))])
    timestamp_columns = set(binding.get("timestamp_columns", []))
    for timestamp in binding.get("timestamp_candidates", []):
        timestamp_columns.update(timestamp.get("columns", []))
        if timestamp.get("column"):
            timestamp_columns.add(timestamp["column"])
    dictionary = graph.get("data_dictionary") or {}
    for table in dictionary.get("tables", []):
        if table.get("table", table.get("table_name")) == binding.get("source_table"):
            parts.extend([table.get("definition"), table.get("description"), table.get("row_meaning")])
    for column in dictionary.get("columns", []):
        table = column.get("table", column.get("table_name"))
        name = column.get("column", column.get("column_name"))
        if table == binding.get("source_table") and (
                name == binding.get("activity_column") or name in timestamp_columns):
            parts.extend([column.get("definition"), column.get("description"),
                          column.get("time_semantics")])
            domain = column.get("value_domain") or {}
            for raw_value in binding.get("raw_values", []):
                meaning = domain.get(str(raw_value)) or {}
                if isinstance(meaning, dict):
                    parts.extend([meaning.get("label"), meaning.get("definition")])
                elif meaning:
                    parts.append(meaning)
    return " ".join(str(part) for part in parts if part not in (None, ""))


def selectable_objects(graph: dict[str, Any]) -> list[dict[str, Any]]:
    """PURPOSE: Return validated logical case concepts, with physical Objects as a legacy fallback.
    INPUT: Runtime Evidence Graph from the native adapter or an older graph fixture.
    OUTPUT: Stable selectable case-object records; invalid/ambiguous concepts are excluded.
    """
    concepts = [item for item in graph.get('entity_types', [])
                if item.get("validation_status", "valid") == "valid"]
    return concepts or list(graph.get('table_key_records', []))


def _binding_record(item: dict[str, Any], graph: dict[str, Any], *,
                    include_semantic_signature: bool = True) -> dict[str, Any]:
    """PURPOSE: Reduce an activity binding to an enumerated semantic selection record.
    INPUT: Runtime activity binding and Evidence Graph.
    OUTPUT: Stable ID, label, source, timestamp and semantic evidence.
    """
    timestamps = []
    for candidate in item.get("timestamp_candidates", []):
        columns = candidate.get("columns") or ([candidate["column"]]
                                                if candidate.get("column") else [])
        timestamps.append({"timestamp_id": candidate.get("id"), "columns": columns,
                           "role": candidate.get("role", "unknown")})
    signature = item.get("semantic_signature") or {}
    compact_signature = ({key: signature.get(key) for key in (
        "action", "transition", "temporal_role", "interpretation_status", "description", "alternatives")}
        if include_semantic_signature else {})
    return {'event_definition_id': item["id"], "activity": item.get("activity_label") or item.get("activity"),
            "source_table": item.get("source_table"), "source_kind": item.get("source_kind"),
            "activity_column": item.get("activity_column"),
            "activity_source": item.get("activity_source"),
            "timestamp_pairing": item.get("timestamp_pairing"),
            "occurrence_identity_rule_id": item.get("occurrence_identity_rule_id"),
            "object_association_ids": list(item.get("object_association_ids", [])),
            "conflict_relation_ids": list(item.get("conflict_relation_ids", [])),
            "carrier_role": item.get("carrier_role"),
            "raw_values": list(item.get("raw_values", []))[:12], "timestamps": timestamps,
            "semantic_signature": compact_signature,
            "activity_semantics": item.get("activity_semantics", {}),
            "interpretation_status": item.get("interpretation_status"),
            "validation_status": item.get("validation_status"),
            "validation_evidence": item.get("validation_evidence", []),
            "uncertainty": item.get("uncertainty", []), "conflicts": item.get("conflicts", []),
            "structural_object_links": list(item.get('event_entity_links', [])),
            "semantic_evidence": _binding_text(item, graph)}


def attribution_paths(graph: dict[str, Any], source_table: str, target_table: str,
                      max_hops: int = MAX_ATTRIBUTION_HOPS, max_paths: int = 3) -> list[dict[str, Any]]:
    """PURPOSE: Find functional declared FK paths, allowing schema-proved UNIQUE reverse steps.
    INPUT: Evidence Graph, source/target tables and path bounds.
    OUTPUT: Reachable paths marked attributable or ambiguous; no SQL is generated.
    """
    max_hops = bounded_hops(max_hops)
    if source_table == target_table:
        return [{"source_table": source_table, "target_table": target_table,
                 "hop_count": 0, "edges": [], "attribution_status": "attributable"}]
    adjacency = defaultdict(list)
    for child, steps in attribution_adjacency(graph.get('relationships', [])).items():
        for step in steps:
            adjacency[child].append((step['right_table'], {**step,
                'from_table':child, 'to_table':step['right_table']}))
    queue = deque([(source_table, [], {source_table})])
    paths = []
    while queue and len(paths) < max_paths:
        table, edges, visited = queue.popleft()
        for neighbour, edge in sorted(adjacency.get(table, []),
                                      key=lambda item: (str(item[1].get("relationship_id")), item[0])):
            if neighbour in visited:
                continue
            next_edges = [*edges, edge]
            if neighbour == target_table:
                paths.append({'source_table':source_table, 'target_table':target_table,
                    'hop_count':len(next_edges), 'edges':next_edges, 'attribution_status':'attributable',
                    'path_kind':'forward_declared_reference', 'attribution_policy':POLICY})
            else:
                queue.append((neighbour, next_edges, {*visited, neighbour}))
    return paths


def assess_attribution(graph: dict[str, Any], source_table: str, target_table: str,
                       max_hops: int = MAX_ATTRIBUTION_HOPS, max_paths: int = 3) -> dict[str, Any]:
    """PURPOSE: Separate graph reachability from defensible case attribution.
    INPUT: Evidence Graph, source and target tables, and bounded-search settings.
    OUTPUT: attributable, ambiguous, or unreachable_within_bound with path evidence.
    """
    max_hops = bounded_hops(max_hops)
    paths = attribution_paths(graph, source_table, target_table, max_hops, max_paths)
    if not paths:
        status = "unreachable_within_bound"
    elif any(path["attribution_status"] == "attributable" for path in paths):
        status = "attributable"
    else:
        status = "ambiguous"
    return {"status": status, "reachable": bool(paths), "paths": paths,
            "max_hops": max_hops, "search_bound": "bounded_not_proof_of_disconnection"}


def assess_object_attribution(graph: dict[str, Any], source_table: str,
                              target: dict[str, Any], *, max_hops: int = MAX_ATTRIBUTION_HOPS,
                              max_paths: int = 3) -> dict[str, Any]:
    """PURPOSE: Assess activity attribution against every member of a logical Object Type.
    INPUT: Runtime graph, source table, selected object/concept and bounded-search settings.
    OUTPUT: Best status and all member-specific assessments for validation/audit.
    """
    max_hops = bounded_hops(max_hops)
    member_tables = list(dict.fromkeys(
        table for table in target.get("member_tables", [target.get("anchor_table")]) if table))
    member_assessments = [assess_attribution(
        graph, source_table, table, max_hops=max_hops, max_paths=max_paths)
        for table in member_tables]
    priority = {"attributable": 0, "ambiguous": 1, "unreachable_within_bound": 2}
    best = min(member_assessments, key=lambda item: priority.get(item["status"], 3)) \
        if member_assessments else {
            "status": "unreachable_within_bound", "reachable": False, "paths": [],
            "max_hops": max_hops, "search_bound": "bounded_not_proof_of_disconnection"}
    return {**best, "target_object_id": target.get("id"),
            "matched_member_table": next((table for table, assessment in zip(
                member_tables, member_assessments) if assessment is best), None),
            "member_assessments": member_assessments}


def assess_binding_attribution(graph: dict[str, Any], binding: dict[str, Any],
                               target: dict[str, Any], *, max_hops: int = MAX_ATTRIBUTION_HOPS,
                               max_paths: int = 3) -> dict[str, Any]:
    """PURPOSE: Reuse validated binding-to-concept paths before falling back to table BFS.
    INPUT: Evidence Graph, one activity binding, selected object and path bounds.
    OUTPUT: Attribution status with binding-native or fallback path evidence.
    """
    max_hops = bounded_hops(max_hops)
    target_ids = {str(target.get("id")), *map(str, target.get("member_object_ids", []))}
    native_paths = []
    for path in binding.get("concept_paths", []):
        validation = (path.get("case_map") or {}).get("validation") or {}
        if (str(path.get("to")) in target_ids and path.get("validation_status") == "valid"
                and validation.get("passed", True)
                and not path_issues(path.get("joins", []), graph.get("relationships", []))):
            native_paths.append({
                "source_table": binding.get("source_table"),
                "target_object_id": target.get("id"),
                "hop_count": len(path.get("edge_ids", [])),
                "edges": path.get("joins", []),
                "attribution_status": "attributable",
                "path_kind": path.get("kind", "concept_path"),
                "concept_path_id": path.get("id"),
                "case_map_id": (path.get("case_map") or {}).get("id")})
    if not native_paths:
        safe_cardinalities = {"11", "n1", "many1", "manytoone", "onetoone"}
        for path in binding.get("paths", []):
            if str(path.get("to")) not in target_ids:
                continue
            cardinality = _norm(path.get("cardinality")).replace(" ", "")
            if cardinality not in safe_cardinalities:
                continue
            native_paths.append({
                "source_table": binding.get("source_table"),
                "target_object_id": target.get("id"),
                "hop_count": len(path.get("edges", [])), "edges": [],
                "edge_ids": list(path.get("edges", [])),
                "attribution_status": "attributable",
                "path_kind": "binding_path"})
    if native_paths:
        return {"status": "attributable", "reachable": True,
                "paths": native_paths[:max_paths], "max_hops": max_hops,
                "search_bound": "validated_binding_evidence",
                "target_object_id": target.get("id"),
                "matched_member_table": target.get("anchor_table"),
                "member_assessments": []}
    return assess_object_attribution(
        graph, binding.get("source_table"), target,
        max_hops=max_hops, max_paths=max_paths)
