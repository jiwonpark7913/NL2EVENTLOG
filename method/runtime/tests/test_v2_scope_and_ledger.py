"""Offline regressions for candidate accounting and requirement-level selection."""

from src.common.activity_identity import activity_identity
from src.step1_understand.candidate_ledger import audit_ledger, candidate_key
from src.step2_retrieve_and_interpret.scope_coverage import check_scope, documented_family_members


def test_ledger_partitions_discovery_admission_and_projection():
    """PURPOSE: Detect a missing projection despite complete candidate accounting.
    INPUT: Three physical candidates and one verified family replacement.
    OUTPUT: Correct decision, projection and discovery-limit counters.
    """
    integer = candidate_key('carrier_event', {'table': 'jobs', 'value': 1})
    text = candidate_key('carrier_event', {'table': 'jobs', 'value': '1'})
    assert integer != text
    ledger = {'candidates': [
        {'id': integer, 'decision': 'approved', 'reason': 'source', 'definition_id': 'broad'},
        {'id': text, 'decision': 'approved', 'reason': 'source', 'definition_id': 'missing'},
        {'id': 'uncertain', 'decision': 'unresolved', 'reason': 'unknown phase'},
    ], 'discovery_limits': [{'table': 'jobs'}]}
    audit = audit_ledger(ledger, {
        'event_definitions': [{'id': 'narrow', 'extraction_status': 'executable'}],
        'event_definition_migration': {'broad': {'status': 'replaced_by_family', 'replacement_ids': ['narrow']}},
    })['audit']
    assert (audit['enumerated'], audit['decided'], audit['approved'], audit['represented']) == (3, 3, 2, 1)
    assert audit['discovery_limited'] and audit['missing_projections'] == [text]


def test_same_label_does_not_merge_distinct_occurrences():
    """PURPOSE: Keep proven occurrence phases and unproved equivalence separate.
    INPUT: Three EDs with identical display strings.
    OUTPUT: Distinct Activity identities and invariance under display-only edits.
    """
    start = {'id': 'e1', 'source_table': 'jobs', 'activity_label': 'Work',
             'timestamp_pairing': {'phase': 'start'}}
    finish = {**start, 'id': 'e2', 'timestamp_pairing': {'phase': 'complete'}}
    other = {**start, 'id': 'e3'}
    assert len({activity_identity(d) for d in (start, finish, other)}) == 3
    assert activity_identity(start) == activity_identity({**start, 'activity_label': 'Job started'})


def test_scope_cannot_approve_only_one_documented_family_member():
    """PURPOSE: Reproduce a model agreement on a wrong singleton without dataset-specific IDs.
    INPUT: Two documented start milestones with valid case attribution and a singleton review.
    OUTPUT: Missing peer diagnosis, then a complete scope when both are selected.
    """
    span = 'actual opening milestones'
    question = 'Show actual opening milestones for each shipment.'
    shared = {'source': 'dispatch', 'case_attribution': 'pass', 'eligible': True,
              'occurrence_time': {'columns': ['at']},
              'source_context': ['Actual FIRST and SECOND are opening milestones.']}
    offered = [dict(shared, id='a', name='Door opens', carrier_code='FIRST'),
               dict(shared, id='b', name='Ramp opens', carrier_code='SECOND')]
    required = documented_family_members({'span': span, 'coverage': 'one'}, ['a'], offered)
    assert required == {'b'}
    decisions = [dict(event_definition_id=i, decision=status, span=span, quote=shared['source_context'][0])
                 for i, status in [('a', 'include'), ('b', 'exclude')]]
    result = check_scope(question, decisions, offered, ['a'], {}, required=required)
    assert result['missing_required'] == ['b']
    assert not result['missing_judgments']
    decisions[-1]['decision'] = 'include'
    assert not check_scope(question, decisions, offered, ['a', 'b'], {}, required=required)['missing_required']
    assert check_scope(question, decisions[:1], offered, ['a'], {})['missing_judgments'] == ['b']


def test_recovery_identity_is_independent_of_available_semantic_signature():
    """PURPOSE: Keep initial and recovered IDs stable for the exact same ED.
    INPUT: Same physical occurrence with/without semantic signature. OUTPUT: Same identity.
    """
    physical = {'id': 'ed', 'source_table': 'fact', 'source_row_key': ['id']}
    annotated = dict(physical, semantic_signature={'subject_id': 'business_object', 'temporal_role': 'actual'})
    assert activity_identity(physical) == activity_identity(annotated)


def test_missing_model_review_and_unexecutable_decision_have_distinct_receipts():
    """PURPOSE: Record a missing model response independently from a known incomplete extraction contract.
    INPUT: Candidate review with no returned ID and a separate supported carrier/clock pair.
    OUTPUT: Missing review receipt and an unresolved candidate without a projection error.
    """
    from src.step1_understand.candidate_ledger import build_ledger
    traces = {'source': {'carrier_timestamp_matrix': [
        {'carrier': 'kind', 'value': 'A', 'ts_id': 'observed', 'candidate_id': 'a', 'status': 'supported',
         'reason': 'clock_role_verified', 'timed_rows': 1, 'population': 1}]}}
    bindings = [{'id': 'a', 'table': 'source', 'ts_id': 'observed', 'alpha': {
        'kind': 'value', 'column': 'kind', 'value': 'A'}, 'extraction_status': 'unresolved'}]
    ledger = build_ledger(traces, {}, bindings, [], 100, reviews=[
        {'kind': 'carrier_value_semantics', 'table': 'source', 'carrier_column': 'kind',
         'missing_candidate_ids': ['b']}])
    audited = audit_ledger(ledger, {'event_definitions': [{'id': 'a', 'extraction_status': 'unresolved'}]})
    candidate, = audited['candidates']
    assert candidate['semantic_status'] == 'supported'
    assert candidate['decision'] == 'unresolved'
    assert audited['audit']['missing_decisions'][0]['candidate_id'] == 'b'
    assert not audited['audit']['missing_projections']
