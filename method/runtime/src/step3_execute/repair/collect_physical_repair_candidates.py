"""Query-local, evidence-constrained Timestamp/Path repair. No oracle inputs."""

from __future__ import annotations
import copy
import json
from src.common.attribution_policy import path_issues
from src.common.schema_metadata import stable_id, timestamp_columns
from src.step3_execute.compile_event_log_sql import upgrade_es_v4_to_v5, downgrade_es_v5_to_v4, event_source_id
from src.common.validate_extraction_contract import freeze_pi_contract, probe_es


def timestamp_signature(timestamp):
    """PURPOSE: Compare executable time expressions independently of metadata wording.
    INPUT: Compiler timestamp expression.
    OUTPUT: Canonical physical expression mapping, including timezone and normalization.
    """
    return {k: timestamp.get(k) for k in ('kind', 'column', 'date_column', 'clock_column',
            'time_column', 'seconds_column', 'components', 'json_path', 'detected_format',
            'format', 'timezone', 'offset_minutes', 'unit')}


def _path_signature(path):
    """PURPOSE: Identify the same directed physical joins despite extra profile fields.
    INPUT: Relationship path.
    OUTPUT: Canonical sequence retaining table, column and relationship IDs.
    """
    return [{k: e.get(k) for k in ('relationship_id', 'left_table', 'left_columns',
                                  'right_table', 'right_columns')} for e in path]


