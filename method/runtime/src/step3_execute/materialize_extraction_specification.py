"""ES v5 semantic boundary: selectors choose cards; storage separates sources and rules."""

from __future__ import annotations
import copy
import re
from collections import defaultdict
from src.common.attribution_policy import path_issues
from src.common.timestamp_policy import documented_timezone
from src.common.runtime_input_contract import validate_runtime_graph, require_no_oracle_payload
from src.common.schema_metadata import stable_id, timestamp_columns
from src.step3_execute.retrieve_extraction_bindings import classify_attribution_path
from src.step3_execute.compile_event_log_sql import downgrade_es_v5_to_v4, event_source_id, upgrade_es_v4_to_v5, validate_es as compiler_validate, EMPTY_RESULT_BASIS, event_to_case_loss, selected_definition_issues
from src.step3_execute.profile_temporal_evidence import scoped_assertions
ES_VERSION = 5


def _state(status, reason_code, reason='', **extra):
    """PURPOSE: Represent a non-success outcome without converting it into Q0.
    INPUT: Status, reason code, optional reason and diagnostic fields.
    OUTPUT: Structured ES-versioned state dictionary.
    """
    return {'es_version': ES_VERSION, 'status': status, 'reason_code': reason_code, 'reason': reason, **extra}


def candidate_cards(query, retrieval, *, use_documentation=True, use_temporal=True):
    """PURPOSE: Prepare shared selector input and controlled evidence ablations.
    INPUT: Query, retrieval, documentation/temporal on-off flags.
    OUTPUT: Copied case/source cards; identical candidate IDs across temporal ablation.
    """
    groups = {}
    for collection, purpose in (('event_rule_candidates', 'event'), ('selection_rule_candidates', 'selection')):
        for values in retrieval.get(collection, {}).values():
            for rule in values:
                gid = stable_id('group', [purpose, rule['case_candidate_id'], rule['source_key']])
                group = groups.setdefault(gid, {'id': gid, 'purpose': purpose, 'case_candidate_id': rule['case_candidate_id'],
                                               'source_key': rule['source_key'], 'activity': rule['activity'], 'candidates': []})
                card = copy.deepcopy(rule)
                if not use_documentation:
                    card['evidence'] = [e for e in card['evidence'] if e.get('layer') != 'documentation']
                if use_temporal and use_documentation:
                    knowledge = retrieval.get('temporal_knowledge') or {}
                    observations = [e for e in knowledge.get('edges', [])
                                    if card['id'] in (e['left_candidate_id'], e['right_candidate_id'])]
                    card['evidence'].extend(copy.deepcopy(observations))
                    for score in knowledge.get('candidate_scores', {}).get(card['id'], []):
                        card['evidence'].append({'id': stable_id('temporal_score', score), 'layer': 'temporal',
                                                 'kind': 'documented_temporal_consistency', **score})
                for evidence in card['evidence']:
                    evidence.setdefault('id', stable_id('evidence', evidence))
                group['candidates'].append(card)
    contexts = {}
    for group in groups.values():
        for candidate in group['candidates']:
            binding = candidate['binding']
            context = contexts.setdefault(binding['source_table'], {'row_activity_labels': [], 'activity_columns': []})
            if binding['source_kind'] == 'row_activity':
                if binding['activity'] not in context['row_activity_labels']:
                    context['row_activity_labels'].append(binding['activity'])
                if binding['activity_column'] not in context['activity_columns']:
                    context['activity_columns'].append(binding['activity_column'])
    return {'question': query['query'], 'V_q': query['V_q'], 'cases': retrieval.get('case_candidates', []), 'view_request': query.get('view_request', {}), 'source_recording_contexts': contexts, 'case_selection': retrieval.get('case_selection', {'kind': 'all_cases'}), 'groups': list(groups.values()), 'documentation_enabled': use_documentation, 'temporal_enabled': bool(use_temporal and use_documentation)}


def _assertions(rule):
    """PURPOSE: Share scoped semantic assertions with temporal profiling.
    INPUT: Candidate evidence and timestamp binding.
    OUTPUT: Sourced assertion mapping; conflicts remain unresolved.
    """
    return scoped_assertions(rule)


def _documented_timestamp_role(rule):
    """PURPOSE: Read a DD time role without confusing it with parse verification.
    INPUT: Candidate evidence containing optional timestamp-role facet records.
    OUTPUT: One documented role, conflicting when DD records disagree, or unknown.
    """
    roles = {
        evidence.get('role') for evidence in rule.get('evidence', [])
        if (evidence.get('kind') == 'timestamp_role_hypothesis'
            and evidence.get('layer') in ('data_dictionary', 'documentation')
            and evidence.get('strength') == 'strong'
            and evidence.get('role') not in (None, 'unknown'))}
    return next(iter(roles)) if len(roles) == 1 else (
        'conflicting' if roles else 'unknown')


