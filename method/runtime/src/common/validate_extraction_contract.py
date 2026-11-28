"""Shared preflight/executed ES validation; runtime evidence never includes Gold."""

from __future__ import annotations
import copy
from contextlib import closing
from src.common.database_io import connect_readonly
from src.common.schema_metadata import stable_id
from src.step3_execute.compile_event_log_sql import downgrade_es_v5_to_v4, upgrade_es_v4_to_v5, event_to_case_loss
from src.step3_execute.retrieve_extraction_bindings import _identity, _rule_probe
VALIDATOR_VERSION = 'frozen-pi-validator-v1'


def freeze_pi_contract(process_view, es, graph=None):
    """PURPOSE: Freeze meaning, occurrence unit and case identity before physical repair.
    INPUT: Accepted PI, initial ES and optional EG; missing semantics remain explicit.
    OUTPUT: Content-addressed contract; never edits PI or fills meaning from Gold.
    """
    bindings = {b['id']: b for b in (graph or {}).get('event_definitions', [])}
    activities = []
    for label in process_view.get('target_activities', []):
        provenance = [p for p in process_view.get('activity_provenance', [])
                      if p.get('conceptual_activity_label') == label or
                      label in p.get('grounded_activity_labels', [])]
        ids = sorted({b for p in provenance for b in p.get('event_definition_ids', [])})
        explicit = next((a for a in process_view.get('activity_contracts', [])
                         if a.get('label') == label), {})
        semantic_evidence = [{'event_definition_id': b, 'semantic_signature': bindings[b].get('semantic_signature'),
                              'activity_source': bindings[b].get('activity_source'),
                              'occurrence_identity_rule_id': bindings[b].get('occurrence_identity_rule_id')}
                             for b in ids if b in bindings]
        activities.append({'id': stable_id('pi_activity', [process_view.get('fingerprint'), label, ids]),
                           'label': label, 'activity_semantics': copy.deepcopy(explicit.get(
                               'activity_semantics', {'status': 'unknown', 'requested_label': label,
                                                      'selected_binding_evidence': semantic_evidence})),
                           'occurrence_granularity': copy.deepcopy(explicit.get(
                               'occurrence_granularity', {'status': 'unknown',
                                   'policy': 'preserve_selected_occurrence',
                                   'original_selection_event_definition_ids': ids})),
                           'original_selection_event_definition_ids': ids})
    normalized = upgrade_es_v4_to_v5(es) if es.get('es_version') == 4 else es
    occurrence_contracts = {}
    for rule in [*normalized.get('event_rules', []), *normalized.get('selection_rules', [])]:
        source = normalized.get('event_sources', {}).get(rule.get('source_id'), {})
        occurrence_contracts[rule.get('id')] = {
            'label': rule.get('label'), 'raw_values': rule.get('raw_values', []),
            'table': source.get('table'), 'encoding': source.get('encoding'),
            'activity_column': source.get('activity_column'),
            'event_identity': copy.deepcopy(source.get('event_identity')),
            'row_condition': copy.deepcopy(source.get('row_condition')),
            'missing_values': copy.deepcopy(source.get('missing_values'))}
        if es.get('es_version') == 6:
            occurrence_contracts[rule.get('id')]['entity_instance_map_id'] = source.get(
                'case_attribution', {}).get('entity_instance_map_id')
    contract = {'version': 1, 'process_information': copy.deepcopy(process_view),
                'activities': activities,
                'occurrence_contracts': occurrence_contracts,
                'case_contract': {'case': copy.deepcopy(es.get('case')),
                                  'case_selection': copy.deepcopy(es.get('case_selection', {'kind': 'all_cases'})),
                                  'scope': process_view.get('object_scope'),
                                  'rollups': copy.deepcopy(process_view.get('selected_rollup_ids', []))}}
    contract['fingerprint'] = stable_id('frozen_pi', contract)
    return contract