def collect_repair_candidates(graph, es, retrieval=None, *, database_snapshot=None):
    """PURPOSE: Enumerate only EG-backed timestamp/path changes for frozen activities.
    INPUT: Runtime EG, draft ES and stored retrieval; all evidence is public/runtime.
    OUTPUT: Context-addressed candidate registry, including unresolved/rejected alternatives.
    Source tables, event keys, carrier values, case identities and population stay fixed.
    """
    from src.common.runtime_input_contract import validate_runtime_graph, require_no_oracle_payload
    validate_runtime_graph(graph)
    require_no_oracle_payload(es)
    from src.step3_execute.materialize_extraction_specification import _assertions, _documented_timestamp_role
    from src.step1_understand.project_runtime_evidence_graph import _timestamp_candidate
    normalized = upgrade_es_v4_to_v5(es) if es.get('es_version') == 4 else es
    contract = normalized.get('frozen_pi_contract') or freeze_pi_contract(normalized['process_view'], normalized, graph)
    bindings = {b['id']: b for b in graph.get('event_definitions', [])}
    inventory = [c for name in ('event_rule_candidates', 'selection_rule_candidates', 'residual_rule_candidates')
                 for values in (retrieval or {}).get(name, {}).values() for c in values]
    units = {t['ts_id']: t for t in graph.get('dbu_rewrite', {}).get('timestamps', [])}
    context = stable_id('repair_context', {'contract': contract, 'es': normalized,
                         'live_database_snapshot': database_snapshot,
                         'graph_fingerprint': graph.get('database_fingerprint'),
                         'bindings': graph.get('event_definitions', []),
                         'paths': graph.get('attribution_paths', []), 'timestamps': units})
    verified_paths = (normalized['process_view'].get('process_information') or {}).get('verified_attribution_paths', {})
    registry = {}
    for rule in normalized.get('event_rules', []):
        source = normalized.get('event_sources', {}).get(rule.get('source_id'), {})
        binding = bindings.get(rule.get('source_event_definition_id'))
        if binding is None or binding.get('source_table') != source.get('table'):
            continue
        if source.get('encoding') == 'row' and (
                binding.get('activity_column') != source.get('activity_column') or
                sorted(map(str, binding.get('raw_values', []))) != sorted(map(str, rule.get('raw_values', [])))):
            continue
        activity = next((a for a in contract['activities'] if a['label'] == rule.get('label') and
                         (not a['original_selection_event_definition_ids'] or binding['id'] in a['original_selection_event_definition_ids'])), None)
        if activity is None:
            continue
        candidates = [c for c in inventory if c.get('binding', {}).get('id') == binding['id']]
        known_times = binding.get('timestamp_candidates', [])
        times = {t.get('id') or stable_id('time', t):
                 (t, 'selected_event_binding' if len(known_times) == 1 or binding.get('ts_id') == t.get('id')
                  else 'unknown', [binding['id']]) for t in known_times}
        for c in candidates:
            t = c['timestamp']
            key = t.get('id') or stable_id('time', t)
            if key not in times:
                role = _assertions(c).get('timestamp_role') or _documented_timestamp_role(c)
                times[key] = (t, 'documented_occurrence' if role == 'occurrence' else 'unknown',
                              [e['id'] for e in c.get('evidence', []) if e.get('id')])
        pairing = binding.get('timestamp_pairing') or {}
        for tid in pairing.get('alternatives', []):
            if isinstance(tid, str) and tid in units and tid not in times:
                times[tid] = (_timestamp_candidate(units[tid]), 'unknown', [tid, binding['id']])
        proposals = []
        for tid, (timestamp, basis, evidence_ids) in times.items():
            if timestamp_signature(timestamp) == timestamp_signature(rule.get('timestamp', {})):
                continue
            # A different column-event timestamp changes its occurrence discriminator;
            # allow restoration of the selected binding, not speculative replacement.
            eligible = basis == 'selected_event_binding' or (
                basis == 'documented_occurrence' and source.get('encoding') == 'row')
            from src.step1_understand.detect_and_normalize_timestamps import occurrence_time_policy
            native_time = units.get(tid)
            clock_policy = (occurrence_time_policy(native_time) if native_time is not None else
                            timestamp.get('occurrence_time_policy'))
            phase = (rule.get('timestamp_pairing') or {}).get('phase')
            candidate_phase = (native_time or timestamp).get('occurrence_phase') or {}
            if (phase in {'start', 'complete'} and candidate_phase.get('phase') != phase and
                    (candidate_phase.get('phase') or basis != 'selected_event_binding')):
                eligible = False
            if clock_policy and not clock_policy.get('eligible'):
                eligible = False
            old_clock = rule.get('timestamp', {})
            old_columns = set(timestamp_columns(old_clock)) | {old_clock[k] for k in
                ('column','date_column','clock_column','seconds_column') if old_clock.get(k)}
            new_columns = set(timestamp_columns(timestamp)) | {timestamp[k] for k in
                ('column','date_column','clock_column','seconds_column') if timestamp.get(k)}
            changed_columns = old_columns - new_columns
            predicate = json.dumps(source.get('row_condition'), sort_keys=True)
            predicate_uncertain = any(json.dumps(column) in predicate for column in changed_columns)
            if source.get('encoding') == 'column' and (
                    timestamp_columns(rule['timestamp']) != timestamp_columns(timestamp) or
                    rule['timestamp'].get('json_path') != timestamp.get('json_path')):
                eligible = False
            if predicate_uncertain:
                eligible = False
            proposals.append({'kind': 'timestamp', 'timestamp': timestamp, 'timestamp_id': tid,
                              'status': 'eligible' if eligible else 'unresolved',
                              'semantic_basis': basis, 'evidence_ids': evidence_ids,
                              'unresolved_reason': 'timestamp_dependent_predicate_requires_evidence' if predicate_uncertain else None})
        current_path = source.get('case_attribution', {}).get('relationship_path', [])
        from src.common.entity_population import source_case
        physical_case = source_case(source, normalized.get('case', {}))
        allowed_paths = verified_paths.get(binding['id'])
        for path in graph.get('attribution_paths', []):
            if allowed_paths is not None and path['id'] not in allowed_paths:
                continue
            case = physical_case
            if (path.get('event_definition_id') != binding['id'] or path.get('to') != case.get('entity_type_id') or
                    path.get('target_table_key_id') != case.get('table_key_id') or
                    path.get('rollup_ids', []) != normalized['process_view'].get('selected_rollup_ids', [])):
                continue
            if _path_signature(path.get('joins', [])) == _path_signature(current_path):
                continue
            proof = path.get('case_map', {}).get('validation', {})
            eligible = (path.get('validation_status') == 'valid' and proof.get('passed')
                        and proof.get('max_cases_per_source', 2) <= 1
                        and not path_issues(path.get('joins', []), graph.get('relationships', [])))
            source_rules = set(source.get('case_attribution', {}).get('identification_rule_ids', []))
            subject_rules = set(path.get('entity_subject_rule_ids', []))
            role_evidence = [e for ir in graph.get('dbu_rewrite', {}).get('identification_rules', [])
                if ir['id'] in source_rules & subject_rules and ir.get('status') == 'supported'
                and ir.get('source', {}).get('table') == source['table']
                and _path_signature(ir.get('joins', [])) == _path_signature(path.get('joins', []))
                and ir.get('entity_instance_map_id') == source.get('case_attribution', {}).get('entity_instance_map_id')
                for e in ir.get('evidence', []) if e.get('field') == 'definition' and e.get('text')]
            proposals.append({'kind': 'path', 'path': path.get('joins', []), 'path_id': path['id'],
                              'status': 'eligible' if eligible else 'unresolved',
                              'semantic_basis': 'same_selected_event_and_frozen_case', 'role_evidence': role_evidence,
                              'evidence_ids': [binding['id'], path['id'], path.get('case_map', {}).get('id')]})
        # Retrieval paths are accepted only when their relationship IDs occur in EG.
        edges = {e['id'] for e in graph.get('relationships', [])}
        for c in candidates:
            if allowed_paths is not None and c.get('attribution_candidate_id') not in allowed_paths:
                continue
            path = c.get('path', [])
            if _path_signature(path) == _path_signature(current_path):
                continue
            if not all(e.get('relationship_id') in edges for e in path):
                continue
            case_candidate = next((v for v in (retrieval or {}).get('case_candidates', [])
                                   if v.get('id') == c.get('case_candidate_id')), {})
            case_candidate = c.get('case_binding', case_candidate)
            if (case_candidate.get('table') != physical_case.get('table') or
                    case_candidate.get('columns') != physical_case.get('columns')):
                continue
            proof = c.get('connection_probe', {})
            eligible = (proof.get('event_to_case_coverage') == 1 and proof.get('max_cases_per_event', 2) <= 1
                        and c.get('attribution_evidence', {}).get('anchor_directed') is True
                        and not path_issues(path, graph.get('relationships', [])))
            proposals.append({'kind': 'path', 'path': path, 'path_id': c.get('attribution_candidate_id'),
                              'status': 'eligible' if eligible else 'unresolved',
                              'semantic_basis': 'same_selected_event_and_frozen_case',
                              'evidence_ids': [binding['id'], c.get('id'), c.get('attribution_candidate_id')]})
        for proposal in proposals:
            item = {**copy.deepcopy(proposal), 'rule_id': rule['id'], 'source_id': rule['source_id'],
                    'event_definition_id': binding['id'], 'pi_activity_id': activity['id'], 'context_id': context,
                    'semantic_evidence': {'signature': copy.deepcopy(binding.get('semantic_signature')),
                                          'evidence': copy.deepcopy(binding.get('evidence', [])),
                                          'frozen_activity': copy.deepcopy(activity)}}
            item['id'] = stable_id('repair_candidate', item)
            registry[item['id']] = item
    return {'context_id': context, 'frozen_pi_contract': contract, 'candidates': registry}