def _event_source(candidate, case):
    """PURPOSE: Materialize table-level candidate evidence as one content-addressed Event Source.
    INPUT: Enumerated grounding candidate and fixed case binding.
    OUTPUT: (source_id, source); no activity label or timestamp is stored in the source.
    """
    binding = candidate['binding']
    row = binding['source_kind'] == 'row_activity'
    case_binding = {key: copy.deepcopy(case[key])
                    for key in ('table', 'columns', 'projection') if key in case}
    path_evidence = copy.deepcopy(candidate.get(
        'attribution_evidence', classify_attribution_path(candidate['path'])))
    case_attribution = {
        'anchor': copy.deepcopy(case_binding),
        'local_event_key': list(candidate['identity_probe']['key_columns']),
        'relationship_path': copy.deepcopy(candidate['path']),
        'cardinality': {
            'max_cases_per_event': candidate['connection_probe']['max_cases_per_event'],
            'event_case_pairs': candidate['connection_probe']['event_case_pairs'],
            'event_to_case_coverage': candidate['connection_probe']['event_to_case_coverage']},
        'multiplicity': 'one_event_per_linked_case',
        'multiplicity_policy': {
            'expected': ('many_allowed' if path_evidence.get('many_case_attribution') or
                         path_evidence.get('bridge_projection') else 'single'),
            'basis': ('validated_bridge_attribution' if path_evidence.get('many_case_attribution') or
                      path_evidence.get('bridge_projection')
                      else 'default_v1')},
        'path_classification': path_evidence,
        'attribution_candidate_id': candidate.get('attribution_candidate_id'),
        'identification_rule_ids': list(candidate.get('identification_rule_ids', []))}
    if case.get('entity_instance_map_id'):
        case_attribution['entity_instance_map_id'] = case['entity_instance_map_id']
    documented = copy.deepcopy(binding.get('documented_source_conditions', []))
    if candidate.get('role_scope'):
        documented.append(copy.deepcopy(candidate['role_scope']))
    if row and (binding.get('timestamp_pairing') or {}).get('phase') in {'start','complete'}:
        documented.append({'kind':'not_null','column':binding['timestamp_columns'][0]})
    row_condition = (None if not documented else documented[0] if len(documented) == 1
                     else {'kind': 'and', 'conditions': documented})
    source = {
        'table': binding['source_table'],
        'encoding': 'row' if row else 'column',
        'activity_column': binding.get('activity_column') if row else None,
        'translation_map_id': binding.get('translation_map_id'),
        'event_identity': {'namespace': binding['source_table'],
                           'key_columns': list(candidate['identity_probe']['key_columns'])},
        'case_attribution': case_attribution,
        'row_condition': row_condition,
        'missing_values': dict.fromkeys(
            ('case', 'event_key', 'activity', 'timestamp'), 'drop'),
        'data_validation': {
            'identity': copy.deepcopy(candidate['identity_probe']),
            'connection': {**copy.deepcopy(candidate['connection_probe']),
                           'scope': 'first_rule'}}}
    references = []
    source_object = candidate.get('source_object')
    if source_object:
        references.append({**copy.deepcopy(source_object), 'role': 'source'})
    references.append({
        'table': case['table'], 'columns': list(case['columns']),
        'entity_type_id': case.get('entity_type_id'),
        'entity_type_name': case.get('entity_type_name') or case['table'],
        'table_key_id': case.get('table_key_id'),
        'role': 'subject', 'evidence_basis': 'validated_case_attribution',
    })
    deduplicated = {}
    for reference in references:
        key = (reference['table'], tuple(reference['columns']))
        if key not in deduplicated or reference['role'] == 'subject':
            deduplicated[key] = reference
    source['object_references'] = list(deduplicated.values())
    return event_source_id(source), source


def _activity_rule(candidate, decision, source_id):
    """PURPOSE: Materialize activity-specific selection evidence as one v5 rule card.
    INPUT: Enumerated candidate, selector decision and existing Event Source ID.
    OUTPUT: Activity Rule containing label/value/time and decision evidence only.
    """
    binding = candidate['binding']
    timestamp = copy.deepcopy(candidate['timestamp'])
    assertions = _assertions(candidate)
    if (zone := documented_timezone(assertions)) and not timestamp.get('timezone'):
        timestamp['timezone'] = zone
        timestamp.pop('native_timezone', None)
    return {
        'id': candidate['id'], 'source_id': source_id,
        'source_event_definition_id': binding['id'],
        **({'eeg_candidate_validation': {key: copy.deepcopy(binding.get(key)) for key in (
            'extraction_status', 'extraction_checks', 'unresolved_reasons', 'activity_semantics',
            'occurrence_identity_status', 'source_row_key')}} if 'extraction_status' in binding else {}),
        'lifecycle_associations': copy.deepcopy(binding.get('lifecycle_associations', [])),
        'occurrence_identity_rule_id': binding.get('occurrence_identity_rule_id'),
        'activity_source': copy.deepcopy(binding.get('activity_source', {})),
        'timestamp_pairing': copy.deepcopy(binding.get('timestamp_pairing')),
        'activity_label_source': binding.get('activity_label_source', binding.get('label_origin')),
        'label': binding.get('activity_label') or binding['activity'],
        'canonical_activity_id': binding.get('canonical_activity_id') or stable_id('activity', re.sub(
            r'[^a-z0-9]+', ' ', (binding.get('activity_label') or binding['activity']).casefold()).strip()),
        'raw_values': list(binding.get('raw_values', []))
                      if binding['source_kind'] == 'row_activity' else [],
        'timestamp': timestamp,
        'eventness': decision['eventness'],
        'history_completeness': decision['history_completeness'],
        'attribution': decision['attribution'],
        'grounding_candidate_id': candidate.get('grounding_candidate_id'),
        'attribution_candidate_id': candidate.get('attribution_candidate_id'),
        'decision': copy.deepcopy(decision),
        'evidence': copy.deepcopy(candidate['evidence'])}


def _rule(candidate, case, decision):
    """PURPOSE: Preserve selector-internal v4 draft compatibility from native v5 builders.
    INPUT: Enumerated candidate, fixed case and selector decision.
    OUTPUT: Expanded draft rule; persisted ES is normalized back to v5 before validation.
    """
    case = candidate.get('case_binding', case)
    source_id, source = _event_source(candidate, case)
    activity_rule = _activity_rule(candidate, decision, source_id)
    temporary = {'es_version': ES_VERSION, 'status': 'accepted',
                 'case': {key: copy.deepcopy(case[key])
                          for key in ('table', 'columns', 'projection', 'entity_type_id',
                                      'entity_type_name', 'table_key_id') if key in case},
                 'event_sources': {source_id: source},
                 'event_rules': [activity_rule], 'selection_rules': [],
                 'case_selection': {'kind': 'all_cases'}}
    return downgrade_es_v5_to_v4(temporary)['event_rules'][0]


