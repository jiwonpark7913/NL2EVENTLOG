"""Query-conditioned interpretation over a DB+Data-Dictionary Event Extraction Graph."""

from __future__ import annotations
import copy
import re
from src.common.attribution_policy import bounded_hops
from src.common.schema_metadata import normalize, stable_id
from src.step2_retrieve_and_interpret.eeg_delivery import EEGDelivery
from src.common.activity_identity import activity_identity
from src.step2_retrieve_and_interpret.interpret_and_verify_process import check, select_iterative
from src.step2_retrieve_and_interpret.recover_unresolved_events import recover_explicit_events
from src.step2_retrieve_and_interpret.resolve_history_attribution import verify_explicit_path_unions
from src.common.llm_usage import DEFAULT_MODEL
from src.common.attribution_policy import MAX_ATTRIBUTION_HOPS, DEFAULT_MAX_REVISIONS
from src.eeg.evidence_graph_projections import get_physical_bindings


def _contains(text, term):
    """PURPOSE: Match complete normalized terms rather than arbitrary substrings.
    INPUT: Normalized text and normalized term.
    OUTPUT: Boolean lexical match.
    """
    if not term:
        return False
    # Korean case particles attach directly to English or Hangul concept names.
    if re.search(r'[가-힣]', text) and term in text:
        return True
    return bool(re.search(r'(?<!\w)' + re.escape(term) + r'(?!\w)', text))


def interpret_intent(question, matches):
    """PURPOSE: Separate target activities, interval boundaries and analysis intent.
    INPUT: Raw request and activity mentions grounded in the Event Extraction Graph.
    OUTPUT: Intent/mention-role evidence only; no physical binding or domain hierarchy.
    """
    boundary = re.search(r'\bfrom\s+(.+?)\s+(?:through|until|to)\s+(.+?)(?:[.?!]|$)', question, re.I)
    if boundary and re.search(r'\b(?:view|cases|database|table)\b|_cases\b', boundary[1], re.I):
        boundary = None
    purpose = re.search(r'\b(?:for|to support)\s+(.+?)(?:[.?!]|$)', question, re.I)
    intent_text = purpose[1].strip() if purpose and re.search(
        r'\b(?:analysis|fulfillment|communication|compliance|monitoring)\b', purpose[1], re.I) else None
    korean_purpose = re.search(r'(.+?)(?:분석|모니터링|준수)(?:을|를)?\s*(?:위해|위한)', question)
    if not intent_text and korean_purpose:
        intent_text = korean_purpose.group(0).strip()
    role_mentions = []
    for mention in matches:
        role = 'target'
        if boundary:
            if _contains(normalize(boundary[1]), normalize(mention['activity_mention'])):
                role = 'start_boundary'
            elif _contains(normalize(boundary[2]), normalize(mention['activity_mention'])):
                role = 'end_boundary'
        role_mentions.append({**mention, 'role': role})
    return {
        'scope_basis': 'query_and_evidence_graph',
        'analysis_intent': {'text': intent_text, 'basis': 'query_text' if intent_text else 'unspecified'},
        'activity_mentions': role_mentions,
        'boundaries': {'start': boundary[1].strip(), 'end': boundary[2].strip()} if boundary else None,
        'contract': 'anchor is not a lifecycle; relationships and temporal order do not establish relevance',
    }


def request_type_from_mode(mode):
    """PURPOSE: Name the request category without changing the executable scope mode.
    INPUT: Internal selected/full/unresolved activity-scope mode.
    OUTPUT: Explicit/implicit/unresolved request type for reports and paper terminology.
    """
    return {'selected': 'explicit', 'full': 'implicit',
            'unresolved': 'unresolved'}.get(mode, 'unresolved')


