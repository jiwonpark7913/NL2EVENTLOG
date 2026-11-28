"""Canonical EEG terminology and lossless legacy-field compatibility."""

from __future__ import annotations
from copy import deepcopy
from typing import Any
EEG_TERMINOLOGY_VERSION = "entity-table-event-definition-v1"


def _copy_alias(record: dict[str, Any], canonical: str, legacy: str) -> None:
    """PURPOSE: Populate one canonical reference without deleting its stable legacy alias.
    INPUT: Mutable EEG record and canonical/legacy field names.
    OUTPUT: None; copies the legacy value only when the canonical field is absent.
    """
    if canonical not in record and legacy in record:
        record[canonical] = deepcopy(record[legacy])


def canonicalize_eeg(graph: dict[str, Any]) -> dict[str, Any]:
    """PURPOSE: Expose paper-aligned EEG collections while preserving old artifact references.
    INPUT: Legacy, canonical, or mixed JSON-compatible EEG mapping.
    OUTPUT: Independent graph with canonical collections and annotated legacy aliases; IDs and
    algorithms are unchanged. ``O:`` remains a Table+Key metadata ID, never a Table ID.
    """
    result = deepcopy(graph)
    _copy_alias(result, "event_definitions", "activity_bindings")
    _copy_alias(result, "event_definitions", "bindings")
    _copy_alias(result, "entity_types", "selectable_object_concepts")
    _copy_alias(result, "entity_types", "object_concepts")
    _copy_alias(result, "entity_identification_rules", "identification_rules")
    _copy_alias(result, "table_key_records", "object_types")

    for definition in result.get("event_definitions", []):
        definition.setdefault("node_type", "event_definition")
    for path in result.get("attribution_paths", []):
        _copy_alias(path, "event_definition_id", "binding_id")
        _copy_alias(path, "target_entity_type_id", "to")
        _copy_alias(path, "target_table_key_id", "target_member")
        case_map = path.get("case_map")
        if isinstance(case_map, dict):
            _copy_alias(case_map, "source_event_definition_id", "source_binding_id")
            _copy_alias(case_map, "target_entity_type_id", "target_concept_id")

    result["eeg_terminology_version"] = EEG_TERMINOLOGY_VERSION
    result["legacy_field_aliases"] = {
        "activity_bindings": "event_definitions",
        "bindings": "event_definitions",
        "selectable_object_concepts": "entity_types",
        "object_concepts": "entity_types",
        "identification_rules": "entity_identification_rules",
        "object_types": "table_key_records",
        "binding_id": "event_definition_id",
        "to": "target_entity_type_id",
        "target_member": "target_table_key_id",
    }
    return result