def materialize_event_definition(
        graph, event_definition_id: str, target_entity_type_id: str,
        selected_table_key_ids: list[str], attribution_path_id: str) -> dict:
    """PURPOSE: Deterministically materialize one graph Event/Path as an ES v5 source and rule.
    INPUT: Runtime Evidence Graph, Event ID, fixed Object Concept/member IDs and Attribution Path ID.
    OUTPUT: Ready MaterializationResult or a typed failure; never invents physical identifiers.
    """
    event_id, target_object_concept_id = event_definition_id, target_entity_type_id
    selected_member_ids = selected_table_key_ids
    failures = {
        "EVENT_NOT_FOUND", "PATH_NOT_FOUND", "TARGET_MISMATCH",
        "AMBIGUOUS_CASE_MAPPING", "UNSUPPORTED_ENCODING", "MISSING_TIMESTAMP",
        "VALIDATION_FAILED"}

    def failed(code, detail="", **extra):
        """PURPOSE: Construct one stable typed materialization failure.
        INPUT: Allowed failure code, detail and diagnostic values.
        OUTPUT: JSON-compatible failure result.
        """
        if code not in failures:
            raise ValueError(f"Unknown materialization failure: {code}")
        return {"status": "failed", "failure_code": code, "detail": detail, **extra}

    bindings = {str(item.get("id")): item for item in (
        graph.get("event_definitions") or graph.get('event_definitions', []))}
    paths = {str(item.get("id")): item for item in graph.get("attribution_paths", [])}
    objects = {str(item.get("id")): item for item in (
        graph.get("table_key_records") or graph.get('table_key_records', []))}
    concepts = {str(item.get("id")): item for item in (
        graph.get("entity_types", []) or graph.get('entity_types', [])
        or graph.get('entity_types', []))}
    binding = bindings.get(str(event_id))
    if binding is None:
        return failed("EVENT_NOT_FOUND", event_id=event_id)
    if binding.get("extraction_status") not in {None, "executable"}:
        return failed("VALIDATION_FAILED", detail="Candidate extraction evidence is unresolved",
                      extraction_checks=copy.deepcopy(binding.get("extraction_checks", {})))
    path = paths.get(str(attribution_path_id))
    if path is None or str(path.get("event_definition_id", path.get('event_definition_id'))) != str(event_id):
        return failed("PATH_NOT_FOUND", event_id=event_id,
                      attribution_path_id=attribution_path_id)
    concept = concepts.get(str(target_object_concept_id))
    selected_members = list(dict.fromkeys(map(str, selected_member_ids)))
    concept_members = set(map(str, (concept or {}).get(
        "member_object_ids", (concept or {}).get("members", []))))
    path_target = path.get("target_entity_type_id", path.get("to"))
    path_table_key = path.get("target_table_key_id", path.get('target_table_key_id'))
    if (concept is None or str(path_target) != str(target_object_concept_id) or
            not selected_members or not set(selected_members) <= concept_members or
            str(path_table_key) not in set(selected_members)):
        return failed("TARGET_MISMATCH", target_object_concept_id=target_object_concept_id,
                      selected_member_ids=selected_members,
                      path_target=path_target, path_member=path_table_key)
    validation = ((path.get("case_map") or {}).get("validation") or {})
    observed = path.get("validation_status") == "valid" and validation.get("passed")
    # An empty result is approved only by rules: a supported identification rule on this path plus a
    # fully supported activity/time/occurrence/identity contract for the Event definition.
    confirmed_empty = (path.get("validation_status") == "rule_confirmed_no_occurrences"
                       and validation.get("source_rows") == 0
                       and bool(path.get("identification_rule_ids"))
                       and all(binding.get("extraction_checks", {}).get(k) == "supported"
                               for k in ("activity", "occurrence", "time", "identity")))
    if not (observed or confirmed_empty) or validation.get("max_cases_per_source", 2) > 1:
        return failed("AMBIGUOUS_CASE_MAPPING", attribution_path_id=attribution_path_id,
                      validation=copy.deepcopy(validation))
    timestamp_candidates = list(binding.get("timestamp_candidates", []))
    if not timestamp_candidates:
        return failed("MISSING_TIMESTAMP", event_id=event_id)
    if binding.get("source_kind") not in {"row_activity", "column_event", "table_event"}:
        return failed("UNSUPPORTED_ENCODING", source_kind=binding.get("source_kind"))
    source_object = next((item for item in objects.values()
                          if item.get("anchor_table") == binding.get("source_table")), None)
    target_table_key_id = objects.get(str(path_table_key))
    if source_object is None or target_table_key_id is None:
        return failed("TARGET_MISMATCH", detail="Physical source or target member is absent")
    case = {
        "id": target_object_concept_id,
        "table": target_table_key_id["anchor_table"],
        "columns": list(target_table_key_id.get("key_columns", [])),
        'entity_type_id': target_object_concept_id,
        'entity_type_name': concept.get("name") or concept.get("label"),
        'table_key_id': target_table_key_id["id"],
    }
    if concept.get('population'):
        if concept['population'].get('status') != 'valid':
            return failed('VALIDATION_FAILED', detail='Canonical Entity population identity is unresolved')
        case['population'] = copy.deepcopy(concept['population'])
        mapping = next((m for m in concept['population']['maps'] if m['representation_id'] == target_table_key_id['id']), None)
        if mapping is None:
            return failed('TARGET_MISMATCH', detail='Target is not a canonical population provider')
        case['entity_instance_map_id'] = mapping['id']
    probe = {
        "event_rows": validation.get("source_rows", 0),
        "linked_events": validation.get("matched_source_rows", 0),
        "output_rows": validation.get("projected_pairs", 0),
        "event_case_pairs": validation.get("projected_pairs", 0),
        # No observed event means no observed ratio; the empty result is approved separately below.
        "event_to_case_coverage": (None if confirmed_empty else
            validation.get("matched_source_rows", 0) / validation.get("source_rows", 0)),
        "max_cases_per_event": validation.get("max_cases_per_source", 0),
        "null_timestamp_pairs": 0,
    }
    if confirmed_empty:
        probe["observation_status"] = "no_in_scope_rows"
        probe["empty_result_approval"] = {
            "status": EMPTY_RESULT_BASIS, "attribution_path_id": attribution_path_id,
            "identification_rule_ids": list(path.get("identification_rule_ids", [])),
            "extraction_checks": copy.deepcopy(binding.get("extraction_checks", {})),
            "target_object_concept_id": target_object_concept_id}
    candidate = {
        "id": stable_id("rule", [event_id, attribution_path_id]),
        "grounding_candidate_id": stable_id("grounding_candidate", [
            event_id, binding.get("ts_id")]),
        "attribution_candidate_id": attribution_path_id,
        "identification_rule_ids": list(path.get('identification_rule_ids', [])),
        "activity": binding.get("activity_label") or binding.get("activity"),
        "binding": binding,
        "timestamp": copy.deepcopy(timestamp_candidates[0]),
        "path": copy.deepcopy(path.get("joins", [])),
        "role_scope": copy.deepcopy(path.get("role_scope")),
        "identity_probe": {"key_columns": list(source_object.get("key_columns", [])),
                           "unique": True},
        "connection_probe": probe,
        "attribution_evidence": classify_attribution_path(path.get("joins", [])),
        "source_object": {"table": source_object["anchor_table"],
                          "columns": list(source_object.get("key_columns", [])),
                          'entity_type_id': source_object["id"],
                          'entity_type_name': source_object.get("name"),
                          'table_key_id': source_object["id"],
                          "evidence_basis": "evidence_graph_source_object"},
        "evidence": copy.deepcopy(binding.get("evidence", [])),
    }
    decision = {"action": "include", "candidate_id": candidate["id"],
                "attribution": "included", "eventness": "observed_event",
                "history_completeness": "unknown", "evidence_ids": [
                    item.get("id") for item in candidate["evidence"] if item.get("id")],
                "basis": "shared_graph_to_es_materializer"}
    source_id, source = _event_source(candidate, case)
    rule = _activity_rule(candidate, decision, source_id)
    fragment = {"es_version": ES_VERSION, "status": "accepted",
                "case": {key: value for key, value in case.items() if key != "id"},
                "event_sources": {source_id: source}, "event_rules": [rule],
                "selection_rules": [], "case_selection": {"kind": "all_cases"}}
    if case.get('population'):
        from src.common.entity_population import upgrade_entity_es
        upgrade_entity_es(fragment)
    validation_result = compiler_validate(fragment)
    if not validation_result.get("passed"):
        return failed("VALIDATION_FAILED", validation=validation_result,
                      event_id=event_id, attribution_path_id=attribution_path_id)
    return {"status": "ready", "event_id": event_id,
            "target_object_concept_id": target_object_concept_id,
            "selected_member_ids": selected_members,
            "attribution_path_id": attribution_path_id,
            "event_source_id": source_id, "event_source": source,
            "event_rule": rule, "es_fragment": fragment,
            "validation": validation_result}