def freeze_process_view(anchor_object_type_id, mode, targets, intent, selected_view,
                        target_basis, scope_resolution, matches, selector_versions):
    """PURPOSE: Create the immutable physical-schema-free WHAT artifact.
    INPUT: Conceptual anchor/scope, provenance and selector versions.
    OUTPUT: Fingerprinted Process View with no table, column, join or SQL fields.
    """
    payload = {
        'anchor_entity_type_id': anchor_object_type_id,
        'mode': mode,
        'request_type': request_type_from_mode(mode),
        'target_activities': list(targets),
        'scope_basis': target_basis,
        'activity_provenance': [{
            'canonical_activity_id': item['canonical_activity_id'],
            'event_definition_ids': list(item.get('event_definition_ids', [])),
            'resolution_source': item.get('resolution_source', 'lexical'),
            **({'conceptual_activity_label': item['canonical']} if item.get('canonical') else {}),
            **({'grounded_activity_labels': list(item['grounded_activity_labels'])}
               if item.get('grounded_activity_labels') else {})}
            for item in matches],
        'activity_contracts': [{
            'label': label,
            'activity_semantics': {'status': 'unknown', 'requested_label': label},
            'occurrence_granularity': {'status': 'unknown', 'policy': 'preserve_selected_occurrence'}}
            for label in targets],
        'discovery_candidate_id': (selected_view or {}).get('id'),
        'selector_versions': dict(selector_versions),
        'scope_resolution_status': scope_resolution.get('status'),
        'analysis_intent': intent['analysis_intent'],
        'contract': 'immutable_conceptual_scope_no_physical_bindings',
    }
    payload['fingerprint'] = stable_id('process_view', payload)
    return payload


def interpret_process_request(question, graph, *, client, model=DEFAULT_MODEL,
                              selector_cache=None, max_hops=MAX_ATTRIBUTION_HOPS,
                              max_revisions=DEFAULT_MAX_REVISIONS, max_candidates=3,
                              semantic_top_k=10, few_shot=True, evidence_retrieval=None, recovery_enabled=True, database=None,
                              recovery_loader=None, unified=None, case_definition_loader=None,
                              case_hint_lookup=None, path_loader=None, paired_pi_controls=False):
    """PURPOSE: Interpret a request using the adopted layer-wise EEG delivery.
    INPUT: Query/graph, model/cache, provenance settings and validation bounds.
    OUTPUT: Validated Process View plus initial, validation and conditional-revision artifacts.
    """
    return _interpret_process_request(
        question, graph, client=client, model=model, selector_cache=selector_cache,
        max_hops=max_hops, max_revisions=max_revisions, max_candidates=max_candidates,
        semantic_top_k=semantic_top_k, few_shot=few_shot, evidence_retrieval=evidence_retrieval,
        eeg_delivery=EEGDelivery(graph, 'layer'), recovery_enabled=recovery_enabled, database=database,
        recovery_loader=recovery_loader, unified=unified, case_definition_loader=case_definition_loader,
        case_hint_lookup=case_hint_lookup, path_loader=path_loader, paired_pi_controls=paired_pi_controls)


def finalize_explicit_attribution(result, graph, database, path_loader=None):
    """PURPOSE: Complete physical path verification before publishing a ready Explicit PI.
    INPUT: Final semantic selection after recovery, public EEG and source SQLite.
    OUTPUT: Union receipts for the audit. Publish disjoint partitions or mark conflicting PI unresolved.
    """
    pi = result['process_information']
    if result['status'] != 'ready' or pi.get('request_mode') != 'explicit':
        return {}
    if path_loader is not None and graph.get('index_scope', {}).get('projection') == 'semantic':
        ids = {i for paths in pi.get('verified_attribution_paths', {}).values() if len(paths) > 1 for i in paths}
        if ids:
            graph = dict(graph, attribution_paths=path_loader(
                [path for path in graph['attribution_paths'] if path['id'] in ids]))
    receipts = verify_explicit_path_unions(graph, database, pi)
    partitions = {identifier: receipt['partition'] for identifier, receipt in receipts.items()
                  if receipt['status'] == 'pass' and receipt.get('partition')}
    if partitions:
        pi['verified_attribution_partitions'] = partitions
    failures = {identifier: receipt for identifier, receipt in receipts.items() if receipt['status'] != 'pass'}
    if failures:
        validation = result['final_validation']
        validation['status'] = 'unresolved'
        for identifier, receipt in failures.items():
            evidence = [identifier, *receipt['path_ids']]
            validation['checks'].append(check('explicit_attribution_union', 'fail', receipt['status'], evidence))
            validation['warnings'].append(dict(kind='explicit_attribution_unresolved', reason=receipt['status'],
                                               evidence_ids=evidence))
            pi['verified_attribution_paths'].pop(identifier)
        result.update(status='selection_required', terminal_status='unresolved',
                      termination_reason=next(iter(failures.values()))['status'])
        pi['status'] = 'selection_required'
    return receipts


