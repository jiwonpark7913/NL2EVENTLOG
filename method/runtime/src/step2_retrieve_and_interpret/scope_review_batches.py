"""Bound review message size without pruning documentable candidates."""

from collections import deque
import json

from src.step2_retrieve_and_interpret.execute_model_roles import Step2ContextLimitExceeded

REVIEW_CARD_LIMIT = 64
MAX_BATCHES = 8


def batches(items, limit):
    """PURPOSE: Split a deterministically ordered inventory under the request review budget.
    INPUT: Full ordered candidate cards and per-message limit. OUTPUT: All non-overlapping chunks.
    An over-budget inventory remains unresolved at the caller.
    """
    if limit < 1 or len(items) > limit * MAX_BATCHES:
        raise ValueError('scope_review_budget_exhausted')
    return [items[start:start + limit] for start in range(0, len(items), limit)] or [[]]


def bounded_replies(items, request_chunk, limit):
    """PURPOSE: Split oversized model payloads without discarding unreviewed candidates.
    INPUT: Ordered inventory, existing role call and batch size. OUTPUT: Replies for a complete partition.
    """
    pending = deque(batches(items, limit))
    replies = []
    while pending:
        chunk = pending.popleft()
        try:
            replies.append(request_chunk(chunk))
        except Step2ContextLimitExceeded as error:
            if len(chunk) < 2 or len(pending) + len(replies) + 2 > MAX_BATCHES:
                raise ValueError('scope_context_budget_exhausted') from error
            halfway = len(chunk) // 2
            pending.appendleft(chunk[halfway:])
            pending.appendleft(chunk[:halfway])
    return replies


def select_batches(ask, payload, limit=REVIEW_CARD_LIMIT):
    """PURPOSE: Collect proposals from all candidate batches.
    INPUT: Existing role executor and full selection payload. OUTPUT: Grounded proposals by requirement.
    """
    cards = payload['activities']
    replies = bounded_replies(cards, lambda chunk: ask('pi_events', dict(payload, activities=chunk)), limit)
    if len(replies) == 1:
        return replies[0]['matches']
    matched = {}
    for reply in replies:
        for result in reply['matches']:
            identifier = result['requirement_id']
            matched.setdefault(identifier, set()).update(result['event_definition_ids'])
    return [{'requirement_id': identifier, 'event_definition_ids': sorted(ids)}
            for identifier, ids in sorted(matched.items())]


def _subset(payload, chunk):
    """PURPOSE: Carry the same request and case interpretation into one disjoint review batch.
    INPUT: Full role payload and cards for this batch. OUTPUT: Locally referential selected/review records.
    """
    ids = {card['id'] for card in chunk}
    review = payload['activity_review']
    selection = payload['selection']
    state = dict(selection, ids=[i for i in selection['ids'] if i in ids],
                 activities=[a for a in selection['activities'] if a['id'] in ids])
    initial = [dict(r, event_definition_ids=[e for e in r['event_definition_ids'] if e in ids])
               for r in review['initial_proposals']]
    revised = {r: [i for i in events if i in ids] for r, events in review['revised_proposals'].items()}
    step = dict(review, candidates=chunk, initial_proposals=[r for r in initial if r['event_definition_ids']],
                revised_proposals={r: events for r, events in revised.items() if events})
    if 'independent_proposal_ids' in review:
        step['independent_proposal_ids'] = [i for i in review['independent_proposal_ids'] if i in ids]
        step['independent_role_paths'] = {i: v for i, v in review['independent_role_paths'].items() if i in ids}
    partial = dict(payload, selection=state, activity_review=step)
    if 'complete_tier1_inventory' in payload:
        partial['complete_tier1_inventory'] = [a for a in payload['complete_tier1_inventory'] if a['id'] in ids]
    return partial


def review_batches(ask, payload, limit=REVIEW_CARD_LIMIT):
    """PURPOSE: Combine source-grounded per-card judgments into a single independent PI review.
    INPUT: Existing role executor and complete activity-review payload.
    OUTPUT: Same review contract, including the union of all judged candidates.
    """
    review = payload.get('activity_review')
    if not review:
        return ask('pi_crosscheck', payload)
    cards = review['candidates']
    replies = bounded_replies(cards, lambda chunk: ask(
        'pi_crosscheck', payload if len(chunk) == len(cards) else _subset(payload, chunk)), limit)
    if len(replies) == 1:
        return replies[0]
    result = {'differences': list({json.dumps(d, sort_keys=True): d for reply in replies
                                  for d in reply['differences']}.values())}
    for key in ('required_case_scope_id',):
        choices = {r[key] for r in replies if key in r}
        if len(choices) > 1:
            raise ValueError('case_scope_unresolved_across_review_batches')
        if choices:
            result[key] = next(iter(choices))
    if 'complete_tier1_inventory' in payload:
        common = set(replies[0].get('absent_from_tier1', []))
        for reply in replies[1:]:
            common.intersection_update(reply.get('absent_from_tier1', []))
        result['absent_from_tier1'] = sorted(common)
    grouped = {}
    for reply in replies:
        for item in reply['requirement_reviews']:
            grouped.setdefault(item['requirement_id'], []).append(item)
    result['requirement_reviews'] = []
    for identifier, verdicts in grouped.items():
        statuses = {item['semantic_status'] for item in verdicts}
        scopes = {item['reviewed_coverage'] for item in verdicts}
        granularities = {item['reviewed_granularity'] for item in verdicts}
        identifiers = sorted({i for item in verdicts for i in item['event_definition_ids']})
        semantic = 'matched' if identifiers else 'time_mismatch' if 'time_mismatch' in statuses else 'missing'
        if identifiers and ('ambiguous' in statuses or len(granularities) > 1):
            semantic = 'ambiguous'
        merged = {
            'requirement_id': identifier, 'event_definition_ids': identifiers,
            'semantic_status': semantic, 'reviewed_coverage': 'all' if 'all' in scopes else 'one',
            'reviewed_granularity': 'distinct' if 'distinct' in granularities else 'coarse',
            'source_attribution_gap': any(item['source_attribution_gap'] for item in verdicts),
            'reason': ' '.join(dict.fromkeys(item['reason'] for item in verdicts)),
        }
        for key in ('exclusions', 'role_path_choices', 'candidate_decisions', 'aligned_proposal_ids'):
            if any(key in item for item in verdicts):
                merged[key] = [value for item in verdicts for value in item.get(key, [])]
        result['requirement_reviews'].append(merged)
    return result