def check_record(name, status, *, code=None, evidence_ids=(), details=None):
    """PURPOSE: Distinguish proof, failure, uncertainty and unexecuted validation.
    INPUT: Check name, four-state status and evidence references.
    OUTPUT: JSON check record with an explicit failure code when applicable.
    """
    if status not in {'pass', 'fail', 'unknown', 'not_run'}:
        raise ValueError('Invalid validation status')
    return {'check': name, 'status': status, 'failure_code': code,
            'evidence_ids': sorted(set(str(i) for i in evidence_ids if i)), 'details': details}


def probe_es(database, es):
    """PURPOSE: Recompute exact keys, conditioned NULL populations and case mappings.
    INPUT: Read-only SQLite snapshot and complete v4/v5 draft, including regenerated predicates.
    OUTPUT: Per-rule live probes or explicit errors; never substitutes another key or path.
    """
    expanded = downgrade_es_v5_to_v4(es) if es.get('es_version') in (5, 6) else es
    results = {}
    with closing(connect_readonly(database)) as conn:
        for rule in [*expanded.get('event_rules', []), *expanded.get('selection_rules', [])]:
            try:
                table = rule['source']['table']
                columns = rule['event_identity']['key_columns']
                identity = _identity(conn, {'name': table, 'key_candidates': [
                    {'columns': columns, 'kind': 'fixed_event_key'}]}, {}, 'reject')
                if not identity['unique']:
                    results[rule['id']] = {'identity': identity, 'error': 'event_key_invalid'}
                    continue
                probe = _rule_probe(conn, {'source_table': table}, rule.get('case', es['case']), rule.get('joins', []),
                                    identity, rule['timestamp'], source_condition=rule['source_condition'])
                # The live probe reports 0/0 as coverage 1.0; carry the materialization-time empty-result
                # approval so an empty live result is judged against confirmed rules, not that default.
                approval = rule.get('data_validation', {}).get('connection', {}).get('empty_result_approval')
                results[rule['id']] = {'identity': identity,
                                      'connection': {**probe, **({'empty_result_approval': copy.deepcopy(approval)}
                                                                 if approval else {})},
                                      'source_condition': copy.deepcopy(rule['source_condition']),
                                      'event_identity': copy.deepcopy(rule['event_identity'])}
            except Exception as error:
                results[rule.get('id', '?')] = {'error': type(error).__name__, 'detail': str(error)}
    return results


