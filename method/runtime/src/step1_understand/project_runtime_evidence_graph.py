"""Compatibility adapter from native DBU rewrite output to the Step 2–5 runtime graph."""

from __future__ import annotations
from pathlib import Path
from typing import Any
from copy import deepcopy
from src.common.graph_identifiers import normalize_event_definition_references
from src.common.event_clock import scoped_event_clock
from src.common.activity_identity import activity_identity
from src.step1_understand.candidate_ledger import audit_ledger
from src.common.timestamp_policy import binding_timezone
from src.common.normalize_relation_assessments import normalize_graph_record
from src.common.attribution_policy import POLICY as LINKING_POLICY, MAX_ATTRIBUTION_HOPS
from src.step1_understand.detect_and_normalize_timestamps import occurrence_time_policy
from src.common.schema_metadata import build_process_view_candidates, database_fingerprint, stable_id


def _timestamp_candidate(unit: dict[str, Any]) -> dict[str, Any]:
    """PURPOSE: Convert a native TimestampUnit into the compiler's enumerated candidate shape.
    INPUT: Native timestamp mapping.
    OUTPUT: Runtime timestamp candidate retaining native format/provenance and supported compiler kind.
    """
    components=[{"column":column,"role":"date" if index==0 else "time"}
                for index,column in enumerate(unit["columns"])]
    detected=unit.get("detected_format")
    if unit["source"] == "composite":
        kind="date_clock"
    elif unit["source"] == "json_path":
        kind="json_path"
    elif detected == "epoch_s":
        kind="epoch_seconds"
    elif detected == "epoch_ms":
        kind="epoch_ms"
    else:
        kind="direct"
    value={"id":unit["ts_id"],"kind":kind,"native_source":unit["source"],
           "column":unit["columns"][0], "columns":list(unit["columns"]),"components":components,
           "json_path":unit.get("json_path"),"detected_format":detected,
           "format":"yyyymmdd" if detected=="compact" and unit.get("precision")=="day" else detected,
           "precision":unit.get("precision"),"timezone":binding_timezone(unit),
           "native_timezone":unit.get("timezone"),"parse_ratio":unit.get("parse_ratio"),
           "role":unit.get("semantic_role", "unknown"),
           "semantic_role":unit.get("semantic_role", "unknown"),
           "role_status":unit.get("role_status", "unknown"),
           "occurrence_time_policy":occurrence_time_policy(unit),
           "time_role":unit.get("time_role", "unresolved"),
           "role_evidence":unit.get("role_evidence", []),
           "role_hypotheses":[],"evidence":unit.get("evidence",[])}
    if unit["source"]=="composite":
        value.update({"date_column":unit["columns"][0],"clock_column":unit["columns"][1],
                      "time_column":unit["columns"][1]})
    return value


