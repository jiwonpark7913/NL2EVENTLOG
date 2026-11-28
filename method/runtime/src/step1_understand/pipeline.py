"""Query-independent DB Understanding rewrite public API."""

from __future__ import annotations
from pathlib import Path
from typing import Any, Callable
import time
from dataclasses import asdict
from src.common.runtime_input_contract import POLICY_VERSION
from src.common.attribution_policy import POLICY as LINKING_POLICY
from src.step1_understand.interpret_event_definitions import extract_activities
from src.step1_understand.candidate_ledger import build_ledger
from src.step1_understand.resolve_activity_meanings import attach_activity_semantics, VERSION as ACTIVITY_SEMANTICS_VERSION
from src.step1_understand.assemble_evidence_graph import assemble_graph, build_table_key_records
from src.step1_understand.classify_table_event_sources import classify_tables
from src.step1_understand.eeg_configuration import DbuConfig
from src.common.database_io import load_inputs
from src.step1_understand.profile_table_values import business_value_evidence, profile_tables
from src.step1_understand.validate_table_relationships import build_relations
from src.step1_understand.profile_table_keys import profile_keys
from src.step1_understand.discover_table_references import discover_references
from src.step1_understand.assess_table_reference_evidence import classify_table_references
from src.step1_understand.validate_event_attribution_paths import attach_concept_paths, build_rollups, discover_bridges, enumerate_attribution_paths
from src.step1_understand.link_event_definitions_to_entities import attach_activity_object_links, build_activity_object_links
from src.step1_understand.validate_event_semantics import build_binding_object_associations, build_binding_pair_relationships, build_occurrence_identity_rules, validate_event_semantics
from src.step1_understand.review_uncertain_event_definitions import apply_review_decision, repair_table
from src.step1_understand.collect_event_review_evidence import candidate_interpretation_inventory, database_content_digest, direct_fk_neighbor_context, summarize_temporal_source_roles, table_uncertainties
from src.common.normalize_relation_assessments import rename_identity_references, rollup_parent_table_key_id, split_relations
from src.step1_understand.summarize_graph_construction import build_report
from src.step1_understand.detect_and_normalize_timestamps import detect_timestamps
from src.step1_understand.describe_event_semantic_signatures import SIGNATURE_SCHEMA_VERSION, attach_semantic_signatures


def _execute_meaning_first_path(
    db_path: Path, tables: list, dd: dict, profiles: dict, table_keys: list, key_profiles: list,
    references: list, config: DbuConfig, llm: Any | None, cache: dict[str, Any] | None,
    relation_records: list, calls: list, timings: dict, measured: Callable
) -> tuple[dict, list]:
    """PURPOSE: Run the meaning-first (entity_types) identity/concept path.
    INPUT: Concept-pipeline inputs plus relation_records from classify_table_references.
    OUTPUT: (entity_extension, final relation_records). The returned relations replace every
            legacy identity relation with the entity model's identity relations, sorted by id;
            build_evidence_graph uses them for rollups and the extension payload.
    SIDE EFFECTS: Extends calls with review/naming audits; measured() records timings.
                  The input relation_records list is not modified.
    """
    from src.step1_understand.identify_and_classify_entities import build_meaning_first_model

    value_evidence = measured('business_value_evidence', business_value_evidence,
        db_path, tables, dd, profiles, config.sample_size)
    entity_extension = measured('meaning_first_entity_model', build_meaning_first_model,
        db_path, tables, dd, table_keys, key_profiles, references, config,
        llm=llm, cache=cache, value_evidence=value_evidence)
    calls.extend(entity_extension.pop('entity_review_audits', []))
    if config.global_ot_review and llm is not None:
        from src.step1_understand.review_entity_meanings import name_entity_model
        calls.extend(measured('business_entity_type_naming', name_entity_model,
            entity_extension, dd, llm=llm, model=config.model, cache=cache))
        entity_extension['entity_build_stages'].append('name_entity_types_from_business_evidence')
    identity_relations = entity_extension.pop('entity_identity_relations', [])
    relation_records = [r for r in relation_records if r.get('kind') != 'identity'] + identity_relations
    relation_records.sort(key=lambda item: item['id'])

    return entity_extension, relation_records