def build_case_attribution_topology(rules):
    """PURPOSE: Build and validate one anchor-rooted attribution decision artifact.
    INPUT: Validated event and case-selection rules with ordered source-to-anchor paths.
    OUTPUT: Shared paths/edges and conflicts where one participating table chooses multiple parents.
    The topology constrains attribution only; it does not establish lifecycle relevance.
    """
    paths, edges, parent_choices = {}, {}, defaultdict(lambda: defaultdict(dict))
    for rule in rules:
        # Parent choice is an invariant within one Event occurrence definition.
        # Distinct row values on the same carrier are disjoint Event subsets and
        # may legitimately use different case-attribution paths.
        occurrence_scope = (rule.get('grounding_candidate_id') or
                            rule.get('source_event_definition_id') or '__unknown__')
        attribution = rule.get('case_attribution', {})
        path = attribution.get('relationship_path', rule.get('joins', []))
        value = {
            'source_table': rule['source']['table'],
            'anchor': attribution.get('anchor', rule.get('case')),
            'relationship_path': path,
            'multiplicity_policy': attribution.get('multiplicity_policy',
                                                    {'expected': 'single', 'basis': 'default_v1'}),
            'path_classification': attribution.get('path_classification',
                                                   classify_attribution_path(path)),
        }
        paths.setdefault(stable_id('case_path', value), value)
        for edge in path:
            signature = stable_id('topology_edge', {
                'relationship_id': edge['relationship_id'], 'direction': edge['direction'],
                'left_table': edge['left_table'], 'right_table': edge['right_table'],
                'left_columns': edge['left_columns'], 'right_columns': edge['right_columns']})
            edges.setdefault(signature, copy.deepcopy(edge))
            choice = parent_choices[occurrence_scope][edge['left_table']].setdefault(
                signature, {'parent': edge['right_table'], 'partitioned': True})
            decision = rule.get('decision') or {}
            choice['partitioned'] = bool(
                choice['partitioned'] and
                decision.get('partition_verified_complete') and
                decision.get('partition_id'))
    conflicts = [
        {'node': node, 'occurrence_scope': scope, 'edge_ids': sorted(choices),
         'parents': sorted({choice['parent'] for choice in choices.values()})}
        for scope, nodes in sorted(parent_choices.items())
        for node, choices in sorted(nodes.items())
        if len(choices) > 1 and not all(
            choice['partitioned'] for choice in choices.values())]
    partitioned_nodes = sorted(
        f'{scope}:{node}' for scope, nodes in parent_choices.items()
        for node, choices in nodes.items()
        if len(choices) > 1 and all(choice['partitioned'] for choice in choices.values()))
    return {'paths': list(paths.values()), 'edges': list(edges.values()), 'conflicts': conflicts,
            'partitioned_nodes': partitioned_nodes,
            'invariant': ('each participating table chooses one parent relation toward the anchor, '
                          'unless exact event-key probes certify disjoint complete path partitions'),
            'status': 'consistent' if not conflicts else 'conflicting',
            'decision_contract': 'shared_attribution_topology',
            'compilation_contract': 'independent_event_relations_union_all'}


def _condition_columns(condition):
    """PURPOSE: Enumerate physical columns used by a structured source predicate.
    INPUT: ES condition tree containing atomic or conjunction predicates.
    OUTPUT: Ordered column names; malformed terms are represented by None.
    """
    if not isinstance(condition, dict):
        return [None]
    if condition.get('kind') == 'and':
        return [column for term in condition.get('conditions', [])
                for column in _condition_columns(term)]
    if condition.get('kind') == 'state_transition':
        return [condition.get('column'), *condition.get('partition_by', []), *condition.get('order_by', [])]
    if condition.get('kind') == 'related_value':
        return condition['joins'][0]['left_columns']
    if condition.get('kind') == 'reference_role':
        return (condition['prefix'] or [condition['step']])[0]['left_columns']
    return [condition.get('column')]