def validate_unified(es, *, process_view=None, graph=None, database=None,
                     phase='preflight', frozen_contract=None, retrieval=None, thresholds=None, baseline_execution=None):
    """PURPOSE: Apply one validation contract in Steps 3 and 4 without status laundering.
    INPUT: Draft, frozen PI/contract, EG and optional DB; phase is preflight or full.
    OUTPUT: Four-state checks, failure/evidence IDs, routing and optional executed log.
    Preflight never executes SQL. A private accepted copy is used solely by the existing
    compiler after structural checks; caller status is not changed by validation.
    """
    # Lazy imports keep orchestration out of this module's import-time dependency graph.
    from src.step3_execute.materialize_extraction_specification import validate_es, validate_physical_references
    from src.step3_execute.pipeline import structural_validation, execution_validation, extraction_diagnostics, localize_repair, reusable_execution
    if phase not in {'preflight', 'full'}:
        raise ValueError('phase must be preflight or full')
    process_view = process_view or es.get('process_view') or {}
    checks = []
    from src.common.entity_population import validate_population, source_case
    population_validation = validate_population(es, graph, database if phase == 'full' else None)
    checks.append(check_record('entity_population_contract', population_validation['contract_status'],
        code='entity_population_invalid' if population_validation['contract_status'] == 'fail' else None,
        details=population_validation['issues']))
    checks.append(check_record('entity_population_keys', population_validation['live_status'],
        code='entity_population_key_invalid' if population_validation['live_status'] == 'fail' else None,
        details=population_validation['issues']))
    from src.common.event_definition_policy import selected_binding_policy
    from src.common.runtime_input_contract import validate_runtime_graph, require_no_oracle_payload
    if graph is not None:
        validate_runtime_graph(graph)
    require_no_oracle_payload(process_view)
    binding_guard = selected_binding_policy(graph or {}, process_view) if graph is not None else {
        'status': 'not_run', 'checks': [], 'evidence_ids': []}
    checks.append(check_record('selected_binding_evidence', binding_guard['status'],
        code='binding_evidence_unresolved' if binding_guard['status'] in {'fail', 'unknown'} else None,
        evidence_ids=binding_guard['evidence_ids'], details=binding_guard['checks']))
    execution = {'passed': False, 'skipped': True, 'issues': [], 'sql': None,
                 'event_log': None, 'diagnostics': None}
    extraction = {'skipped': True, 'metrics': {}, 'signals': [], 'hard_failure': False}
    expected = frozen_contract or es.get('frozen_pi_contract')
    if expected is None:
        expected = freeze_pi_contract(process_view, es, graph)
    expected_hash = stable_id('frozen_pi', {k: v for k, v in expected.items() if k != 'fingerprint'})
    invariant = (expected.get('fingerprint') == expected_hash and
                 expected.get('process_information') == process_view and
                 es.get('process_view') == process_view and
                 expected['case_contract']['case'] == es.get('case') and
                 expected['case_contract']['case_selection'] == es.get('case_selection', {'kind': 'all_cases'}))
    if es.get('frozen_pi_contract') is not None and es['frozen_pi_contract'] != expected:
        invariant = False
    checks.append(check_record('frozen_pi', 'pass' if invariant else 'fail',
                               code=None if invariant else 'frozen_pi_changed',
                               evidence_ids=[expected.get('fingerprint')]))
    build = es.get('build_diagnostics', {})
    if (build.get('reason_code') == 'invalid_selector_output' and
            'AMBIGUOUS_CASE_MAPPING' not in str(build.get('reason'))):
        checks.append(check_record('step3_decisions', 'fail', code='step3_decision_invalid', details=build))
    if build.get('incomplete_slots'):
        checks.append(check_record('step3_materialization', 'fail', code='incomplete_materialization',
                                   details=build['incomplete_slots']))
    try:
        draft = upgrade_es_v4_to_v5(es) if es.get('es_version') == 4 else copy.deepcopy(es)
        draft['status'] = 'accepted'  # compiler input, never the returned/caller draft
        actual_occurrences = freeze_pi_contract(process_view, draft, graph)['occurrence_contracts']
        occurrence_ok = actual_occurrences == expected.get('occurrence_contracts', actual_occurrences)
        checks.append(check_record('occurrence_granularity', 'pass' if occurrence_ok else 'fail',
                                   code=None if occurrence_ok else 'occurrence_contract_changed',
                                   evidence_ids=actual_occurrences))
        structural = structural_validation(process_view, draft)
        semantic = validate_es(draft)
        for name in ('static', 'data', 'semantic'):
            layer = semantic[name]
            checks.append(check_record('preflight_' + name, 'pass' if layer['passed'] else 'fail',
                         code=None if layer['passed'] else name + '_contract_invalid', details=layer['issues'],
                         evidence_ids=[r.get('source_event_definition_id') or r.get('id') for r in draft.get('event_rules', [])]))
        if not structural['passed']:
            checks.append(check_record('structure', 'fail', code='structural_contract_invalid',
                                       details=structural['issues']))
        physical = validate_physical_references(graph, draft) if graph is not None else None
        checks.append(check_record('physical_ids', ('pass' if physical['passed'] else 'fail') if physical else 'unknown',
                      code='physical_reference_invalid' if physical and not physical['passed'] else None,
                      details=physical))
        if graph is not None:
            from src.step3_execute.repair.collect_physical_repair_candidates import timestamp_signature
            bindings = {b['id']: b for b in graph.get('event_definitions', [])}
            mismatches, unknown, invalid_receipts = [], [], []
            for rule in [*draft.get('event_rules', []), *draft.get('selection_rules', [])]:
                receipt = rule.get('repair_realization', {})
                binding = bindings.get(rule.get('source_event_definition_id') or '')
                if binding is None and receipt:
                    binding = bindings.get(receipt.get('event_definition_id'))
                if binding is None:
                    unknown.append(rule.get('id'))
                    if receipt:
                        invalid_receipts.append(rule.get('id'))
                    continue
                known = binding.get('timestamp_candidates', [])
                if known and not any(timestamp_signature(t) == timestamp_signature(rule.get('timestamp', {})) for t in known):
                    if receipt.get('kind') == 'timestamp' and receipt.get('semantic_basis') == 'documented_occurrence':
                        unknown.append(rule['id'])
                    else:
                        mismatches.append(rule['id'])
                if receipt:
                    receipt_valid = (receipt.get('id') == stable_id('repair_candidate', {
                        k: v for k, v in receipt.items() if k != 'id'}) and receipt.get('status') == 'eligible')
                    if receipt.get('kind') == 'timestamp':
                        receipt_valid = receipt_valid and timestamp_signature(receipt.get('timestamp', {})) == timestamp_signature(rule['timestamp'])
                        if receipt.get('semantic_basis') == 'selected_event_binding':
                            receipt_valid = receipt_valid and any(timestamp_signature(t) == timestamp_signature(rule['timestamp']) for t in known)
                        else:
                            from src.step3_execute.materialize_extraction_specification import _assertions, _documented_timestamp_role
                            evidence_candidates = [c for name in ('event_rule_candidates', 'residual_rule_candidates')
                                for values in (retrieval or {}).get(name, {}).values() for c in values]
                            receipt_valid = receipt_valid and any(
                                c.get('binding', {}).get('id') == binding['id'] and
                                timestamp_signature(c.get('timestamp', {})) == timestamp_signature(rule['timestamp']) and
                                (_assertions(c).get('timestamp_role') or _documented_timestamp_role(c)) == 'occurrence'
                                for c in evidence_candidates)
                    elif receipt.get('kind') == 'path':
                        source = draft['event_sources'][rule['source_id']]
                        receipt_valid = receipt_valid and receipt.get('path') == source.get('case_attribution', {}).get('relationship_path')
                        native = next((p for p in graph.get('attribution_paths', []) if p.get('id') == receipt.get('path_id')), None)
                        if native is not None:
                            receipt_valid = receipt_valid and (
                                native.get('event_definition_id') == binding['id'] and native.get('validation_status') == 'valid' and
                                native.get('to') == draft['case'].get('entity_type_id') and
                                native.get('target_table_key_id') == source_case(source, draft['case']).get('table_key_id') and
                                native.get('joins') == receipt.get('path'))
                        else:
                            evidence_candidates = [c for name in ('event_rule_candidates', 'residual_rule_candidates')
                                for values in (retrieval or {}).get(name, {}).values() for c in values]
                            receipt_valid = receipt_valid and any(c.get('binding', {}).get('id') == binding['id'] and
                                c.get('attribution_candidate_id') == receipt.get('path_id') and
                                c.get('path') == receipt.get('path') for c in evidence_candidates)
                    else:
                        receipt_valid = False
                    if not receipt_valid:
                        invalid_receipts.append(rule['id'])
            checks.append(check_record('timestamp_binding', 'fail' if mismatches else 'unknown' if unknown else 'pass',
                         code='timestamp_binding_mismatch' if mismatches else None,
                         evidence_ids=mismatches + unknown))
            if any(r.get('repair_realization') for r in draft.get('event_rules', [])):
                checks.append(check_record('repair_semantic_compatibility', 'fail' if invalid_receipts else 'pass',
                                           code='repair_evidence_invalid' if invalid_receipts else None,
                                           evidence_ids=invalid_receipts or [r.get('repair_realization', {}).get('id')
                                               for r in draft.get('event_rules', [])]))
    except Exception as error:
        draft = None
        structural = {'passed': False, 'issues': []}
        checks.append(check_record('structure', 'fail', code='draft_incomplete', details=str(error)))
    probes = {}
    # Run live probes even for a stale data certificate; they are useful repair diagnostics.
    if phase == 'full' and database is not None and draft is not None and invariant:
        try:
            probes = probe_es(database, draft)
            unavailable = [r for r, p in probes.items() if p.get('error') not in (None, 'event_key_invalid')]
            key_errors = [r for r, p in probes.items() if p.get('error') == 'event_key_invalid' or
                          (not p.get('error') and not p.get('identity', {}).get('unique'))]
            path_errors = [r for r, p in probes.items() if not p.get('error') and (
                           event_to_case_loss(p.get('connection', {})) is not None or
                           p.get('connection', {}).get('max_cases_per_event', 2) > 1)]
            for name, errors, code in [('live_keys', key_errors, 'event_key_invalid'),
                                       ('live_attribution', path_errors, 'attribution_invalid')]:
                checks.append(check_record(name, 'fail' if errors else 'unknown' if unavailable or (name == 'live_attribution' and key_errors) else 'pass',
                                           code=code if errors else None, evidence_ids=errors, details=probes))
            checks.append(check_record('timestamp_population_and_predicates', 'unknown' if key_errors or unavailable else 'pass',
                                       details=probes, evidence_ids=probes))
        except Exception as error:
            checks.append(check_record('live_keys', 'unknown', code='probe_unavailable', details=str(error)))
            checks.append(check_record('live_attribution', 'unknown', code='probe_unavailable'))
            checks.append(check_record('timestamp_population_and_predicates', 'unknown', code='probe_unavailable'))
    else:
        checks.extend(check_record(name, 'not_run') for name in
                      ('live_keys', 'live_attribution', 'timestamp_population_and_predicates'))
    # Semantics are not inferred from successful SQL or a plausible event count.
    checks.append(check_record('timestamp_semantics', 'unknown',
                               details='Initial meaning is inherited from frozen PI; replacements require EG evidence.'))
    if phase == 'full' and database is not None and draft is not None and binding_guard['status'] not in {'fail', 'unknown'} and not any(c['status'] == 'fail' for c in checks):
        execution = reusable_execution(database, es, baseline_execution) or execution_validation(database, draft)
        if execution['passed']:
            extraction = extraction_diagnostics(draft, execution['event_log'], execution['diagnostics'], thresholds=thresholds)
        checks.append(check_record('sql_execution', 'pass' if execution['passed'] else 'fail',
                                   code=None if execution['passed'] else 'sql_execution_failed', details=execution['issues']))
        checks.append(check_record('event_collision_and_deduplication',
                                   'pass' if execution['passed'] and not extraction['hard_failure'] else
                                   'fail' if execution['passed'] else 'not_run',
                                   code='event_collision' if extraction['hard_failure'] else None,
                                   details=extraction.get('signals')))
    else:
        checks.extend(check_record(name, 'not_run') for name in ('sql_execution', 'event_collision_and_deduplication'))
    failed = [c for c in checks if c['status'] == 'fail']
    full_checks = {c['check']: c['status'] for c in checks}
    hard_passed = not failed and binding_guard['status'] not in {'fail', 'unknown'} and (phase == 'preflight' or all(full_checks.get(n) == 'pass' for n in
                    ('live_keys', 'live_attribution', 'timestamp_population_and_predicates',
                     'sql_execution', 'event_collision_and_deduplication')))
    next_action = 'verify_or_repair'
    if binding_guard['status'] in {'fail', 'unknown'}:
        next_action = 'needs_step2_revision'
    if (not invariant or es.get('reason_code') in {'process_view_mutated', 'process_view_semantics_invalid'} or
            es.get('build_result', {}).get('next_action') == 'needs_step2_revision'):
        next_action = 'needs_step2_revision'
    elif draft is None:
        next_action = 'unresolved'
    return {'validator_version': VALIDATOR_VERSION, 'phase': phase,
            'status': 'valid' if hard_passed else 'repair_required', 'hard_passed': hard_passed,
            'checks': checks, 'failure_codes': sorted({c['failure_code'] for c in failed if c['failure_code']}),
            'next_action': next_action, 'frozen_pi_contract': expected,
            'process_view_fingerprint': process_view.get('fingerprint'),
            'structural': structural, 'execution': execution, 'extraction': extraction,
            'live_probes': probes, 'repair': localize_repair(structural, execution, extraction, retrieval),
            'validated_attribution_replacements': {},
            'contract': 'frozen_pi_physical_repair_only',
            'semantic_correctness': 'not_established_by_validation'}