def build_evidence_graph(db_path: Path, dd_path: Path, config: DbuConfig | None = None,
                         llm: Any | None = None, *, cache: dict[str, Any] | None = None):
    """PURPOSE: Build one query-independent Evidence Graph from the two permitted inputs.
    INPUT: SQLite path, DD JSON path, config, a required model client, and optional response cache.
    OUTPUT: EvidenceGraph with report/call audits attached; DB is opened read-only.
    """
    if llm is None:
        raise ValueError("EEG construction requires an LLM client")
    config = config or DbuConfig()
    timings: dict[str, float] = {}

    def measured(name: str, function, *args, **kwargs):
        """PURPOSE: Execute one pipeline stage and record elapsed wall time.
        INPUT: Stage name, callable and arguments.
        OUTPUT: Callable result; timing is stored in the enclosing build audit.
        """
        started = time.perf_counter()
        value = function(*args, **kwargs)
        timings[name] = time.perf_counter() - started
        return value

    tables, dd, warnings = measured("load", load_inputs, Path(db_path), Path(dd_path))
    profiles = measured("profile", profile_tables, Path(db_path), tables, config.sample_size)
    key_profiles = measured("keys", profile_keys, Path(db_path), tables)
    timestamps, ts_traces = measured("timestamps", detect_timestamps, Path(db_path), tables, profiles, dd, config)
    classifications = measured("classify", classify_tables, tables, timestamps, dd)
    calls: list[dict[str, Any]] = []
    bindings, activity_traces = measured(
        "activities", extract_activities, Path(db_path), tables, profiles, dd, timestamps, classifications, config,
        llm=llm, cache=cache, audits=calls)
    from src.step1_understand.source_coverage import reconsider_missing_pairs, source_claims
    claims = measured('source_coverage', source_claims, Path(db_path), tables, dd, timestamps, key_profiles)
    bindings, activity_traces, coverage_rechecks = measured(
        'source_coverage_rechecks', reconsider_missing_pairs, Path(db_path), tables, profiles, dd,
        timestamps, classifications, config, claims, bindings, activity_traces)
    candidate_inventory = candidate_interpretation_inventory(
        Path(db_path), tables, classifications, activity_traces, timestamps, profiles)
    # Deterministic interpretation first: review only what public evidence leaves undecided.
    attach_activity_semantics(Path(db_path), bindings, tables, timestamps, dd, llm=None,
                              model=config.model, cache=None, review_budget=0)
    uncertainties = {table.name: table_uncertainties(
        table, classifications[table.name], activity_traces[table.name], bindings, timestamps)
        for table in tables}
    event_review_queue = {name: sorted({item["reason"] for item in items})
                          for name, items in uncertainties.items()}
    review_database_digest = (database_content_digest(Path(db_path))
                              if any(event_review_queue.values()) else None)
    repair_started = time.perf_counter()
    if config.repair and llm is not None:
        for table in sorted(tables, key=lambda item: item.name):
            state = classifications[table.name]
            reasons = event_review_queue.get(table.name, [])
            if not reasons:
                continue
            decision, audit = repair_table(
                table, state, activity_traces[table.name], profiles, timestamps, dd, config, llm, cache,
                bindings=bindings, neighbors=direct_fk_neighbor_context(table, tables, dd),
                review_reasons=reasons, uncertainties=uncertainties[table.name],
                database_digest=review_database_digest, db_path=Path(db_path))
            calls.append(audit)
            if decision is None:
                state["review_status"] = "unresolved"
                continue
            bindings, state["review_status"] = apply_review_decision(
                bindings, table, state, decision, timestamps, dd, Path(db_path))
    timings["repair"] = time.perf_counter() - repair_started
    semantics_calls = measured("activity_semantics", attach_activity_semantics,
        Path(db_path), bindings, tables, timestamps, dd,
        llm=llm, model=config.model, cache=cache, review_budget=config.activity_semantic_review_budget)
    calls.extend(semantics_calls)
    if config.semantic_signatures:
        signature_calls = measured(
            "semantic_signatures", attach_semantic_signatures,
            bindings, timestamps, dd, llm=llm, model=config.model,
            cache=cache, batch_size=config.semantic_signature_batch_size,supported_only=True)
        calls.extend(signature_calls)
    relations = measured("relations", build_relations, Path(db_path), tables, dd, key_profiles)
    references, reference_diagnostics = measured(
        "references", discover_references, Path(db_path), tables, dd, relations,
        inclusion_threshold=config.inferred_inclusion_threshold,
        member_share=config.polymorphic_member_share,
        max_members=config.polymorphic_max_members)
    table_keys = build_table_key_records(tables, dd, key_profiles)
    relation_records = measured(
        "table_reference_assessments", classify_table_references, references, dd,
        db_path=Path(db_path), table_keys=table_keys, timestamps=timestamps,
        child_ref_threshold=config.part_of_child_ref_coverage,
        multi_parent_threshold=config.part_of_multi_parent_ratio,
        containment_threshold=config.part_of_interval_containment,
        precedes_threshold=config.part_of_temporal_precedes,
        tolerance_seconds=config.part_of_tolerance_seconds,
        include_identity_candidates=False)
    semantic_object_groups, global_ot_proposals, global_ot_audits = [], [], []
    ot_name_updates, provisional_groups, concept_rejections = {}, [], []

    entity_extension, relation_records = _execute_meaning_first_path(
        Path(db_path), tables, dd, profiles, table_keys, key_profiles, references,
        config, llm, cache, relation_records, calls, timings, measured)
    concepts = entity_extension['entity_types']
    bridges = measured("bridges", discover_bridges, table_keys, references)
    rollups = measured("rollups", build_rollups, table_keys, relation_records, references)
    rollups_by_parent: dict[str, list[dict[str, Any]]] = {}
    for rollup in rollups:
        rollups_by_parent.setdefault(str(rollup_parent_table_key_id(rollup)), []).append(rollup)
    for concept in concepts:
        concept["rollups"] = sorted(
            [item["id"] for member in concept.get("members", [])
             for item in rollups_by_parent.get(str(member), [])])
    attribution_paths = measured(
        "attribution", enumerate_attribution_paths, Path(db_path), bindings, table_keys,
        concepts, references, bridges, rollups, max_hops=config.max_hops, dictionary=dd)
    from src.step1_understand.entity_representations import validate_entity_attribution
    attribution_paths = measured('entity_attribution', validate_entity_attribution,
        Path(db_path), attribution_paths, concepts)
    attach_concept_paths(bindings, attribution_paths)
    event_entity_links = measured(
        'event_entity_links', build_activity_object_links,
        bindings, table_keys, concepts, references)
    attach_activity_object_links(bindings, event_entity_links)
    entity_extension['entity_build_stages'].append('link_events_to_identification_rules')
    occurrence_identity_rules = measured(
        "occurrence_identity", build_occurrence_identity_rules, bindings, table_keys)
    event_definition_pair_relationships = measured(
        'event_definition_pair_relationships', build_binding_pair_relationships,
        bindings, timestamps)
    event_entity_associations = measured(
        'event_entity_associations', build_binding_object_associations,
        bindings, concepts, timestamps, table_keys, dd)
    event_semantics_diagnostics = measured(
        "event_semantics_validation", validate_event_semantics, bindings,
        occurrence_identity_rules, event_definition_pair_relationships,
        event_entity_associations, concepts, timestamps)
    entity_extension['entity_build_stages'].append('assess_lifecycle_membership')
    extension = {**entity_extension, "entity_linking_policy":LINKING_POLICY, "key_profiles": key_profiles, "references": references,
                 "semantic_object_groups": semantic_object_groups,
                 "global_ot_review": {
                     "enabled": config.global_ot_review,
                     "provisional_groups": [
                         {"id": item["id"], "kind": item["kind"],
                          "members": item["members"], "name": item["name"]}
                         for item in provisional_groups],
                     "proposals": global_ot_proposals,
                     "final_groups": [
                         {"id": item["id"], "kind": item["kind"],
                          "members": item["members"], "name": item["name"]}
                         for item in concepts]},
                 "reference_diagnostics": reference_diagnostics,
                 **split_relations(relation_records, table_keys, references,
                                   entity_extension.get("entity_identity_decisions", [])),
                 "concepts": concepts,
                 "concept_rejected": concept_rejections,
                 "bridges": bridges, "rollups": rollups,
                 "attribution_paths": attribution_paths,
                 'event_entity_links': event_entity_links,
                 "occurrence_identity_rules": occurrence_identity_rules,
                 'event_definition_pair_relationships': event_definition_pair_relationships,
                 'event_entity_associations': event_entity_associations,
                 "event_semantics_diagnostics": event_semantics_diagnostics,
                 "event_binding_schema_version": "event-binding-v2",
                 "event_semantic_signature_schema_version": SIGNATURE_SCHEMA_VERSION}
    if "entity_identity_decisions" in extension:
        extension["entity_identity_decisions"] = rename_identity_references(
            extension["entity_identity_decisions"])
    dataset = str(dd.get("name") or Path(db_path).parent.parent.name).split()[0].casefold()
    graph = measured("assemble", assemble_graph, dataset, config.digest(), tables, dd, timestamps,
                     classifications, sorted(bindings,key=lambda item:item["id"]), relations,
                     config.max_hops, extension=extension, key_profiles=key_profiles)
    from src.step1_understand.validate_event_semantics import finalize_extraction_contracts
    finalize_extraction_contracts(graph.data, key_profiles)
    from src.step1_understand.classify_definition_validation_axes import attach_validation_axes
    measured('independent_validation_axes',attach_validation_axes,graph.data,key_profiles,Path(db_path))
    from src.common.event_definition_eligibility import review_entity_events
    calls.extend(measured('entity_event_review', review_entity_events, graph.data, dd, Path(db_path),
                          llm, config.model, cache))
    final_bindings = {b['id']: b for b in graph.data['bindings']}
    for audit in calls:
        application = audit.get('application')
        if application is not None and application.get('applied'):
            revised_times = {r['timestamp_unit_id'] for r in application.get('time_role_revisions', [])}
            affected = {change['after'] for kind in ('added', 'updated') for change in application[kind]}
            affected.update(b['id'] for b in final_bindings.values() if b['ts_id'] in revised_times)
            application['revalidation'] = {identifier: {
                'extraction_status': final_bindings[identifier].get('extraction_status'),
                'extraction_checks': final_bindings[identifier].get('extraction_checks', {}),
                'validation_axes': final_bindings[identifier].get('validation_axes', {}),
                'time_conversion': final_bindings[identifier].get('review_time_validation', {})}
                for identifier in sorted(affected) if identifier in final_bindings}

    graph.data['source_coverage_claims'] = claims
    graph.data['source_coverage_rechecks'] = coverage_rechecks
    graph.data["physical_schema"] = [asdict(table) for table in tables]
    graph.data["event_interpretation_candidates"] = candidate_inventory
    graph.data['state_history_discovery'] = [
        {'table': name, 'status': trace['state_history_status']} for name, trace in activity_traces.items()
        if trace.get('state_history_status')]
    graph.data["activity_semantics_version"] = ACTIVITY_SEMANTICS_VERSION
    graph.data["runtime_input_policy"] = POLICY_VERSION
    graph.data["input_contract_audit"] = dd.get("input_contract_audit", {})
    graph.data['carrier_timestamp_matrix'] = [
        row for trace in activity_traces.values() for row in trace.get('carrier_timestamp_matrix', [])]
    graph.data['candidate_ledger'] = build_ledger(activity_traces, ts_traces, bindings, timestamps, config.ts_scan_limit,
                                                   native=graph.data, reviews=calls)
    graph.data["build_configuration"] = asdict(config)
    graph.data["semantic_policy_version"] = "entity-scoped-event-inventory-v6-carrier-identification"
    bound_times = {item.get("ts_id") for item in bindings}
    graph.data["unresolved_temporal_units"] = [
        {"ts_id": item["ts_id"], "table": item["table"],
         "status": "unresolved", "reason": "no_event_binding"}
        for item in timestamps if item["ts_id"] not in bound_times]
    graph.data["table_roles"] = summarize_temporal_source_roles(tables, timestamps, bindings)
    graph.data["event_review_queue"] = [
        {"table": name, "reasons": reasons,
         "status": classifications[name].get("review_status", "pending")}
        for name, reasons in sorted(event_review_queue.items()) if reasons]
    report = build_report(graph.data, ts_traces, activity_traces, calls, warnings, timings)
    graph.report = report
    graph.llm_calls = calls
    graph.normalized_dictionary = dd
    graph.profiles = profiles
    graph.physical_tables = tables
    return graph