def materialize_candidate(es, candidate, registry):
    """PURPOSE: Apply an enumerated timestamp/path ID without free SQL/column edits.
    INPUT: Initial ES, exact registry candidate and immutable query-local registry.
    OUTPUT: Independent draft preserving source, key, raw values, case and frozen PI.
    """
    if registry['candidates'].get(candidate.get('id')) != candidate or candidate.get('status') != 'eligible':
        raise ValueError('Candidate is absent, altered, or lacks semantic evidence')
    trial = upgrade_es_v4_to_v5(es) if es.get('es_version') == 4 else copy.deepcopy(es)
    trial['frozen_pi_contract'] = copy.deepcopy(registry['frozen_pi_contract'])
    rule = next(r for r in trial['event_rules'] if r['id'] == candidate['rule_id'])
    if candidate['kind'] == 'timestamp':
        rule['timestamp'] = copy.deepcopy(candidate['timestamp'])
        rule['grounding_candidate_id'] = candidate['id']
    elif candidate['kind'] == 'path':
        from src.step3_execute.retrieve_extraction_bindings import classify_attribution_path
        source = copy.deepcopy(trial['event_sources'][rule['source_id']])
        source['case_attribution']['relationship_path'] = copy.deepcopy(candidate['path'])
        source['case_attribution']['attribution_candidate_id'] = candidate['path_id']
        source['case_attribution']['path_classification'] = classify_attribution_path(candidate['path'])
        rule['attribution_candidate_id'] = candidate['path_id']
        new_id = event_source_id(source)
        trial['event_sources'][new_id] = source
        rule['source_id'] = new_id
    else:
        raise ValueError('Source/Event Identity repair is not enabled')
    rule['realizes_pi_activity_id'] = candidate['pi_activity_id']
    rule['repair_realization'] = copy.deepcopy(candidate)
    referenced = {r['source_id'] for r in [*trial['event_rules'], *trial.get('selection_rules', [])]}
    trial['event_sources'] = {k: v for k, v in trial['event_sources'].items() if k in referenced}
    return trial


def refresh_probe_certificates(database, trial):
    """PURPOSE: Rebuild affected probe certificates without silently changing key or case.
    INPUT: Independent draft with candidate timestamp/path already materialized.
    OUTPUT: Draft with fresh data/topology evidence; validation still required.
    """
    from src.step3_execute.materialize_extraction_specification import build_case_attribution_topology
    probes = probe_es(database, trial)
    sources = {}
    for rule in [*trial['event_rules'], *trial.get('selection_rules', [])]:
        source = copy.deepcopy(trial['event_sources'][rule['source_id']])
        probe = probes.get(rule['id'], {})
        if probe.get('error'):
            raise ValueError('Live probe failed: ' + str(probe))
        source['data_validation'] = copy.deepcopy(probe)
        source['case_attribution']['cardinality'] = {k: probe['connection'][k] for k in
            ('max_cases_per_event', 'event_case_pairs', 'event_to_case_coverage')}
        sid = event_source_id(source)
        sources[sid] = source
        rule['source_id'] = sid
    trial['event_sources'] = sources
    trial['case_attribution_topology'] = build_case_attribution_topology(
        [*downgrade_es_v5_to_v4(trial)['event_rules'], *downgrade_es_v5_to_v4(trial).get('selection_rules', [])])
    return trial