def _interpret_process_request(question, graph, *, client, eeg_delivery, model=DEFAULT_MODEL,
                               selector_cache=None, max_hops=MAX_ATTRIBUTION_HOPS,
                               max_revisions=DEFAULT_MAX_REVISIONS, max_candidates=3,
                               semantic_top_k=10, few_shot=True, evidence_retrieval=None, recovery_enabled=True,
                               independent_initial=False, unified=None, database=None, recovery_loader=None,
                               case_definition_loader=None, case_hint_lookup=None, path_loader=None, paired_pi_controls=False):
    """PURPOSE: Build PI and the runtime query contract from a supplied delivery view.
    INPUT: Request/graph, interpreter settings and a payload projection; None reproduces the archived comparator.
    OUTPUT: Validated Process View and model decision trace.
    """
    max_hops = bounded_hops(max_hops)
    delivery_mode = 'current' if eeg_delivery is None else getattr(eeg_delivery, 'mode', 'custom')
    result = select_iterative(question, graph, client, model, selector_cache, max_hops=max_hops, max_revisions=max_revisions, max_candidates=max_candidates, semantic_top_k=semantic_top_k, few_shot=few_shot, evidence_retrieval=evidence_retrieval, eeg_delivery=eeg_delivery,
                              scope_verification=bool(graph.get('candidate_ledger') or graph.get('indexed_request')),
                              independent_initial=independent_initial, unified=unified, database=database,
                              case_definition_loader=case_definition_loader, case_hint_lookup=case_hint_lookup,
                              path_loader=path_loader, paired_pi_controls=paired_pi_controls)
    recovery_audit = []
    retrieval_missing = any(row['retrieval_gaps'] for row in result.get('retrieval_coverage', []))
    recovery_enabled = bool(recovery_enabled and delivery_mode == 'layer' and not retrieval_missing)
    try:
        if recovery_enabled:
            if recovery_loader is not None and result['status'] == 'partial' and any(
                    set(row.get('reason_codes', ())) & {'event_definition_missing', 'event_definition_unverified', 'case_attribution_missing'}
                    for row in result['process_information'].get('activity_requirement_results', [])):
                graph = recovery_loader(graph)
            result, graph, recovery_audit = recover_explicit_events(question, graph, result, max_hops)
        explicit_attribution = finalize_explicit_attribution(result, graph, database, path_loader)
    except ValueError:
        budget = getattr(client, 'pi_request_budget', None)
        if budget is None or not budget.exhausted:
            raise
        result.update(status='partial', terminal_status='unresolved', termination_reason=budget.exhausted)
        result['process_information']['status'] = 'partial'
        explicit_attribution = {}
    final = result['final_selection']
    get_physical_bindings(graph, list(final.get('event_definition_ids', [])))
    bindings = {item['id']: item for item in graph.get('event_definitions', [])}
    selectable = graph.get('entity_types') or graph.get('table_key_records', [])
    objects = {item['id']: item for item in selectable}
    grouped = {}
    pi = result.get('process_information') or {}
    selection_by_binding = {item['event_definition_id']: item
                            for item in final.get('activity_selections', [])}
    requested_by_id = {item.get('requested_activity_id'): item
                       for item in final.get('requested_activity_interpretations', [])
                       if item.get('requested_activity_id')}
    for event_definition_id in final.get('event_definition_ids', []):
        binding = bindings.get(event_definition_id)
        if not binding:
            continue
        physical_label = binding.get('activity_label') or binding.get('activity')
        selection_item = selection_by_binding.get(event_definition_id, {})
        requested = requested_by_id.get(selection_item.get('requested_activity_id'), {})
        conceptual_label = physical_label
        identifier = activity_identity(binding)
        record = grouped.setdefault(identifier, {
            'activity_mention': requested.get('query_expression') or
                                selection_item.get('query_expression') or conceptual_label,
            'canonical': conceptual_label,
            'canonical_activity_id': identifier,
            'event_definition_ids': [], 'resolution_source': 'candidate_constrained_llm',
            'grounded_activity_labels': []})
        record['event_definition_ids'].append(event_definition_id)
        if physical_label not in record['grounded_activity_labels']:
            record['grounded_activity_labels'].append(physical_label)
    matches = list(grouped.values())
    targets = list(dict.fromkeys(item['canonical'] for item in matches))
    selected_object_id = final.get('target_object_id')
    target_object = objects.get(selected_object_id, {})
    anchor_id = target_object.get('anchor_entity_type_id', selected_object_id)
    if selected_object_id in {c['id'] for c in graph.get('entity_types', [])}:
        case_concept_id = selected_object_id
    else:
        case_concept = next((item for item in graph.get('entity_types', [])
                             if item.get('kind') == 'entity' and
                             item.get('members') == [anchor_id]), None)
        case_concept_id = case_concept.get('id') if case_concept else None
    selected_view = {'id': stable_id('pv_candidate', selected_object_id),
                     'anchor_entity_type_id': anchor_id,
                     'target_object_concept_id': case_concept_id}
    mode = final.get('mode')
    intent = interpret_intent(question, matches)
    validation = result['final_validation']
    scope_resolution = {
        'status': 'selected' if result['status'] == 'ready' else result['status'],
        'decisions': result['revisions'],
        'warnings': validation.get('warnings', []),
        'contract': result['selector_contract']}
    process_view = freeze_process_view(
        anchor_id, mode, targets, intent, selected_view,
        'candidate_constrained_evidence_graph', scope_resolution, matches,
        {'pv_selector': 'llm_graph', 'initial': result['prompt_versions']['initial'],
         'revision': result['prompt_versions']['revision']})
    process_view.update({
        'target_object': anchor_id,
        'target_object_concept_id': case_concept_id,
        'target_object_selection_id': selected_object_id,
        'case_concept_id': case_concept_id,
        'event_definitions': list(final.get('event_definition_ids', [])),
        'object_scope': final.get('object_scope', 'own_only'),
        'selected_rollup_ids': list(final.get('selected_rollup_ids', [])),
        'selected_rollup_edge_ids': sorted({edge for item in graph.get('rollups', [])
                                            if item.get('id') in final.get('selected_rollup_ids', [])
                                            for edge in item.get('edge_ids', [])}),
        'attribution_validation_status': validation.get('status'),
        'contract': 'target_object_mode_event_definition_ids',
        'entity_linking_policy': graph.get('entity_linking_policy')})
    if result.get('terminal_status'):
        process_view.update({
            'target_ot_id': selected_object_id,
            'activity_scope': final['activity_scope'],
            'object_scope_policy': final['scope_policy'],
            'process_focus':copy.deepcopy(final.get('process_focus')),
            'process_information':copy.deepcopy(result.get('process_information')),
            'selected_events': [{'candidate_id': item['event_definition_id'],
                                 'requirement_ids': item.get('requirement_ids', [])}
                                for item in final['activity_selections']],
            'validation_status': result['terminal_status'],
            'revision_count': result['final_selection_version']})
    if target_object.get('population'):
        process_view['entity_population_contract'] = copy.deepcopy(target_object['population'])
    process_view['scope'] = {
        'mode': process_view['object_scope'],
        'derivation': copy.deepcopy(final.get('scope_evidence')),
        'selected_rollup_ids': list(process_view['selected_rollup_ids']),
        'selection_evidence': [value for value in (
            final.get('revision_reason'), final.get('reason')) if value],
    }
    process_view['activity_contracts'] = []
    for match in grouped.values():
        label = match['canonical']
        selected_bindings = [bindings[bid] for bid in match['event_definition_ids']]
        interpretations = [requested_by_id.get(selection_by_binding.get(b['id'], {}).get('requested_activity_id'), {})
                           for b in selected_bindings]
        process_view['activity_contracts'].append({
            'label': label,
            'activity_semantics': {
                'requested_interpretations': copy.deepcopy(interpretations),
                'selected_binding_semantics': [{'event_definition_id': b['id'],
                    'semantic_signature': copy.deepcopy(b.get('semantic_signature')),
                    'activity_semantics': copy.deepcopy(b.get('activity_semantics')),
                    'interpretation_status': b.get('interpretation_status'),
                    'validation_status': b.get('validation_status'),
                    'validation_evidence': copy.deepcopy(b.get('validation_evidence', [])),
                    'timestamp_pairing': copy.deepcopy(b.get('timestamp_pairing')),
                    'uncertainty': copy.deepcopy(b.get('uncertainty', [])),
                    'conflicts': copy.deepcopy(b.get('conflicts', [])),
                    'activity_source': copy.deepcopy(b.get('activity_source'))} for b in selected_bindings],
                'status': 'explicit_evidence' if any(interpretations) else 'selected_binding_evidence'},
            'occurrence_granularity': {
                'policy': 'preserve_selected_occurrence',
                'selected_occurrence_rules': [{'event_definition_id': b['id'],
                    'source_kind': b.get('source_kind'),
                    'occurrence_identity_rule_id': b.get('occurrence_identity_rule_id'),
                    'raw_values': copy.deepcopy(b.get('raw_values', []))} for b in selected_bindings]}})
    process_view['fingerprint'] = stable_id(
        'process_view', {key: value for key, value in process_view.items() if key != 'fingerprint'})
    status = result['status']
    reason_code = None if status == 'ready' else (
        'full_scope_rule_missing' if any(item.get('kind') == 'full_scope_rule_missing'
                                         for item in validation.get('warnings', []))
        else 'process_view_validation_warning')
    if status == 'partial':
        reason_code = 'explicit_activity_requirements_unresolved'
    first_failure = None if status == 'ready' else (
        'process_view_attribution_validation' if any(
            item.get('kind') in ('invalid_target_object', 'extra_invalid_binding',
                                 'attribution_unreachable_within_bound',
                                 'attribution_ambiguous', 'explicit_attribution_unresolved')
            for item in validation.get('warnings', []))
        else 'process_view_selection')
    case_name = target_object.get('name') or target_object.get('label') or target_object.get('anchor_table')
    
    return {
        'query': question, 'status': status, 'reason_code': reason_code,
        'first_failure_stage': first_failure, 'encoding_types': [],
        'reasons': [] if status == 'ready' else [reason_code], 'evidence': [],
        'V_q': {'case_notion': case_name, 'anchor_entity_type_id': anchor_id,
                'process_view_id': selected_view['id'], 'process_view_candidate_id': selected_view['id'],
                'mode': mode, 'request_type': request_type_from_mode(mode),
                'activities': targets if mode == 'selected' else None,
                'target_activities': targets,
                'target_basis': 'candidate_constrained_evidence_graph',
                'unresolved_activities': list(final.get('unresolved_activities', [])),
                'unresolved_activity_requirement_ids': [r['id'] for r in final.get('activity_requirement_results', [])
                                                        if r['status'] != 'verified']},
        'process_information':copy.deepcopy(result.get('process_information')),
        'process_view': process_view,
        'process_view_initial_selection': result['initial_selection'],
        'process_view_initial_audit': result['initial_audit'],
        'process_view_validation': validation,
        'process_view_validation_history': result['validations'],
        'process_view_revisions': result['revisions'],
        'process_view_termination_reason': result.get('termination_reason'),
        'process_interpretation_trace': {
            'cross_check': copy.deepcopy(result.get('cross_check')),
            'unresolved_event_recovery': recovery_audit,
            'unresolved_event_recovery_enabled': recovery_enabled,
            'terminal_status': result.get('terminal_status'),
            'requirements': result.get('requirements'),
            'request_parsing':copy.deepcopy(result.get('request_parsing')),
            'requirements_version': result.get('requirements_version'),
            'parsing_verification': result.get('parsing_verification'),
            'event_selection_verifications': result.get('event_selection_verifications', []),
            'case_notion_review_batch': result.get('case_notion_review_batch'),
            'implicit_selection_audit': result.get('implicit_selection_audit'),
            **({'explicit_attribution_unions': explicit_attribution} if explicit_attribution else {}),
            'entity_type_selection': copy.deepcopy(result.get('entity_type_selection')),
            'initial_candidates': result.get('initial_candidates', []),
            'rejected_initial_candidates': result.get('rejected_initial_candidates', []),
            'candidate_interpretations': result.get('candidate_interpretations', []),
            'interpretation_comparison': result.get('interpretation_comparison'),
            'candidate_count': result.get('candidate_count', 0),
            'revision_count': result.get('revision_count', 0),
            'expansion_history': result.get('expansion_history', []),
            'retrieval_coverage': [
                dict(receipt, selected=sorted(set(pi.get('selected_event_definition_ids', []))
                                              & set(receipt['cataloged']))
                     if receipt['case'] == pi.get('case_notion_et_id') else [])
                for receipt in result.get('retrieval_coverage', [])
            ],
            'model_calls': result.get('model_calls', []),
            'configuration': result.get('configuration', {})},
        'process_view_final_selection_version': result.get('final_selection_version'),
        'process_view_final_selection_fingerprint': result.get('final_selection_fingerprint'),
        'view_request': intent,
        'process_view_discovery': {
            'status': 'selected' if anchor_id else 'unresolved',
            'selected_candidate_id': selected_view['id'],
            'candidates': [selected_view],
            'selector_audit': {'selector': 'llm_graph',
                               'prompt_version': result['prompt_versions']['initial']}},
        'scope_resolution': scope_resolution,
        'model_interpretation': {
            'initial_selection': result['initial_selection'],
            'conditional_revisions': result['revisions']},
        'runtime_policy': {'input_contract': 'database+data_dictionary+question', 'pv_selector': 'llm_graph', 'db_understanding': 'native', 'retrieval_mode': 'case_indexed_subgraph' if graph.get('indexed_request') else 'full_eeg_summary', 'eeg_delivery': delivery_mode, 'semantic_top_k': semantic_top_k, 'max_revisions': max_revisions, 'validation_max_hops': max_hops},
        'runtime_manifest': {
            'input_contract': 'database+data_dictionary+question',
            'prompt_versions': result['prompt_versions'],
            'database_fingerprint': graph.get('database_fingerprint'),
            'data_dictionary_fingerprint': graph.get('data_dictionary_fingerprint')},
        'mentions': {'activities': matches, 'case': [],
                     'explicit_activities': [item.get('query_expression')
                                             for item in result['initial_selection'].get(
                                                 'activity_selections', [])],
                     'process_view': [], 'business_object': [case_name] if case_name else []},
        'scope_flags': [],
        'seeds': {'process_views': [{'process_view': selected_view['id'],
                                     'candidate_id': selected_view['id'],
                                     'card': {'case_selection': {'kind': 'all_cases'}}}],
                  'case': [], 'activities': matches},
}