def validate_physical_references(graph, es):
    """PURPOSE: Block invented table/column/join references before ES compilation.
    INPUT: Immutable schema graph and a materialized extraction specification.
    OUTPUT: Passed flag and precise issues; performs no model or database calls.
    """
    json_rule_ids = {rule.get('id') for rule in [*es.get('event_rules', []), *es.get('selection_rules', [])]
                     if es.get('event_sources', {}).get(rule.get('source_id'), {}).get('encoding') == 'json'}
    expanded = (downgrade_es_v5_to_v4(es)
                if es.get('es_version') in (5, 6) else copy.deepcopy(es))
    table_columns = {
        table['name']: {column['name'] for column in table.get('columns', [])}
        for table in graph.get('tables', [])}
    relations = {edge['id']: edge for edge in graph.get('relationships', [])}
    issues = []

    def require_table(table, context):
        """PURPOSE: Check one physical table reference against the profiled graph.
        INPUT: Table name and diagnostic context.
        OUTPUT: Its column set, or an empty set while recording an issue.
        """
        if table not in table_columns:
            issues.append(f'{context}: unknown table {table!r}')
            return set()
        return table_columns[table]

    def require_columns(table, columns, context):
        """PURPOSE: Check physical column ownership for one table.
        INPUT: Existing/unknown table, column iterable and context.
        OUTPUT: None; every violation is appended to the report.
        """
        available = require_table(table, context)
        for column in columns:
            if not isinstance(column, str) or column not in available:
                issues.append(f'{context}: column {column!r} does not exist in {table!r}')

    rules = [*expanded.get('event_rules', []), *expanded.get('selection_rules', [])]
    case = expanded.get('case', {})
    projection = case.get('projection')
    if projection:
        if projection.get('kind') != 'json_array_values':
            issues.append('case projection: unsupported projection kind')
        for rule in rules:
            require_columns(rule.get('source', {}).get('table'),
                            [projection.get('column')], 'case projection')
    else:
        require_columns(case.get('table'), case.get('columns', []), 'case binding')

    logical_case = case
    for rule in rules:
        case = rule.get('case', logical_case) if logical_case.get('population') else logical_case
        require_columns(case.get('table'), case.get('columns', []), 'case member')
        rule_id = rule.get('id', '<unknown-rule>')
        source_table = rule.get('source', {}).get('table')
        require_columns(source_table,
                        rule.get('event_identity', {}).get('key_columns', []),
                        f'{rule_id} event identity')
        activity = rule.get('activity', {})
        if activity.get('kind') != 'constant':
            require_columns(source_table, [activity.get('column')],
                            f'{rule_id} activity')
        require_columns(source_table, timestamp_columns(rule.get('timestamp', {})),
                        f'{rule_id} timestamp')
        require_columns(source_table, _condition_columns(rule.get('source_condition')),
                        f'{rule_id} source condition')

        from src.common.occurrence_conditions import occurrence_terms
        # Legacy expansion retains the source ED ID in the Activity record.
        definition_id = rule.get('source_event_definition_id') or activity.get('source_event_definition_id')
        binding = next((event for event in graph.get('event_definitions', [])
                        if event['id'] == definition_id), None)
        expected = [term for condition in (binding or {}).get('documented_source_conditions', [])
                    for term in occurrence_terms(condition)]
        relational = occurrence_terms(rule.get('source_condition'))
        selected_ids = es.get('process_view', {}).get('event_definitions')
        if relational != expected or (relational and (binding is None or
                (selected_ids is not None and definition_id not in selected_ids))):
            issues.append(f'{rule_id}: relational predicate differs from the verified ED')
        for term in relational:
            for edge in term.get('joins', []):
                require_columns(edge['left_table'], edge['left_columns'], f'{rule_id} occurrence lookup')
                require_columns(edge['right_table'], edge['right_columns'], f'{rule_id} occurrence lookup')
            if term['kind'] == 'related_value':
                require_columns(term['joins'][-1]['right_table'], [term['column']], f'{rule_id} lookup value')
        joins = rule.get('joins', [])
        references = graph.get('relationships', [])
        issues.extend(f'{rule_id}: {issue}' for issue in path_issues(joins, references))
        from src.common.attribution_policy import role_scope_issues, role_scope_steps
        scopes = role_scope_steps(rule.get('source_condition'))
        for scope in scopes:
            issues.extend(f'{rule_id}: {issue}' for issue in role_scope_issues(scope, joins, references))
        path = next((p for p in graph.get('attribution_paths', [])
                     if p.get('id') == rule.get('attribution_candidate_id')), None)
        if scopes != ([path['role_scope']] if path and path.get('role_scope') else []):
            issues.append(f'{rule_id}: Role source scope differs from the verified graph path')
        pi = es.get('process_view', {}).get('process_information') or {}
        verified = pi.get('verified_attribution_paths', {}).get(definition_id)
        if verified and (not path or path['id'] not in verified or path.get('joins') != joins):
            issues.append(f'{rule_id}: Attribution path differs from the frozen PI')
        current = source_table
        for position, join in enumerate(rule.get('joins', [])):
            context = f'{rule_id} join {position}'
            left_table, right_table = join.get('left_table'), join.get('right_table')
            left_columns = join.get('left_columns', [])
            right_columns = join.get('right_columns', [])
            require_columns(left_table, left_columns, context)
            require_columns(right_table, right_columns, context)
            if left_table != current:
                issues.append(f'{context}: path does not continue from {current!r}')
            relation = relations.get(join.get('relationship_id'))
            if relation is None:
                issues.append(f'{context}: unknown relationship ID')
            else:
                direct = (left_table == relation.get('left_table') and
                          right_table == relation.get('right_table') and
                          left_columns == relation.get('left_columns') and
                          right_columns == relation.get('right_columns'))
                reverse = (left_table == relation.get('right_table') and
                           right_table == relation.get('left_table') and
                           left_columns == relation.get('right_columns') and
                           right_columns == relation.get('left_columns'))
                if not (direct or reverse):
                    issues.append(f'{context}: columns do not match relationship ID')
            current = right_table
        if not projection and rule_id not in json_rule_ids and current != case.get('table'):
            issues.append(f'{rule_id}: join path does not reach case table')
        rule_case = rule.get('case', {})
        if rule_case != case:
            issues.append(f'{rule_id}: rule case binding differs from ES case')
    normalized = (upgrade_es_v4_to_v5(es)
                  if es.get('es_version') == 4 else copy.deepcopy(es))
    for source_id, source in normalized.get('event_sources', {}).items():
        if source.get('encoding') != 'json':
            continue
        context = f'{source_id} JSON source'
        source_table = source.get('table')
        spec = source.get('json_spec', {})
        require_columns(source_table, source.get('event_identity', {}).get('key_columns', []),
                        context + ' event identity')
        require_columns(source_table, [spec.get('payload_column')], context + ' payload')
        if source.get('row_condition') is not None:
            require_columns(source_table, _condition_columns(source['row_condition']),
                            context + ' condition')
        selectors = [spec.get('activity'), spec.get('timestamp'), spec.get('case'),
                     spec.get('event_id'), *spec.get('event_identity_fields', [])]
        physical = [selector.get('column') for selector in selectors
                    if isinstance(selector, dict) and selector.get('column')]
        require_columns(source_table, physical, context + ' selector')
        lookup = spec.get('activity_lookup')
        if lookup:
            require_columns(source_table, lookup.get('source_columns', []), context + ' lookup source')
            require_columns(lookup.get('table'), [*lookup.get('lookup_columns', []),
                                                  lookup.get('value_column')],
                            context + ' lookup table')
    process_view = normalized.get('process_view', {})
    selected_rollups = process_view.get('selected_rollup_ids', [])
    known_rollups = {item.get('id') for item in graph.get('rollups', [])}
    for rollup_id in selected_rollups:
        if rollup_id not in known_rollups:
            issues.append('Process View references unknown rollup ID: ' + str(rollup_id))
    used_relations = {edge.get('relationship_id')
                      for source in normalized.get('event_sources', {}).values()
                      for edge in source.get('case_attribution', {}).get('relationship_path', [])}
    missing_rollup_edges = set(process_view.get('selected_rollup_edge_ids', [])) - used_relations
    if missing_rollup_edges:
        issues.append('Selected rollup is absent from executable attribution paths: ' +
                      ', '.join(sorted(missing_rollup_edges)))
    return {'passed': not issues, 'issues': issues,
            'contract': 'every executable physical reference must occur in the profiled schema graph'}