def project_event_definitions(data):
    """PURPOSE: Project verified native EDs into the existing PI and ESpec schema.
    INPUT: Native bindings, Timestamp Units, and optional event–entity associations.
    OUTPUT: Runtime binding records, preserving physical provenance and source conditions.
    """
    timestamps={item["ts_id"]:item for item in data["timestamps"]}
    bindings=[]
    for item in data["bindings"]:
        alpha=item["alpha"]; label=str(alpha["name"])
        source_kind="row_activity" if alpha["kind"]=="value" else "column_event" if alpha["kind"]=="column" else "table_event"
        raw_values=[alpha["value"]] if alpha["kind"]=="value" else []
        source_key = stable_id("source", [source_kind, item["table"], alpha.get("column"),
                                              raw_values, list(timestamps[item["ts_id"]]["columns"])])
        activity_source=item.get("activity_source") or (
            {"kind":"value","table":item["table"],"column":alpha.get("column"),
             "value":alpha.get("value")} if alpha["kind"]=="value" else
            {"kind":"column","table":item["table"],"timestamp_unit_id":item["ts_id"],
             "source_columns":list(timestamps[item["ts_id"]]["columns"])})
        bindings.append({"id":item["id"],"source_key":source_key,
                         "alpha":dict(alpha),"ts_id":item["ts_id"],
                         "activity":label,"activity_label":item.get("activity_label", label),
                         "activity_source":activity_source,
                         "activity_label_source":item.get("activity_label_source", item["provenance"]),
                         "activity_semantics":deepcopy(item.get("activity_semantics", {})),
                         "meaning_card":deepcopy(item.get("meaning_card")),
                         **{key:deepcopy(item.get(key)) for key in (
                             "extraction_status", "extraction_checks", "unresolved_reasons", "validation_axes", "candidate_kind", "activity_name_hypothesis",
                             "candidate_tier", "entity_reviews", "unresolved_axis", "review_dictionary", "carrier_clock_relationship",
                             "source_row_key", "row_selection", "occurrence_identity_status", "occurrence_time_source") if key in item},
                         "interpretation_status":item.get("interpretation_status", "unresolved"),
                         "validation_status":item.get("validation_status"),
                         "validation_evidence":deepcopy(item.get("validation_evidence", [])),
                         "uncertainty":deepcopy(item.get("uncertainty", [])),
                         "conflicts":deepcopy(item.get("conflicts", [])),
                         "candidate_status":item.get("candidate_status"),
                         "event_kind":item.get("event_kind", "unknown"),
                         "canonical_activity_id":stable_id("activity",label.casefold()),
                         "source_table":item["table"],"source_kind":source_kind,
                         "activity_column":alpha.get("column"),"raw_values":raw_values,
                         "carrier_role":item.get("carrier_role"),
                         "timestamp_pairing":item.get("timestamp_pairing"),
                         "occurrence_identity_rule_id":item.get("occurrence_identity_rule_id"),
                         "object_association_ids":item.get("object_association_ids", []),
                         "lifecycle_associations":deepcopy([a for a in data.get('event_entity_associations', [])
                                                            if a.get('event_definition_id') == item["id"]]),
                         "conflict_relation_ids":item.get("conflict_relation_ids", []),
                         'legacy_event_definition_ids':item.get('legacy_event_definition_ids', []),
                         "encoding_interpretation":item.get("encoding_interpretation"),
                         "conflict_group":item.get("conflict_group"),
                         "semantic_signature":deepcopy(item.get("semantic_signature", {})),
                         "null_count":item.get("null_count", 0),
                         "null_ratio":item.get("null_ratio", 0.0),
                         "null_meaning":item.get("null_meaning", "unknown"),
                         "null_policy":item.get("null_policy", "exclude_and_report"),
                         "untimed_excluded_count":item.get("untimed_excluded_count", 0),
                         "timestamp_candidates":[_timestamp_candidate(scoped_event_clock(
                             item, timestamps[item['ts_id']]))],
                         "timestamp_columns":list(timestamps[item["ts_id"]]["columns"]),
                         "alternative_labels":[],"label_origin":item["provenance"],
                         "documented_source_conditions":deepcopy(item.get("documented_source_conditions", [])), "eventness":"unknown",
                         "history_completeness":"unknown",
                         "paths":item.get("paths",[]),
                         "concept_paths":item.get("concept_paths",[]),
                         'event_entity_links':item.get('event_entity_links',[]),
                         "provenance":item["provenance"],"evidence":item["evidence"]})
    return bindings


