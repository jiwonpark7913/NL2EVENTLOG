"""One explicit binding-evidence policy for interpretation and physical extraction."""

from __future__ import annotations
from src.common.runtime_input_contract import EXECUTION_AXES, extraction_status_from_checks
VERSION = 'binding-eligibility-v1'


def binding_policy(binding, *, versioned=False):
    """PURPOSE: Keep meaning, pairing and physical validation distinct across stages.
    INPUT: Runtime binding and whether the graph promises current semantic metadata.
    OUTPUT: Review eligibility and four-state evidence checks; unknown never becomes confirmed.
    """
    physical = binding.get('validation_status')
    physical_status = ('fail' if physical in {'invalid', 'rejected', 'failed', 'fail'} else
                       'pass' if physical in {'valid', 'validated', 'accepted', 'pass', 'supported'} else
                       'unknown' if physical else 'not_run')
    semantics = binding.get('activity_semantics') or {}
    states = [s for s in (binding.get('interpretation_status'), semantics.get('status'),
                         semantics.get('occurrence_status')) if s]
    # Retrieval signatures steer membership only; they do not re-judge validated extraction semantics.
    if versioned and not semantics:
        states.append('unresolved')
    semantic_status = ('fail' if any(s in {'conflicting', 'rejected', 'invalid'} for s in states) else
                       'unknown' if any(s != 'supported' for s in states) else
                       'pass' if states else 'not_run')
    pairing = (binding.get('timestamp_pairing') or {}).get('status')
    pairing_status = ('pass' if pairing in {'supported', 'supported_by_review', 'valid', 'validated'} else
                      'fail' if pairing in {'invalid', 'rejected', 'conflicting', 'failed'} else
                      'unknown' if pairing else 'not_run')
    conflicts = binding.get('conflicts') or binding.get('uncertainty')
    checks = {
        'physical_validation': {'status': physical_status, 'reason': 'native_physical_validation'},
        'activity_semantics': {'status': semantic_status, 'reason': 'meaning_and_occurrence_status'},
        'timestamp_pairing': {'status': pairing_status, 'reason': 'activity_timestamp_pairing_status'},
        'binding_uncertainty': {'status': 'unknown' if conflicts else 'not_run',
                                'reason': 'retained_native_uncertainty_and_conflicts'}}
    # Only the complete four-axis payload is authoritative. Older/synthetic graphs may carry the summary
    # string alone and must retain the legacy compatibility path rather than inventing four unresolved axes.
    raw_contract = binding.get('extraction_checks')
    contract_present = isinstance(raw_contract, dict) and all(axis in raw_contract for axis in EXECUTION_AXES)
    if contract_present:
        contract = extraction_status_from_checks(raw_contract)
        axis_names = {'activity': 'activity_meaning', 'occurrence': 'occurrence_semantics',
                      'time': 'timestamp_role_and_pairing', 'identity': 'source_occurrence_identity'}
        for axis in EXECUTION_AXES:
            checks[axis_names[axis]] = {
                'status': 'pass' if contract['checks'][axis] == 'supported' else
                          'fail' if contract['checks'][axis] in {'rejected', 'invalid', 'conflicting'} else 'unknown',
                'reason': 'authoritative_step1_extraction_axis', 'details': contract['checks'][axis]}
        checks['extraction_contract'] = {
            'status': 'pass' if contract['status'] == 'executable' and
                      binding.get('extraction_status', contract['status']) == contract['status'] else 'unknown',
            'reason': 'independent_activity_time_and_identity_validation',
            'details': contract['checks'], 'unresolved_reasons': contract['unresolved_reasons']}
    for record in checks.values():
        record['evidence_ids'] = [binding['id'], *semantics.get('evidence_ids', [])]
    authoritative_executable = (contract_present and contract['status'] == 'executable' and
                                binding.get('extraction_status', contract['status']) == 'executable')
    clean = all(c['status'] in {'pass', 'not_run'} for c in checks.values())
    # Unresolved candidates stay inspectable in Step 2, while confirmation and SQL remain blocked below.
    selectable = authoritative_executable and clean if contract_present else physical_status != 'fail'
    legacy_history = (not contract_present and binding.get('extraction_status') == 'executable' and
                      semantic_status == 'pass' and clean)
    return {'history_supported': (authoritative_executable and clean) or legacy_history,
            'version': VERSION, 'review_eligible': physical_status != 'fail', 'checks': checks,
            'confirmation_allowed': clean,
            'selectable': selectable}


def selected_binding_policy(graph, process_view):
    """PURPOSE: Recheck frozen selected IDs at Step 3/4 without repairing conceptual decisions.
    INPUT: EG and PI. OUTPUT: pass/fail/unknown/not_run summary and per-binding checks.
    """
    ids = set(process_view.get('event_definitions', []))
    ids.update(b for p in process_view.get('activity_provenance', []) for b in p.get('event_definition_ids', []))
    by_id = {b['id']: b for b in (graph or {}).get('event_definitions', [])}
    checks = []
    for identifier in sorted(ids):
        if identifier not in by_id:
            checks.append({'event_definition_id': identifier, 'check': 'candidate_existence', 'status': 'fail',
                           'reason': 'selected_binding_missing_from_EG', 'evidence_ids': [identifier]})
            continue
        policy = binding_policy(by_id[identifier], versioned=bool(graph.get('activity_semantics_version')))
        checks.extend({'event_definition_id': identifier, 'check': name, **record}
                      for name, record in policy['checks'].items())
    states = {c['status'] for c in checks}
    return {'status': 'fail' if 'fail' in states else 'unknown' if 'unknown' in states else
            'pass' if 'pass' in states else 'not_run', 'checks': checks,
            'evidence_ids': sorted(ids)}
