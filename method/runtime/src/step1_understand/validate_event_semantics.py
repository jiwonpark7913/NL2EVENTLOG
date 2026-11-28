"""Event Binding v2 occurrence, conflict and object-scope semantics."""

from __future__ import annotations
from itertools import combinations
from typing import Any
import re
from src.common.graph_identifiers import content_hash
from src.common.event_clock import scoped_event_clock


def _stable(prefix: str, payload: Any) -> str:
    """PURPOSE: Build a deterministic content-derived identifier for one v2 entity.
    INPUT: Entity prefix and JSON-compatible identity payload.
    OUTPUT: Stable prefixed identifier.
    """
    return f"{prefix}:" + content_hash(payload)[:16]


def build_occurrence_identity_rules(bindings: list[dict[str, Any]],
                                    objects: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """PURPOSE: Define source-row activity-instance and event-occurrence identities.
    INPUT: Canonical bindings and table-backed Objects with validated keys.
    OUTPUT: Stable identity rules; timestamps are never used as the sole identity.
    """
    key_by_table = {item["table"]: list(item["pk"]) for item in objects}
    result = []
    for binding in sorted(bindings, key=lambda item: item["id"]):
        keys = key_by_table.get(binding["table"], [])
        alpha = binding.get("alpha", {})
        discriminator = ({"kind": "value", "column": alpha.get("column"),
                          "value": alpha.get("value")}
                         if alpha.get("kind") == "value" else
                         {"kind": "timestamp_stage", "ts_id": binding.get("ts_id")})
        if ((binding.get('timestamp_pairing') or {}).get('occurrence_discriminator')
                or (binding.get('timestamp_pairing') or {}).get('phase') in {'start','complete'}):
            discriminator['ts_id'] = binding['ts_id']
        payload = {"table": binding["table"], "source_key_columns": keys,
                   "event_discriminator": discriminator}
        if binding.get("documented_source_conditions"):
            payload["definition_scope"] = binding["id"]
        identifier = _stable("OID", payload)
        result.append({"id": identifier, 'event_definition_id': binding["id"],
                       "activity_instance_key_columns": keys,
                       "event_occurrence_discriminator": discriminator,
                       "identity_status": "supported" if keys else "unresolved",
                       "evidence": ([{"source": "schema_key", "columns": keys}]
                                    if keys else []),
                       "policy": "source_row_key_plus_event_discriminator"})
        binding["occurrence_identity_rule_id"] = identifier
    return result


def build_binding_pair_relationships(bindings: list[dict[str, Any]],
                                     timestamps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """PURPOSE: Replace blanket mixed-table exclusion with pairwise occurrence semantics.
    INPUT: Canonical bindings and classified TimestampUnits.
    OUTPUT: Stable alternative/complementary/lifecycle/independent/unknown relations.
    """
    timestamp_by_id = {item["ts_id"]: item for item in timestamps}
    by_table: dict[str, list[dict[str, Any]]] = {}
    for binding in bindings:
        by_table.setdefault(binding["table"], []).append(binding)
    result = []
    for table, table_bindings in sorted(by_table.items()):
        for left, right in combinations(sorted(table_bindings, key=lambda item: item["id"]), 2):
            if left.get("encoding_interpretation") == right.get("encoding_interpretation"):
                continue
            left_ts, right_ts = left.get("ts_id"), right.get("ts_id")
            left_role = timestamp_by_id.get(left_ts, {}).get("semantic_role", "unknown")
            right_role = timestamp_by_id.get(right_ts, {}).get("semantic_role", "unknown")
            text = " ".join([str(left.get("activity_label", "")),
                             str(right.get("activity_label", ""))]).casefold()
            evidence, status = [], "candidate"
            if left_ts == right_ts:
                relationship, status = "alternative", "supported"
                evidence.append("shared_timestamp_unit")
            elif {left_role, right_role} & {"ingestion_time", "recorded_time"}:
                relationship, status = "independent", "supported"
                evidence.append("timestamp_role_separation")
            elif (re.search(r"\b(start|started|begin|opened)\b", text) and
                  re.search(r"\b(complete|completed|finish|finished|closed)\b", text)):
                relationship, status = "lifecycle_pair", "supported"
                evidence.append("documented_stage_semantics")
            else:
                relationship = "unknown"
                evidence.append("insufficient_pair_evidence")
            pair = sorted([left["id"], right["id"]])
            result.append({"id": _stable("CR", [table, pair]), "binding_pair": pair,
                           "relationship": relationship,
                           "occurrence_identity_rule_ids": sorted(filter(None, [
                               left.get("occurrence_identity_rule_id"),
                               right.get("occurrence_identity_rule_id")])),
                           "evidence": evidence, "confidence_basis": evidence[0],
                           "status": status})
    by_binding: dict[str, list[str]] = {}
    for relation in result:
        for event_definition_id in relation["binding_pair"]:
            by_binding.setdefault(event_definition_id, []).append(relation["id"])
    for binding in bindings:
        binding["conflict_relation_ids"] = sorted(by_binding.get(binding["id"], []))
    return sorted(result, key=lambda item: item["id"])


def build_binding_object_associations(bindings: list[dict[str, Any]],
                                      concepts: list[dict[str, Any]],
                                      timestamps: list[dict[str, Any]],
                                      objects: list[dict[str, Any]],
                                      dd: dict[str, Any]) -> list[dict[str, Any]]:
    """PURPOSE: Separate executable attribution from object-specific lifecycle membership.
    INPUT: Bindings with concept paths, Object Types and TimestampUnit roles.
    OUTPUT: One stable association per Binding–Concept pair with evidence and uncertainty.
    """
    timestamp_by_id = {item["ts_id"]: item for item in timestamps}
    concept_ids = {item["id"] for item in concepts}
    object_table = {item["id"]: item["table"] for item in objects}
    table_definition = {item["table"]: item.get("definition", "")
                        for item in dd.get("tables", [])}
    column_definition = {(item["table"], item["column"]): item.get("definition", "")
                         for item in dd.get("columns", [])}
    narrative = " ".join([*(str(item.get("text", "")) for item in dd.get("processes", [])),
                           *(str(item) for item in dd.get("business_rules", []))]).casefold()
    associations = []
    for binding in sorted(bindings, key=lambda item: item["id"]):
        paths_by_concept: dict[str, list[dict[str, Any]]] = {}
        for path in binding.get("concept_paths", []):
            paths_by_concept.setdefault(str(path.get("to")), []).append(path)
        linked_concepts = {str(concept_id)
                           for link in binding.get('event_entity_links', [])
                           for concept_id in link.get("target_object_concept_ids", [])}
        for concept_id in sorted((set(paths_by_concept) | linked_concepts) & concept_ids):
            paths = paths_by_concept.get(concept_id, [])
            valid_paths = [path for path in paths if path.get("validation_status") == "valid"]
            ambiguous_paths = [path for path in paths if path.get("validation_status") == "ambiguous"]
            attributable = bool(valid_paths)
            attribution_status = ("attributable" if attributable else
                                  "ambiguous" if ambiguous_paths else
                                  "structural_only")
            from src.step1_understand.detect_and_normalize_timestamps import occurrence_time_policy
            timestamp = scoped_event_clock(binding, timestamp_by_id.get(binding.get("ts_id"), {}))
            time_proof = occurrence_time_policy(timestamp)
            role = timestamp.get("semantic_role", "unknown")
            semantics = binding.get('activity_semantics', {})
            activity_supported = (binding.get('interpretation_status') == 'supported' and
                semantics.get('status') == 'supported' and semantics.get('occurrence_status') == 'supported' and
                time_proof['eligible'] and binding.get('timestamp_pairing', {}).get('status', 'supported')
                in {'supported', 'supported_by_review'} and
                binding.get('semantic_signature', {}).get('interpretation_status') not in {'ambiguous', 'conflicting'}
                and not binding.get('uncertainty') and not binding.get('conflicts'))
            label = str(binding.get("activity_label", binding.get("alpha", {}).get("name", "")))
            concept = next(item for item in concepts if item["id"] == concept_id)
            target_terms = {object_table.get(member, "").casefold().rstrip("s")
                            for member in concept.get("members", [])}
            alpha_column = binding.get("alpha", {}).get("column")
            source_text = " ".join([
                table_definition.get(binding["table"], ""),
                column_definition.get((binding["table"], alpha_column), "")
                if alpha_column else "", label]).casefold()
            semantic_target_support = any(
                term and re.search(r"\b" + re.escape(term) +
                    r"s?\s+(?:business\s+)?(?:lifecycle|process|activity|activities|events?|transitions?|occurrences?)\b", source_text)
                for term in target_terms)
            narrative_support = any(term and re.search(r"\b" + re.escape(term) +
                r"s?\s+(?:business\s+)?(?:lifecycle|process)\b", narrative)
                for term in target_terms) and label.casefold() in narrative and binding['table'].casefold() in narrative
            # An explicit subject/transition statement is semantic evidence without requiring
            # the literal words lifecycle/process. Merely mentioning an FK target is insufficient.
            transition_support = any(term and re.search(
                r"\b(?:records?|captures?|represents?)\b[^.!?]{0,80}\b" + re.escape(term) +
                r"s?\b[^.!?]{0,60}\b(?:activities|activity|events?|transitions?|occurrences?)\b|" +
                r"\b" + re.escape(term) + r"s?\s+(?:activity|event|transition|occurrence)\b",
                source_text) for term in target_terms)
            semantic_target_support = semantic_target_support or narrative_support or transition_support
            semantic_target_exclusion = any(term and re.search(
                r"\b(?:not|never|excluded|unrelated)\b[^.!?]{0,70}\b" + re.escape(term) +
                r"s?\s+(?:business\s+)?(?:lifecycle|process|activity|activities|events?|transitions?|occurrences?)\b", source_text)
                for term in target_terms)
            technical = role in {"ingestion_time", "recorded_time", "scheduled_time"} or bool(
                re.search(r"\b(audit|backup|ingest|load|sync|technical|system update)\b", label, re.I))
            rule_contract = 'identification_rules' in concept
            own = (any(path.get('entity_subject_rule_ids') for path in valid_paths) if rule_contract else
                   any(path.get("kind") == "own" and path.get("validation_status") == "valid" for path in paths))
            reported_on_local_artifact = bool(timestamp.get('row_value_scope') and
                                              binding['table'] in {object_table.get(member)
                                                                   for member in concept.get('members', [])})
            if reported_on_local_artifact:
                own = False
                membership, object_role, reason = "excluded", "context", "represented_action_on_related_entity"
            elif semantic_target_exclusion:
                membership, object_role, reason = "excluded", "context", "dictionary_excludes_related_lifecycle"
            elif technical:
                membership, object_role, reason = "excluded", "context", "technical_or_non_occurrence_time"
            elif not activity_supported:
                membership, object_role, reason = "candidate", "related_object", "activity_interpretation_unresolved"
            elif own and attributable:
                membership, object_role, reason = "confirmed", "subject", "own_object_occurrence"
            elif attributable and semantic_target_support and role in {
                    "business_occurrence", "effective_time", "unknown"}:
                membership, object_role, reason = (
                    "confirmed", "related_object", "dictionary_supported_related_lifecycle")
            else:
                membership, object_role, reason = "candidate", "related_object", "positive_scope_evidence_required"
            payload = {'event_definition_id': binding["id"], "object_concept_id": concept_id}
            associations.append({"id": _stable("AO", payload), **payload,
                                 "structurally_attributable": attributable,
                                 "attribution_status": attribution_status,
                                 "attribution_path_ids": sorted(path["id"] for path in paths),
                                 "lifecycle_membership": membership,
                                 "membership_evidence": [{"source": "fixed_scope_policy",
                                                          "detail": reason}],
                                 "object_role": object_role,
                                 "own_event_status": ("supported" if own and membership == "confirmed" else
                                                      "uncertain" if own else "not_subject") if rule_contract else None,
                                 "identification_rule_ids": sorted({rid for path in paths for rid in path.get('identification_rule_ids', [])}),
                                 "subject_identification_rule_ids": sorted({rid for path in paths for rid in path.get('entity_subject_rule_ids', [])}),
                                 "scope_policy_version": "et-independent-membership-v3",
                                 "activity_semantics_status": semantics.get("status", "unresolved"),
                                 "occurrence_time_policy": time_proof})
    by_binding: dict[str, list[str]] = {}
    for association in associations:
        by_binding.setdefault(association['event_definition_id'], []).append(association["id"])
    for binding in bindings:
        binding["object_association_ids"] = sorted(by_binding.get(binding["id"], []))
    return sorted(associations, key=lambda item: item["id"])


def validate_event_semantics(bindings: list[dict[str, Any]],
                             occurrence_rules: list[dict[str, Any]],
                             conflict_relations: list[dict[str, Any]],
                             object_associations: list[dict[str, Any]],
                             concepts: list[dict[str, Any]],
                             timestamps: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """PURPOSE: Detect dangling/duplicate v2 IDs and contradictory pair states.
    INPUT: Canonical Binding v2 entities and valid Object Type targets.
    OUTPUT: Deterministic diagnostics; an empty list means the structural schema is valid.
    """
    diagnostics = []
    event_definition_ids = {item["id"] for item in bindings}
    concept_ids = {item["id"] for item in concepts}
    timestamp_ids = {item["ts_id"] for item in (timestamps or [])}
    referenced_timestamps = {item.get("ts_id") for item in bindings if item.get("ts_id")}
    for binding in bindings:
        if timestamps is not None and binding.get("ts_id") not in timestamp_ids:
            diagnostics.append({"kind": "dangling_timestamp", "entity": binding["id"],
                                "timestamp_id": binding.get("ts_id")})
    for timestamp_id in sorted(timestamp_ids - referenced_timestamps):
        diagnostics.append({"kind": "unlinked_timestamp", "entity": timestamp_id})
    collections = (("occurrence_identity", occurrence_rules),
                   ("conflict_relation", conflict_relations),
                   ("object_association", object_associations))
    for kind, records in collections:
        ids = [item["id"] for item in records]
        if len(ids) != len(set(ids)):
            diagnostics.append({"kind": "duplicate_id", "entity": kind})
    for relation in conflict_relations:
        missing = set(relation.get("binding_pair", [])) - event_definition_ids
        if missing:
            diagnostics.append({"kind": "dangling_binding", "entity": relation["id"],
                                'event_definition_ids': sorted(missing)})
    rule_ids = {item["id"] for item in occurrence_rules}
    relation_ids = {item["id"] for item in conflict_relations}
    association_ids = {item["id"] for item in object_associations}
    for rule in occurrence_rules:
        if rule.get('event_definition_id') not in event_definition_ids:
            diagnostics.append({"kind": "dangling_binding", "entity": rule["id"],
                                'event_definition_ids': [rule.get('event_definition_id')]})
    pair_states: dict[tuple[str, ...], set[str]] = {}
    for relation in conflict_relations:
        pair = tuple(sorted(relation.get("binding_pair", [])))
        pair_states.setdefault(pair, set()).add(str(relation.get("relationship")))
        missing_rules = set(relation.get("occurrence_identity_rule_ids", [])) - rule_ids
        if missing_rules:
            diagnostics.append({"kind": "dangling_occurrence_rule",
                                "entity": relation["id"],
                                "occurrence_identity_rule_ids": sorted(missing_rules)})
    for pair, states in sorted(pair_states.items()):
        if len(states) > 1:
            diagnostics.append({"kind": "contradictory_pair_relationship",
                                "binding_pair": list(pair), "relationships": sorted(states)})
    for association in object_associations:
        if association['event_definition_id'] not in event_definition_ids:
            diagnostics.append({"kind": "dangling_binding", "entity": association["id"],
                                'event_definition_ids': [association['event_definition_id']]})
        if association.get("object_concept_id") not in concept_ids:
            diagnostics.append({"kind": "dangling_object_concept",
                                "entity": association["id"],
                                "object_concept_id": association.get("object_concept_id")})
        if (association["structurally_attributable"] and
                association["attribution_status"] != "attributable"):
            diagnostics.append({"kind": "contradictory_attribution", "entity": association["id"]})
    for binding in bindings:
        referenced_rule = binding.get("occurrence_identity_rule_id")
        if referenced_rule not in rule_ids:
            diagnostics.append({"kind": "dangling_occurrence_rule", "entity": binding["id"],
                                "occurrence_identity_rule_ids": [referenced_rule]})
        missing_relations = set(binding.get("conflict_relation_ids", [])) - relation_ids
        if missing_relations:
            diagnostics.append({"kind": "dangling_conflict_relation", "entity": binding["id"],
                                "conflict_relation_ids": sorted(missing_relations)})
        missing_associations = set(binding.get("object_association_ids", [])) - association_ids
        if missing_associations:
            diagnostics.append({"kind": "dangling_object_association", "entity": binding["id"],
                                "object_association_ids": sorted(missing_associations)})
        alpha = binding.get("alpha", {})
        if (not binding.get("activity_label_source") or not alpha.get("name") or
                (alpha.get("kind") == "value" and "value" not in alpha)):
            diagnostics.append({"kind": "missing_activity_provenance", "entity": binding["id"]})
    return diagnostics


def finalize_extraction_contracts(graph, key_profiles):
    """PURPOSE: Preserve independent meaning, temporal and occurrence-identity proof obligations.
    INPUT: Assembled native EEG and already measured declared-key profiles.
    OUTPUT: In-place candidate contracts, executable status and validated occurrence rules.
    No rows, inferred keys or SQL proposed by a model are introduced.
    """
    keys = {(k['table'], tuple(k['columns'])): k for k in key_profiles}
    times = {t['ts_id']: t for t in graph['timestamps']}
    role_names = {'business_occurrence': 'valid_time', 'effective_time': 'valid_time',
                  'recorded_time': 'transaction_time', 'ingestion_time': 'transaction_time',
                  'scheduled_time': 'planned_time', 'estimated_time': 'estimated_time',
                  'non_event_time': 'attribute_time'}
    from src.step1_understand.detect_and_normalize_timestamps import occurrence_time_policy
    for time in times.values():
        time['occurrence_time_policy'] = occurrence_time_policy(time)
        time['time_role'] = (role_names.get(time.get('semantic_role'), 'unresolved')
                             if time.get('role_status') == 'supported' else 'unresolved')
    objects = {o['table']: o for o in graph['objects']}
    rules = {r['event_definition_id']: r for r in graph.get('occurrence_identity_rules', [])}
    for candidate in graph['bindings']:
        table = candidate['table']
        columns = objects.get(table, {}).get('pk', [])
        key = keys.get((table, tuple(columns)), {})
        identity = 'supported' if key.get('unique') else 'unresolved'
        time = scoped_event_clock(candidate, times.get(candidate.get('ts_id'), {}))
        semantics = candidate.get('activity_semantics', {})
        pairing = candidate.get('timestamp_pairing', {})
        time_supported = (occurrence_time_policy(time)['eligible'] and
                          (not pairing or pairing.get('status') in {'supported', 'supported_by_review'}))
        # The retrieval signature only steers retrieval/membership; it never demotes validated meaning.
        meaning_status = semantics.get('status', 'unresolved')
        from src.step1_understand.resolve_activity_meanings import activity_label_issue
        label_issue = activity_label_issue(candidate['alpha'].get('name'))
        candidate['activity_label_issue'] = label_issue
        if meaning_status == 'supported' and label_issue:
            meaning_status = 'unresolved'  # shared executable gate: placeholder/time-attribute/documentation names
        checks = {'activity': meaning_status,
                  'occurrence': semantics.get('occurrence_status', 'unresolved'),
                  'time': 'supported' if time_supported else 'unresolved',
                  'identity': identity}
        from src.common.runtime_input_contract import extraction_status_from_checks
        contract = extraction_status_from_checks(checks)
        candidate['extraction_checks'] = contract['checks']
        candidate['extraction_status'] = contract['status']
        candidate['unresolved_reasons'] = contract['unresolved_reasons']
        candidate['source_row_key'] = list(columns)
        candidate['row_selection'] = ({'kind': 'equals', 'column': candidate['alpha']['column'],
                                      'value': candidate['alpha']['value']}
                                     if candidate['alpha']['kind'] == 'value' else {'kind': 'all_rows'})
        candidate['occurrence_identity_status'] = identity
        if candidate['id'] in rules:
            rules[candidate['id']]['identity_status'] = identity
            rules[candidate['id']]['key_validation'] = key
    graph['eeg_contract_version'] = 'step1-four-stage-v1'
    graph['event_table_candidates'] = [t['table'] for t in graph['tables'] if t['ts_ids']]
    for table in graph['tables']:
        table['event_table_candidate'] = bool(table['ts_ids'])
