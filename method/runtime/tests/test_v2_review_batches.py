"""Regression checks for bounded but exhaustive candidate review."""

import pytest

from src.step2_retrieve_and_interpret.scope_review_batches import review_batches
from src.step2_retrieve_and_interpret.scope_coverage import check_scope


def test_batch_review_preserves_every_candidate_and_selected_member():
    """PURPOSE: Ensure required occurrences straddling batches can both be verified.
    INPUT: Three cards and two required events. OUTPUT: Exact merged IDs and judgments.
    """
    question = 'Show all warehouse milestones.'
    cards = [{'id': name, 'name': name} for name in ('opening', 'tracking', 'closing')]
    requirement = {'id': 'R1', 'span': 'all warehouse milestones'}
    payload = {
        'original_request': question,
        'selection': {'ids': ['opening', 'closing'], 'activities': cards},
        'activity_review': {'requirements': [requirement], 'candidates': cards,
                            'initial_proposals': [{'requirement_id': 'R1', 'event_definition_ids': ['opening', 'closing']}],
                            'revised_proposals': {}, 'scope_verification': True},
    }

    def ask(role, chunk):
        """PURPOSE: Simulate only locally visible judgments. INPUT: Review batch. OUTPUT: Partial reply."""
        assert role == 'pi_crosscheck'
        offered = chunk['activity_review']['candidates']
        matched = [a['id'] for a in offered if a['id'] != 'tracking']
        return {'differences': [], 'requirement_reviews': [
            dict(requirement_id='R1', event_definition_ids=matched, semantic_status='matched' if matched else 'missing',
                 reviewed_coverage='all', reviewed_granularity='distinct', source_attribution_gap=False,
                 reason='Documented milestone review', candidate_decisions=[
                     dict(event_definition_id=a['id'], decision='include' if a['id'] in matched else 'exclude',
                          span=requirement['span'], quote=a['name']) for a in offered])]}
    verdict, = review_batches(ask, payload, limit=2)['requirement_reviews']
    assert verdict['event_definition_ids'] == ['closing', 'opening']
    coverage = check_scope(question, verdict['candidate_decisions'], cards, verdict['event_definition_ids'], {})
    for key in ('missing_judgments', 'missing_required', 'unsupported_selection', 'invalid_judgments'):
        assert not coverage[key]
    with pytest.raises(ValueError, match='scope_review_budget_exhausted'):
        review_batches(ask, dict(payload, activity_review={**payload['activity_review'], 'candidates': cards * 8}), limit=2)


def test_context_preflight_splits_without_losing_unreviewed_candidates():
    """PURPOSE: Follow context preflight with smaller exhaustive batches.
    INPUT: A typed context error before send. OUTPUT: Complete review or an explicit unresolved budget.
    """
    from src.step2_retrieve_and_interpret.execute_model_roles import Step2ContextLimitExceeded
    from src.step2_retrieve_and_interpret.scope_review_batches import bounded_replies

    def read(chunk):
        """PURPOSE: Emulate a two-card context. INPUT: Candidate subset. OUTPUT: Accepted subset."""
        if len(chunk) > 2:
            raise Step2ContextLimitExceeded('local preflight')
        return chunk

    records = ['a', 'b', 'c', 'd', 'e']
    assert [item for batch in bounded_replies(records, read, 64) for item in batch] == records
    with pytest.raises(ValueError, match='scope_context_budget_exhausted'):
        bounded_replies(list(range(64)), read, 64)