def missing_process_view_activities(process_view, rules):
    """PURPOSE: Verify PV activity coverage by stable Event IDs before label fallback.
    INPUT: Process View with activity_provenance and materialized ES v4 activity rules.
    OUTPUT: Conceptual target labels lacking any selected physical Event representation.
    """
    target_labels = set(process_view.get('target_activities', []))
    rule_labels = {rule.get('activity', {}).get('label') for rule in rules}
    rule_binding_ids = {
        rule.get('activity', {}).get('source_event_definition_id') or rule.get('source_event_definition_id')
        for rule in rules}
    covered_labels = target_labels & rule_labels
    for item in process_view.get('activity_provenance', []):
        label = item.get('conceptual_activity_label')
        event_definition_ids = set(item.get('event_definition_ids', []))
        grounded_labels = set(item.get('grounded_activity_labels', []))
        if (label in target_labels and
                ((event_definition_ids and event_definition_ids & rule_binding_ids) or
                 grounded_labels & rule_labels)):
            covered_labels.add(label)
    return sorted(target_labels - covered_labels)


def project_process_view_activity_labels(process_view, rules):
    """PURPOSE: Emit query-level activity names while retaining physical Event provenance.
    INPUT: PV provenance and mutable v4 rules produced from selected Event IDs.
    OUTPUT: Same rule list with conceptual labels applied only through an unambiguous ID mapping.
    """
    labels_by_binding = defaultdict(set)
    for item in process_view.get('activity_provenance', []):
        label = item.get('conceptual_activity_label')
        if not label:
            continue
        for event_definition_id in item.get('event_definition_ids', []):
            labels_by_binding[str(event_definition_id)].add(str(label))
    for rule in rules:
        activity = rule.get('activity', {})
        event_definition_id = str(activity.get('source_event_definition_id') or
                         rule.get('source_event_definition_id') or '')
        labels = labels_by_binding.get(event_definition_id, set())
        if len(labels) != 1:
            continue
        conceptual = next(iter(labels))
        physical = activity.get('label')
        if physical != conceptual:
            activity['physical_label'] = physical
            activity['label'] = conceptual
            activity['activity_label_source'] = 'query_semantic_projection'
            rule['activity_label_source'] = 'query_semantic_projection'
    return rules


