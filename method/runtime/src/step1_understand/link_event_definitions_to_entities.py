"""Deterministic structural associations between activity bindings and Objects."""

from __future__ import annotations
from collections import defaultdict
from copy import deepcopy
from typing import Any
from src.common.graph_identifiers import content_hash, table_key_id


def _concept_memberships(concepts: list[dict[str, Any]]) -> dict[str, list[str]]:
    """PURPOSE: Index valid Object Types by their Physical Object members.
    INPUT: Existing concept records from the unchanged identity algorithm.
    OUTPUT: Physical Object ID to sorted valid Concept IDs.
    """
    result: dict[str, list[str]] = defaultdict(list)
    for concept in concepts:
        if concept.get("validation_status") != "valid":
            continue
        for object_id in concept.get("members", []):
            result[str(object_id)].append(str(concept["id"]))
    return {key: sorted(set(values)) for key, values in result.items()}


def build_activity_object_links(bindings: list[dict[str, Any]],
                                objects: list[dict[str, Any]],
                                concepts: list[dict[str, Any]],
                                references: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """PURPOSE: Link each existing binding to its source-PK Object and declared-FK targets.
    INPUT: Existing bindings, Physical Objects, Concepts and reference inventory.
    OUTPUT: Deduplicated structural links; no lifecycle membership or executable path is asserted.
    """
    object_by_table = {item["table"]: item for item in objects}
    memberships = _concept_memberships(concepts)
    direct_by_child: dict[str, list[dict[str, Any]]] = defaultdict(list)
    polymorphic_by_child: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for reference in references:
        if reference.get("kind") == "declared":
            direct_by_child[str(reference.get("child_table"))].append(reference)
        elif reference.get("kind") == "polymorphic_ref":
            polymorphic_by_child[str(reference.get("child_table"))].append(reference)
    links: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()

    def append(binding: dict[str, Any], target: dict[str, Any], link_type: str,
               source_columns: list[str], target_columns: list[str],
               reference: dict[str, Any] | None) -> None:
        """PURPOSE: Append one stable structural edge while preserving composite-key order.
        INPUT: Binding/target, edge type, ordered columns and optional existing reference.
        OUTPUT: None; duplicate binding/key/reference tuples are skipped.
        """
        signature = (binding["id"], target["id"], link_type, tuple(source_columns),
                     tuple(target_columns), (reference or {}).get("id"))
        if signature in seen:
            return
        seen.add(signature)
        concept_ids = memberships.get(target["id"], [])
        payload = {'event_definition_id': binding["id"],
                   'target_table_key_id': target["id"],
                   "target_object_concept_ids": concept_ids,
                   "target_object_concept_id": concept_ids[0] if concept_ids else None,
                   "link_type": link_type,
                   "source_columns": list(source_columns),
                   "target_columns": list(target_columns),
                   "reference_id": (reference or {}).get("id"),
                   "reference_kind": (reference or {}).get("kind"),
                   "validation_status": ((reference or {}).get("validation_status")
                                         if reference else "schema_valid"),
                   "association_semantics": "structural_not_lifecycle_membership",
                   "executable_attribution": False,
                   "evidence": ([{"kind": "schema", "fact": "source_representation" if link_type == "source_er" else "source_primary_key"}]
                                if reference is None else
                                [{"kind": "schema", "fact": reference.get("kind"),
                                  "reference_id": reference.get("id")},
                                 *list(reference.get("evidence", []))])}
        payload["id"] = "AOL:" + content_hash(payload)[:16]
        links.append(payload)

    for binding in sorted(bindings, key=lambda item: item["id"]):
        source_table = str(binding["table"])
        source_object = object_by_table.get(source_table)
        append(binding, source_object or {'id': table_key_id(source_table)}, "source_er", [], [], None)
        links[-1].update(relation_type='SOURCED_FROM', source_table=source_table,
            instance_attribution_status='not_run', validation_status='source_provenance')
        if source_object:
            append(binding, source_object, "source_pk", list(source_object["pk"]),
                   list(source_object["pk"]), None)
        for reference in sorted(direct_by_child.get(source_table, []),
                                key=lambda item: item["id"]):
            target = object_by_table.get(reference.get("parent_table"))
            if not target:
                continue
            source_concepts = set(memberships.get(source_object["id"], [])) if source_object else set()
            target_concepts = set(memberships.get(target["id"], []))
            shared = source_concepts & target_concepts
            if any(next((concept for concept in concepts if concept["id"] == concept_id), {}).get(
                    "kind") == "identity" for concept_id in shared):
                continue
            pairs = [tuple(pair) for pair in reference.get("columns", [])]
            append(binding, target, "direct_fk", [pair[0] for pair in pairs],
                   [pair[1] for pair in pairs], reference)
        for reference in sorted(polymorphic_by_child.get(source_table, []),
                                key=lambda item: item["id"]):
            concept = next((item for item in concepts
                            if item.get("reference_id") == reference.get("id") and
                            item.get("validation_status") == "valid"), None)
            if concept is None:
                # Preserve a polymorphic reference as unresolved structural evidence;
                # unlike the legacy supertype builder, do not invent a semantic ET.
                payload = {'event_definition_id': binding['id'], 'target_table_key_id': None,
                    'target_object_concept_ids': [], 'target_object_concept_id': None,
                    'link_type': 'polymorphic', 'source_columns': list(reference.get('source_columns', [])),
                    'target_columns': [], 'reference_id': reference['id'], 'reference_kind': 'polymorphic_ref',
                    'validation_status': 'structural_only', 'executable_attribution': False,
                    'association_semantics': 'structural_not_lifecycle_membership',
                    'reason': 'semantic_target_type_unresolved', 'evidence': deepcopy(reference.get('evidence', []))}
                payload['id'] = 'AOL:' + content_hash(payload)[:16]
                links.append(payload)
                continue
            source_columns = list(reference.get("source_columns", []))
            payload = {'event_definition_id': binding["id"],
                       'target_table_key_id': None,
                       "target_object_concept_ids": [concept["id"]],
                       "target_object_concept_id": concept["id"],
                       "link_type": "polymorphic", "source_columns": source_columns,
                       "target_columns": list(concept.get("case_key", {}).get("fields", [])),
                       "reference_id": reference.get("id"), "reference_kind": "polymorphic_ref",
                       "validation_status": reference.get("validation_status", "ambiguous"),
                       "association_semantics": "structural_not_lifecycle_membership",
                       "executable_attribution": False,
                       "evidence": [{"kind": "schema", "fact": "polymorphic_reference",
                                     "reference_id": reference.get("id")},
                                    *list(reference.get("evidence", []))]}
            payload["id"] = "AOL:" + content_hash(payload)[:16]
            signature = (binding["id"], concept["id"], "polymorphic",
                         tuple(source_columns), reference.get("id"))
            if signature not in seen:
                seen.add(signature)
                links.append(payload)
    return sorted(links, key=lambda item: item["id"])


def attach_activity_object_links(bindings: list[dict[str, Any]],
                                 links: list[dict[str, Any]]) -> None:
    """PURPOSE: Attach link references to each binding without copying the binding itself.
    INPUT: Existing mutable binding records and global structural-link records.
    OUTPUT: None; each binding gains a deterministic event_entity_links list.
    """
    by_binding: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for link in links:
        by_binding[link['event_definition_id']].append(link)
    for binding in bindings:
        binding['event_entity_links'] = sorted(
            by_binding.get(binding["id"], []), key=lambda item: item["id"])
