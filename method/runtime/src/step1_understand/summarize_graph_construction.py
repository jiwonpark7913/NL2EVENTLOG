"""DBU machine and human-readable reports."""

from __future__ import annotations
from collections import Counter
from typing import Any


def build_report(graph: dict[str, Any], timestamp_traces: dict[str, Any], activity_traces: dict[str, Any],
                 repair_audits: list[dict[str, Any]], load_warnings: list[dict[str, Any]],
                 timings: dict[str, float]) -> dict[str, Any]:
    """PURPOSE: Preserve every table decision and aggregate discovery/cost counts.
    INPUT: Final graph, stage traces, LLM audits, loader warnings and elapsed seconds.
    OUTPUT: dbu_report.json mapping.
    """
    bindings_by_table=Counter(item["table"] for item in graph["bindings"])
    # Identity review audits: current task name plus the pre-v4 name found in stored audits.
    identity_tasks = {"representative_key_identity", 'entity_type_identity'}
    inventory_reviews = [a for a in repair_audits if a.get("task") == "entity_event_review"]
    repair_calls = [item for item in repair_audits
                    if item.get("task") not in identity_tasks | {"entity_event_review", "global", "targeted", "naming", "entity_type_naming", "identification", "classification", "representation"}]
    identity_calls = [item for item in repair_audits
                      if item.get("task") in identity_tasks]
    global_ot_calls = [item for item in repair_audits
                       if item.get("task") in {"global", "targeted", "naming", "entity_type_naming", "identification", "classification", "representation"}]
    records=[]
    for table in graph["tables"]:
        name=table["table"]
        records.append({**table,"timestamp_trace":timestamp_traces.get(name,{}),
                        "activity_trace":activity_traces.get(name,{}),
                        "repair":next((item for item in repair_calls if item.get("table")==name),None),
                        'event_definition_ids':[item["id"] for item in graph["bindings"] if item["table"]==name]})
    repair_usage, identity_usage, global_ot_usage = Counter(), Counter(), Counter()
    for audit in repair_calls:
        repair_usage.update(audit.get("usage",{}))
    for audit in identity_calls:
        identity_usage.update(audit.get("usage",{}))
    for audit in global_ot_calls:
        global_ot_usage.update(audit.get("usage",{}))
    references = graph.get("references", graph.get("relations", []))
    path_status = Counter(item.get("validation_status", "unknown")
                          for item in graph.get("attribution_paths", []))
    identity_status = Counter(item.get("validation_status", "unknown")
                              for item in graph.get("identity_mapping_assessments", []))
    known_identity_decisions = (identity_status["valid"] + identity_status["rejected"] +
                                identity_status["unresolved"])
    if known_identity_decisions != sum(identity_status.values()):
        raise ValueError("Every identity candidate must be valid, rejected, or unresolved")
    object_tables = {item["table"] for item in graph.get("objects", [])}
    keyless_tables = [{"table": item["table"], "reason": "no_primary_or_unique_not_null_key"}
                      for item in graph.get("tables", []) if item["table"] not in object_tables]
    linked_bindings = {item['event_definition_id'] for item in graph.get('event_entity_links', [])}
    orphan_bindings = [{'event_definition_id': item["id"], "table": item["table"],
                        "reason": "no_source_or_reference_concept_link"}
                       for item in graph.get("bindings", []) if item["id"] not in linked_bindings]
    untimed = [{'event_definition_id': item["id"], "table": item["table"],
                "activity": item.get("alpha", {}).get("name"),
                "timestamp_id": item.get("ts_id"),
                "null_count": int(item.get("null_count", 0)),
                "null_ratio": float(item.get("null_ratio", 0.0)),
                "null_meaning": item.get("null_meaning", "unknown"),
                "null_policy": item.get("null_policy", "exclude_and_report")}
               for item in graph.get("bindings", []) if int(item.get("null_count", 0)) > 0]
    timestamp_links = graph.get("timestamp_event_links", [])
    uncovered_timestamps = [item for item in timestamp_links
                            if item.get("coverage_status") != "covered"]
    review_queue = graph.get("event_review_queue", [])
    binding_status = Counter(item.get("interpretation_status", "legacy_unclassified")
                             for item in graph["bindings"])
    return {"version":graph.get("version", "dbu-rewrite-1"),"dataset":graph["dataset"],"tables":records,
            **{key: graph.get(key, []) for key in ('table_semantic_profiles','entity_types',
                'entity_instance_maps','entity_case_populations','entity_model_diagnostics','semantic_entity_memberships')},
            "key_profiles": graph.get("key_profiles", []),
            "reference_diagnostics": graph.get("reference_diagnostics", []),
            "table_reference_assessments": graph.get("table_reference_assessments", []),
            "identity_mapping_assessments": graph.get("identity_mapping_assessments", []),
            "entity_type_separations": graph.get("entity_type_separations", []),
            "concepts": graph.get("concepts", []), "rollups": graph.get("rollups", []),
            "semantic_object_groups": graph.get("semantic_object_groups", []),
            "global_ot_review": graph.get("global_ot_review", {}),
            "bridges": graph.get("bridges", []),
            "attribution_paths": graph.get("attribution_paths", []),
            "concept_rejected": graph.get("concept_rejected", []),
            "keyless_tables": keyless_tables, "orphan_bindings": orphan_bindings,
            "untimed_events": untimed,
            "uncovered_timestamps": uncovered_timestamps,
            "load_warnings":load_warnings,"summary":{
                "table_status":dict(sorted(Counter(item["status"] for item in graph["tables"]).items())),
                "timestamp_formats":dict(sorted(Counter(
                    item.get("detected_format") or "unknown" for item in graph["timestamps"]
                ).items())),
                "timestamp_accepted_by":dict(sorted(Counter(
                    item.get("accepted_by") or "unknown" for item in graph["timestamps"]
                ).items())),
                "binding_kinds":dict(sorted(Counter(item["alpha"]["kind"] for item in graph["bindings"]).items())),
                "binding_count":len(graph["bindings"]),"timestamp_count":len(graph["timestamps"]),
                "event_table_candidate_count": len(graph.get("event_interpretation_candidates", [])),
                "event_review_table_count": len(review_queue),
                "event_review_applied_table_count": sum(
                    item.get("status") == "applied" for item in review_queue),
                "event_review_unresolved_table_count": sum(
                    item.get("status", "pending").startswith("unresolved") or
                    item.get("status") == "pending" for item in review_queue),
                "event_binding_interpretation_status": dict(sorted(binding_status.items())),
                "unresolved_temporal_unit_count": len(graph.get("unresolved_temporal_units", [])),
                "timestamp_event_covered_count": sum(
                    item.get("coverage_status") == "covered" for item in timestamp_links),
                "timestamp_event_uncovered_count": len(uncovered_timestamps),
                'entity_representation_count': len(graph.get('table_semantic_profiles', graph['objects'])),
                'entity_type_count': len(graph.get('entity_types', graph.get('concepts', []))),
                'entity_type_count_policy':'diagnostic_only',
                'entity_linking_policy':graph.get('entity_linking_policy'),
                'pending_semantic_membership_count':sum(g.get('identity_status')=='unknown'
                    for g in graph.get('semantic_entity_memberships', [])),
                "object_count":len(graph["objects"]),"relation_count":len(graph["relations"]),
                "reference_kind": dict(sorted(Counter(
                    item.get("kind", "declared") for item in references).items())),
                "concept_kind": dict(sorted(Counter(
                    item.get("kind", "unknown") for item in graph.get("concepts", [])).items())),
                "identity_relation_status": dict(sorted(identity_status.items())),
                "identity_candidate_count": sum(identity_status.values()),
                "identity_merged_count": identity_status["valid"],
                "identity_separated_count": identity_status["rejected"],
                "identity_unresolved_count": identity_status["unresolved"],
                "rollup_count": len(graph.get("rollups", [])),
                "bridge_count": len(graph.get("bridges", [])),
                "attribution_path_status": dict(sorted(path_status.items())),
                "keyless_table_count": len(keyless_tables),
                "orphan_binding_count": len(orphan_bindings),
                "untimed_binding_count": len(untimed),
                "untimed_excluded_count": sum(item["null_count"] for item in untimed),
                "entity_event_review_calls":sum(not a["cache_hit"] and "llm_unavailable" not in a["errors"] for a in inventory_reviews),
                "entity_event_review_input_tokens":sum(a.get("usage", {}).get("input_tokens", 0) for a in inventory_reviews),
                "entity_event_review_output_tokens":sum(a.get("usage", {}).get("output_tokens", 0) for a in inventory_reviews),
                "repair_calls":sum(not item.get("cache_hit") and item.get("actual_model_call",True) and "llm_unavailable" not in item.get("errors",[]) for item in repair_calls),
                "repair_cache_hits":sum(bool(item.get("cache_hit")) for item in repair_calls),
                "repair_validated":sum(bool(item.get("validated")) for item in repair_calls),
                "repair_input_tokens":repair_usage["input_tokens"],
                "repair_output_tokens":repair_usage["output_tokens"],
                "identity_llm_calls":sum(not item.get("cache_hit") and item.get("actual_model_call",True) and
                                         "llm_unavailable" not in item.get("errors", [])
                                         for item in identity_calls),
                "identity_llm_cache_hits":sum(bool(item.get("cache_hit")) for item in identity_calls),
                "identity_llm_validated":sum(bool(item.get("validated")) for item in identity_calls),
                "identity_llm_input_tokens":identity_usage["input_tokens"],
                "identity_llm_output_tokens":identity_usage["output_tokens"],
                "global_ot_llm_calls": sum(not item.get("cache_hit") and not item.get("errors")
                                           for item in global_ot_calls),
                "global_ot_input_tokens": global_ot_usage["input_tokens"],
                "global_ot_output_tokens": global_ot_usage["output_tokens"],
                "global_ot_proposals_applied": sum(
                    item.get("status") == "applied" for item in
                    graph.get("global_ot_review", {}).get("proposals", [])),
                "global_ot_proposals_rejected": sum(
                    item.get("status") == "rejected" for item in
                    graph.get("global_ot_review", {}).get("proposals", [])),
                "stage_seconds":{key:round(value,6) for key,value in sorted(timings.items())}}}