def validate_es(es):
    """PURPOSE: Check static, data-probe and semantic layers independently.
    INPUT: Candidate-built ES including probe and decision evidence.
    OUTPUT: Layered validation report and passed flag; no DB or model calls.
    """
    static = compiler_validate(es)
    expanded = (downgrade_es_v5_to_v4(es)
                if es.get('es_version') in (5, 6) else copy.deepcopy(es))
    data, semantic = [], []
    process_view = es.get('process_view', {})
    object_scope = process_view.get('object_scope', 'own_only')
    selected_rollups = process_view.get('selected_rollup_ids', [])
    if object_scope == 'own_only' and selected_rollups and process_view.get('activity_scope',
            process_view.get('request_type')) != 'explicit':
        static['issues'].append('own_only Process View cannot select rollups')
        static['passed'] = False
    expected_fingerprint = stable_id('process_view', {k: v for k, v in process_view.items() if k != 'fingerprint'}) if process_view else None
    if process_view and process_view.get('fingerprint') != expected_fingerprint:
        static['issues'].append('Process View fingerprint changed after query understanding')
        static['passed'] = False
    topology = es.get('case_attribution_topology') or build_case_attribution_topology(
        [*expanded.get('event_rules', []), *expanded.get('selection_rules', [])])
    if topology.get('conflicts'):
        static['issues'].append('Case attribution topology selects multiple parent relations for a shared node')
        static['passed'] = False
    # A PI selection contract is checked by Event definition ID in the compiler (static layer); the label
    # fallback below applies only to ESs without that contract.
    if selected_definition_issues(upgrade_es_v4_to_v5(es) if es.get('es_version') == 4 else es) is None:
        missing_targets = missing_process_view_activities(
            process_view, expanded.get('event_rules', []))
        if missing_targets:
            semantic.append('Ungrounded Process View activities: ' + ', '.join(missing_targets))
    for rule in [*expanded.get('event_rules', []), *expanded.get('selection_rules', [])]:
        probe = rule.get('data_validation', {})
        if not probe.get('identity', {}).get('unique'):
            data.append('Unverified key: ' + rule['id'])
        partition_complete = bool(
            (rule.get('decision') or {}).get('partition_verified_complete') and
            (rule.get('decision') or {}).get('partition_id'))
        loss = event_to_case_loss(probe.get('connection', {}))
        if loss and not partition_complete:
            data.append(('Unresolved event-to-case loss: ' if loss == 'event_to_case_loss'
                         else 'Unconfirmed empty Event Source: ') + rule['id'])
        if rule.get('eventness') != 'observed_event' or rule.get('attribution') != 'included':
            semantic.append('Unresolved eventness/attribution: ' + rule['id'])
    return {'static': static, 'data': {'passed': not data, 'issues': data},
            'semantic': {'passed': not semantic, 'issues': semantic}, 'passed': static['passed'] and not data and not semantic}


def build_pi_es(graph, query):
    """PURPOSE: Compile exactly the frozen PI selected Event definitions without an additional model selection.
    INPUT: Validated PI, complete Entity population and current EEG. OUTPUT: ES v6 or explicit unresolved physical failure.
    No activity is added/dropped by ranking; verified alternate paths deduplicate through canonical case IDs.
    """
    if query.get('status') != 'ready':
        return _state('selection_required','implicit_case_or_eeg_evidence_unresolved')
    return materialize_pi_selection(graph, query['query'], query.get('process_view', {}), query['V_q'])


def materialize_pi_selection(graph, question, view, analysis_context):
    """PURPOSE: Build an ESpec from a structurally bound, explicit selection of EEG rules.
    INPUT: Executable EEG projection, request, fixed Case/ED/path view and analysis context.
    OUTPUT: Frozen PI materialization using the original compiler contract.
    """
    from src.common.event_definition_eligibility import graph_for_selection
    graph = graph_for_selection(graph, view)
    target_id=view.get('target_ot_id') or view.get('target_object_selection_id')
    target=next((o for o in graph.get('entity_types',[]) if o['id']==target_id),None)
    if not target or target.get('population',{}).get('status')!='valid':
        return _state('selection_required','canonical_entity_population_unresolved')
    identifiers=list(view.get('event_definitions',[]))
    pi = view.get('process_information') or {}
    verified_paths = pi.get('verified_attribution_paths', {})
    selection = copy.deepcopy(pi.get('case_scope') or {'kind':'all_cases'})
    sources,rules={},[]
    for identifier in sorted(identifiers):
        # Observed proofs, or (when no in-scope occurrence exists) rule-confirmed empty paths yielding no rows.
        paths=[p for p in graph.get('attribution_paths',[]) if p.get('event_definition_id')==identifier and
            p.get('to')==target_id and (identifier not in verified_paths or p['id'] in verified_paths[identifier])
            and (p.get('validation_status')=='valid' and
            p.get('case_map',{}).get('validation',{}).get('passed') or
            p.get('validation_status')=='rule_confirmed_no_occurrences') and
            not path_issues(p.get('joins',[]),graph.get('relationships',[]))]
        if not paths:
            return _state('selection_required','implicit_attribution_proof_missing',event_definition_id=identifier)
        # The existing topology contract admits disjoint partitions proved on the selected ED paths.
        partition = pi.get('verified_attribution_partitions', {}).get(identifier)
        if partition:
            path_ids = sorted(path['id'] for path in paths)
            source_count = sum(path['case_map']['validation']['matched_source_rows'] for path in paths)
            partition_id = stable_id('history_partition', [graph['database_fingerprint'], target_id, identifier,
                                                            path_ids, source_count])
            if (len(path_ids) < 2 or partition.get('path_ids') != path_ids
                    or partition.get('source_occurrences') != source_count or partition.get('id') != partition_id):
                return _state('validation_failed', 'invalid_pi_attribution_partition', event_definition_id=identifier)
        # Keep validated projections and preserve the canonical Event for each executable branch.
        for path in sorted(paths,key=lambda p:(len(p.get('joins',[])),p['id'])):
            result=materialize_event_definition(graph,identifier,target_id,target.get('member_object_ids',target.get('members',[])),path['id'])
            if result.get('status')!='ready':
                return _state('validation_failed','implicit_materialization_failed',detail=result)
            sources.update(result['es_fragment']['event_sources'])
            rule = result['event_rule']
            if partition:
                rule['decision'].update(partition_id=partition['id'], partition_verified_complete=True)
            rules.append(rule)
    if 'activity_mapping' in view or 'activity_mapping' in pi:
        return _state('validation_failed', 'activity_mapping_is_not_supported')
    population=copy.deepcopy(target['population'])
    canonical=population['maps'][0]
    es={'es_version':6,'status':'accepted','query':question,'V_q':copy.deepcopy(analysis_context),
        'case':{'table':canonical['table'],'columns':list(canonical['key_columns']),
            'entity_type_id':target_id,'entity_type_name':target.get('name'),
            'table_key_id':canonical['representation_id'],'population':population},
        'event_sources':sources,'event_rules':rules,'selection_rules':[],'case_selection':selection,
        'activity_source_policy':'entity_population','process_view':copy.deepcopy(view),
        'selector':'deterministic_pi_materializer','database_fingerprint':graph['database_fingerprint'],
        'pi_materialization_contract':{'policy':'validated_selected_event_definitions',
            'request_mode':view.get('activity_scope','implicit'),'selected_event_definition_ids':sorted(identifiers),
            'process_focus':copy.deepcopy(view.get('process_focus')),
            'lifecycle_membership_gate':False,'selection_policy':'validated_PI_selected_definitions',
            'activity_label_policy':'eeg_canonical_only',
            'canonical_labels':{rule['source_event_definition_id']:rule['label'] for rule in rules}}}
    es['validation']=compiler_validate(es)
    if not es['validation']['passed']:
        es.update(status='validation_failed',reason_code='implicit_es_validation_failed')
    es['id']=stable_id('es',es)
    return es


