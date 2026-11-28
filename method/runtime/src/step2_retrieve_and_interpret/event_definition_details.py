"""Deterministic Event-definition meaning cards and bounded Step 2 evidence lookup."""

from __future__ import annotations
import copy
DETAIL_SCHEMA_VERSION = "event-definition-details-v1"
DETAIL_SECTIONS = frozenset({"dictionary", "activity_semantics", "time_pairing",
                             "occurrence_identity", "attribution", "validation"})


def get_event_definition_details(graph, event_definition_ids, target_entity_type_id, sections, *,
                                 allowed_event_definition_ids=None, catalog=None):
    """PURPOSE: Read bounded original evidence without mutation/re-judgment.
    INPUT: Graph, IDs, current ET, sections, presented allowlist and matching catalog. OUTPUT: Section records.
    """
    identifiers, requested = list(event_definition_ids), list(sections)
    allowed = set(allowed_event_definition_ids if allowed_event_definition_ids is not None else identifiers)
    if not identifiers or len(identifiers) != len(set(identifiers)) or not set(identifiers) <= allowed:
        raise ValueError("event_detail_id_not_presented")
    if not requested or len(requested) != len(set(requested)) or not set(requested) <= DETAIL_SECTIONS:
        raise ValueError("event_detail_section_invalid")
    if catalog is None or not target_entity_type_id or not set(identifiers) <= set(catalog):
        raise ValueError("event_detail_target_context_invalid")
    bindings = {item["id"]: item for item in graph.get('event_definitions', [])}
    if not set(identifiers) <= set(bindings):
        raise ValueError("event_detail_id_missing")
    output = {}
    for identifier in identifiers:
        binding, row = bindings[identifier], catalog[identifier]
        values = {
            "dictionary": copy.deepcopy(row.get("dictionary_evidence")),
            "activity_semantics": {key: copy.deepcopy(binding.get(key)) for key in
                ("activity_semantics", "semantic_signature", "interpretation_status", "validation_evidence")},
            "time_pairing": {key: copy.deepcopy(binding.get(key)) for key in
                ("timestamp_pairing", "timestamp_candidates", "occurrence_time_source")},
            "occurrence_identity": {key: copy.deepcopy(binding.get(key)) for key in
                ("occurrence_identity_rule_id", "occurrence_identity_status", "row_selection", "source_row_key")},
            "attribution": copy.deepcopy(row.get("attribution")),
            "validation": {"binding_policy": copy.deepcopy(row.get("binding_policy")),
                           "validation_status": binding.get("validation_status"),
                           "extraction_status": binding.get("extraction_status"),
                           "extraction_checks": copy.deepcopy(binding.get("extraction_checks")),
                           "uncertainty": copy.deepcopy(binding.get("uncertainty") or []),
                           "conflicts": copy.deepcopy(binding.get("conflicts") or [])}}
        output[identifier] = {section: values[section] for section in requested}
    return {"detail_schema_version": DETAIL_SCHEMA_VERSION, "target_entity_type_id": target_entity_type_id,
            "details": output}