def to_runtime_graph(native: Any, database: Path) -> dict[str, Any]:
    """PURPOSE: Expose native DBU objects/bindings/relations through existing query and ES contracts.
    INPUT: EvidenceGraph facade and original SQLite path.
    OUTPUT: Runtime graph whose physical IDs all derive from the native graph.
    """
    data=normalize_event_definition_references(deepcopy(normalize_graph_record(native.data)))
    table_models={item.name:item for item in native.physical_tables}
    dd_columns={(item["table"],item["column"]):item
                for item in native.normalized_dictionary.get("columns",[])}
    tables=[]
    for name in sorted(table_models):
        model=table_models[name]; profile=native.profiles[name]
        key_candidates=[]
        if model.primary_key:
            key_candidates.append({"kind":"primary_key","columns":list(model.primary_key),"unique":True})
        key_candidates.extend({"kind":"unique_key","columns":list(key),"unique":True}
                              for key in model.unique_keys if key!=model.primary_key)
        tables.append({"id":f"table:{name}","name":name,"row_count":profile["row_count"],
                       "columns":[{"id":column.id,"name":column.name,"type":column.declared_type,
                                   "declared_type":column.declared_type,
                                   "dictionary_type":dd_columns.get((name,column.name),{}).get("type"),
                                   "logical_type":dd_columns.get((name,column.name),{}).get("representation_class"),
                                   "observed_storage_types":profile["columns"][column.name]["storage_types"],
                                   "not_null":column.not_null,"distinct_count":profile["columns"][column.name]["distinct_count"],
                                   "null_count":profile["columns"][column.name]["null_count"],"profile_status":"measured"}
                                  for column in model.columns],
                       "primary_key":list(model.primary_key), "unique_keys":deepcopy(model.unique_keys),
                       "foreign_keys":deepcopy(model.foreign_keys),
                       "definition":next((t.get("definition", "") for t in native.normalized_dictionary["tables"]
                                           if t["table"] == name), ""),
                       "key_candidates":key_candidates,"local_id":list(model.primary_key),
                       "profile_status":"measured","role_hypotheses":[],"row_semantics_status":"unknown"})
    bridge_tables={item["table"] for item in data.get("bridges", [])
                   if item.get("validation_status") == "valid"}
    relations=[]
    relation_inventory=data.get("references", data["relations"])
    for item in relation_inventory:
        if item.get("kind") in {"polymorphic_ref", "generic_reference"}:
            continue
        relations.append({"id":item["id"],"left_table":item["child_table"],
                          "left_columns":[pair[0] for pair in item["columns"]],
                          "right_table":item["parent_table"],
                          "right_columns":[pair[1] for pair in item["columns"]],
                          "declared":(item.get("kind") == "declared" or item.get("declared") is True),
                          "kind":"foreign_key" if (item.get("kind") == "declared" or item.get("declared") is True) else "value_inclusion",
                          "source":"declared_fk" if (item.get("kind") == "declared" or item.get("declared") is True) else "verified_value_overlap",
                          "prior_confidence":1.0,"confidence":1.0,
                          "reference_evidence":deepcopy(item.get("reference_evidence", {})),
                          "candidate_status":item.get("candidate_status", "verified"),
                          "cardinality":item["cardinality"],
                          "child_key_unique":item.get('child_key_unique', False),
                          "bridge_table": item["child_table"] in bridge_tables,
                          "evidence":item["evidence"]})
    objects=[]
    dd_tables={item["table"]:item for item in native.normalized_dictionary["tables"]}
    for item in data["objects"]:
        definition=dd_tables.get(item["table"],{})
        label=item.get("display_name") or item["table"].replace("_"," ").title()
        objects.append({"id":item["id"],"name":label,"label":label,"anchor_table":item["table"],
                        "key_columns":list(item["pk"]),"identity_candidates":[{"kind":item.get("key_kind","unknown"),"columns":list(item["pk"]),"unique":True}],
                        "lexical_aliases":[item["table"],label],
                        "documented_aliases":[{"alias":label,"normalized":label.casefold(),
                                                "source":definition.get("id","data_dictionary")}],
                        "model_aliases":[],
                        "description":definition.get("definition","") ,"evidence":item["evidence"],
                        **{key:item.get(key) for key in (
                            "canonical_name","display_name","naming_status","name_source",
                            "candidate_names","naming_evidence","naming_warnings","naming_version")}})
    objects_by_id={item["id"]:item for item in objects}
    selectable_concepts=[]
    for concept in data.get("concepts", []):
        if concept.get("validation_status") != "valid" or concept.get("selectable") is False:
            continue
        members=[objects_by_id[identifier] for identifier in concept.get("members", [])
                 if identifier in objects_by_id]
        if not members:
            continue
        canonical_id=concept.get("case_key", {}).get("canonical_member") or members[0]["id"]
        canonical=objects_by_id.get(canonical_id, members[0])
        aliases={concept.get("name", "")}
        descriptions=[]
        for member in members:
            aliases.update(member.get("lexical_aliases", []))
            aliases.update(value.get("alias", "") for value in member.get("documented_aliases", []))
            if member.get("description"):
                descriptions.append(member["description"])
        selectable_concepts.append({
            "id":concept["id"], "kind":concept.get("kind"),
            "validation_status":concept.get("validation_status"),
            "name":concept.get("name") or canonical["name"],
            "label":concept.get("name") or canonical["label"],
            "anchor_table":canonical["anchor_table"],
            'anchor_entity_type_id':canonical["id"],
            "member_object_ids":[member["id"] for member in members],
            "member_tables":[member["anchor_table"] for member in members],
            "key_columns":list(canonical["key_columns"]),
            "member_keys":concept.get("case_key", {}).get("member_keys", {
                member["id"]:list(member["key_columns"]) for member in members}),
            "lexical_aliases":sorted(alias for alias in aliases if alias),
            "documented_aliases":[], "model_aliases":[],
            "description": (concept.get("business_definition") or
                            " ".join(dict.fromkeys(descriptions))),
            'business_definition': concept.get('business_definition', ''),
            "physical_descriptions": list(dict.fromkeys(descriptions)),
            "business_definition": concept.get("business_definition"),
            "rollups": list(concept.get("rollups", [])),
            "case_id_map": dict(concept.get("case_id_map", {})),
            'entity_type_id': concept.get('entity_type_id'),
            'population': deepcopy(concept.get('population')),
            'pending_semantic_group_ids':list(concept.get('pending_semantic_group_ids', [])),
            'roles': list(concept.get('roles', ['unknown'])),
            'identification_target_ids': list(concept.get('identification_target_ids', [])),
            'identification_rules': deepcopy(concept.get('identification_rules', [])),
            'semantic_status': concept.get('semantic_status'),
            'business_meaning': concept.get('business_meaning'),
            'instance_granularity': concept.get('instance_granularity'),
            "evidence":concept.get("evidence", []),
            **{key:concept.get(key) for key in (
                "canonical_name","display_name","naming_status","name_source",
                "candidate_names","naming_evidence","naming_warnings","naming_version")},
        })
    bindings=project_event_definitions(data)
    partial={'table_key_records':objects,"relationships":relations,'event_definitions':bindings}
    views=build_process_view_candidates(partial, max_hops=data.get("build_configuration", {}).get("max_hops", MAX_ATTRIBUTION_HOPS))
    db_path=Path(database).resolve()
    graph={"schema_graph_version":8,"database":str(db_path),"database_fingerprint":database_fingerprint(db_path),
           "profile_mode":"dbu_rewrite","tables":tables,"relationships":relations,
           "relationship_candidates":relations,"relationship_budget_exhausted":False,
           "relationship_discovery_cost":{"exact_probe_count":0,"deferred_count":0,"unindexed_probe_count":0},
           'table_key_records':objects,'entity_types':data.get("concepts", []),
           **{k:deepcopy(data.get(k)) for k in ('entity_model_version','entity_types',
                'table_semantic_profiles','entity_instance_maps','entity_case_populations','entity_model_diagnostics',
                'semantic_entity_memberships','identification_targets','identification_rules',
                'entity_identity_decisions','entity_build_stages','semantic_classification_pairs',
                'business_value_evidence') if k in data},
           "semantic_object_groups":data.get("semantic_object_groups", []),
           'entity_types':selectable_concepts,
           **{k:data.get(k, []) for k in ("table_reference_assessments","identity_mapping_assessments",
                                         "entity_type_separations")},
           "rollups":data.get("rollups", []),"bridges":data.get("bridges", []),
           "attribution_paths":data.get("attribution_paths", []),
           'event_entity_links':data.get('event_entity_links', []),
           'event_entity_associations':data.get('event_entity_associations', []),
           "activity_semantics_version":data.get("activity_semantics_version"),
           "runtime_input_policy":data.get("runtime_input_policy"),
           "input_contract_audit":deepcopy(data.get("input_contract_audit", {})),
           "build_configuration":deepcopy(data.get("build_configuration", {})),
           "semantic_policy_version":data.get("semantic_policy_version"),
           'event_definition_pair_relationships':data.get('event_definition_pair_relationships', []),
           "occurrence_identity_rules":data.get("occurrence_identity_rules", []),
           "event_semantics_diagnostics":data.get("event_semantics_diagnostics", []),
           "event_binding_schema_version":data.get("event_binding_schema_version", "event-binding-v1"),
           "event_semantic_signature_schema_version":data.get(
               "event_semantic_signature_schema_version", "event-semantic-signature-v1"),
           "reference_diagnostics":data.get("reference_diagnostics", []),
           "eeg_contract_version":data.get("eeg_contract_version"),
           "event_table_candidates":deepcopy(data.get("event_table_candidates", [])),
           "event_interpretation_candidates":deepcopy(data.get("event_interpretation_candidates", [])),
           "unresolved_temporal_units":deepcopy(data.get("unresolved_temporal_units", [])),
           "table_roles":deepcopy(data.get("table_roles", [])),
           'event_definitions':bindings,
           "view_candidates":views,"data_dictionary":native.normalized_dictionary,
           "dbu_rewrite":data,"dbu_report":native.report,"dbu_llm_calls":native.llm_calls,
           "activity_candidates":data["activity_candidates"],
           "input_contract":data["input_contract"],
           "entity_linking_policy":data.get("entity_linking_policy", LINKING_POLICY),
           "source_discovery_contract":"dbu-rewrite-1: DB+DD only; query-independent"}
    if 'carrier_timestamp_matrix' in data:
        graph['carrier_timestamp_matrix'] = deepcopy(data['carrier_timestamp_matrix'])
    from src.step1_understand.collect_unresolved_event_evidence import collect_unresolved_event_evidence
    graph["unresolved_event_evidence"] = collect_unresolved_event_evidence(data, native.normalized_dictionary)
    graph["evidence_graph"]={}  # Native evidence is exposed under dbu_rewrite; legacy capability graph is absent.
    from src.common.normalize_graph_terminology import canonicalize_eeg
    graph = canonicalize_eeg(graph)
    for definition in graph['event_definitions']:
        definition['activity_identity'] = activity_identity(definition)
        definition['canonical_activity_id'] = definition['activity_identity']
    from src.step1_understand.carrier_event_families import apply_carrier_policy
    graph = apply_carrier_policy(graph, database)
    if 'candidate_ledger' in data:
        graph['candidate_ledger'] = audit_ledger(data['candidate_ledger'], graph)
    if 'source_coverage_claims' in data:
        from src.step1_understand.source_coverage import source_coverage
        graph['source_coverage'] = source_coverage(data['source_coverage_claims'], data, graph)
        graph['source_coverage']['rechecks'] = data.get('source_coverage_rechecks', [])
    return graph