def preserve_draft_result(graph, query, retrieval, result):
    """PURPOSE: Preserve Step 3 drafts/diagnostics and route physical failures to Step 4.
    INPUT: Runtime graph/query/retrieval and original builder result, including failures.
    OUTPUT: Compatible ES plus build envelope; incomplete or invalid decisions remain explicit.
    """
    from src.common.validate_extraction_contract import freeze_pi_contract, validate_unified
    es = copy.deepcopy(result)
    incomplete = []
    if not es.get('case') or not es.get('event_rules'):
        selection = es.get('selection') or {}
        cases = retrieval.get('case_candidates', [])
        case = next((c for c in cases if c.get('id') == selection.get('case_candidate_id')), None)
        if case:
            cards = candidate_cards(query, retrieval)
            groups = {g['id']: g for g in cards['groups'] if g['case_candidate_id'] == case['id']}
            chosen = {'event': [], 'selection': []}
            for decision in selection.get('decisions', []):
                if decision.get('action') != 'include':
                    continue
                group = groups.get(decision.get('group_id'), {})
                candidate = next((c for c in group.get('candidates', []) if c['id'] == decision.get('candidate_id')), None)
                if candidate is None:
                    incomplete.append({'code': 'unknown_candidate_id', 'candidate_id': decision.get('candidate_id')})
                    continue
                try:
                    chosen[group['purpose']].append(_rule(candidate, case, decision))
                except Exception as error:
                    incomplete.append({'code': 'materialization_failed', 'candidate_id': candidate['id'], 'detail': str(error)})
            if chosen['event']:
                project_process_view_activity_labels(query.get('process_view', {}), chosen['event'])
                draft = {'es_version': 4, 'status': es.get('status', 'validation_failed'),
                         'reason_code': es.get('reason_code'), 'case': {k: copy.deepcopy(v) for k, v in case.items()
                            if k in ('table', 'columns', 'projection', 'entity_type_id', 'entity_type_name', 'table_key_id', 'population')},
                         'event_rules': chosen['event'], 'selection_rules': chosen['selection'],
                         'case_selection': copy.deepcopy(retrieval.get('case_selection', {'kind': 'all_cases'})),
                         'activity_source_policy': 'single', 'process_view': copy.deepcopy(query.get('process_view', {})),
                         'selection': selection, 'database_fingerprint': graph.get('database_fingerprint')}
                es = {**es, **upgrade_es_v4_to_v5(draft)}
                es['case_attribution_topology'] = build_case_attribution_topology([*chosen['event'], *chosen['selection']])
    from src.common.entity_population import upgrade_entity_es
    es = upgrade_entity_es(es)
    es.setdefault('process_view', copy.deepcopy(query.get('process_view', {})))
    es['frozen_pi_contract'] = freeze_pi_contract(es['process_view'], es, graph)
    es['build_diagnostics'] = {'original_status': result.get('status'), 'reason_code': result.get('reason_code'),
                              'reason': result.get('reason'), 'validation': result.get('validation'),
                              'incomplete_slots': incomplete}
    report = validate_unified(es, process_view=query.get('process_view', {}), graph=graph,
                               phase='preflight', retrieval=retrieval)
    es['unified_validation'] = report
    has_draft = bool(es.get('case') and (es.get('event_rules') or es.get('pi_materialization_contract') or es.get('implicit_history_contract')))
    next_action = report['next_action'] if has_draft else 'unresolved'
    if result.get('status') == 'selection_required':
        next_action = 'unresolved'
    if query.get('status') != 'ready' or result.get('reason_code') == 'process_view_mutated':
        next_action = 'needs_step2_revision'
    es['build_result'] = {'build_status': 'partial_draft' if incomplete else 'draft_ready' if has_draft else 'no_draft',
                          'next_action': next_action, 'draft_es_location': 'self',
                          'candidate_refs': sorted({c['id'] for name in ('event_rule_candidates', 'selection_rule_candidates')
                            for values in retrieval.get(name, {}).values() for c in values}),
                          'incomplete_slots': incomplete}
    if has_draft and not report['hard_passed'] and result.get('status') in {'accepted', 'validation_failed'}:
        es['status'] = 'validation_failed'
    es.pop('id', None)
    es['id'] = stable_id('es', es)
    return es


def build_extraction_specification(graph, query, retrieval, **options):
    """PURPOSE: Build ES with a shared validation contract and lossless failure envelope.
    INPUT: Existing builder arguments and keyword options; public API remains compatible.
    OUTPUT: Accepted ES or preserved draft plus diagnostics/routing; no extra LLM calls.
    """
    from src.common.event_definition_policy import selected_binding_policy
    validate_runtime_graph(graph)
    require_no_oracle_payload(query.get('process_view', {}))
    from src.common.event_definition_eligibility import graph_for_selection
    pi = query.get('process_information') or query.get('process_view', {}).get('process_information') or {}
    if query.get('status') == 'partial' or pi.get('status') == 'partial':
        result = _state('selection_required', 'explicit_activity_requirements_unresolved',
                        first_failure_stage='process_view_selection')
        return preserve_draft_result(graph, query, retrieval, result)
    graph = graph_for_selection(graph, query.get('process_view', {}))
    guard = selected_binding_policy(graph, query.get('process_view', {}))
    if guard['status'] in {'fail', 'unknown'}:
        result = _state('selection_required', 'binding_evidence_unresolved',
                        binding_policy=guard, first_failure_stage='process_view_selection')
    else:
        result = build_pi_es(graph, query)
    return preserve_draft_result(graph, query, retrieval, result)
