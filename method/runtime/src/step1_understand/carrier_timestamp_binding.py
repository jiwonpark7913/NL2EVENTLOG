"""Evidence-based relationships between individual carrier values and source clocks."""

import re

from src.common.event_clock import documented_message_receipt_clock

from src.step1_understand.detect_and_normalize_timestamps import (
    documented_action_clock, name_tokens, occurrence_time_policy,
)

_PHASE_TERMS = {
    'start': {'start', 'started', 'beginning', 'began', 'commenced'},
    'complete': {'finish', 'finished', 'end', 'ended', 'complete', 'completed', 'completion'},
}
_CLOCK_WORDS = {'actual', 'utc', 'date', 'time', 'timestamp', 'of', 'for', 'the', 'this', 'a', 'an'}
_ENDPOINT_CONNECTORS = {'at', 'which', 'was', 'is', 'were', 'assigned', 'confirmed', 'recorded'}
_WORK_TERMS = {'job', 'jobs', 'task', 'tasks', 'operation', 'operations', 'work'}


def documented_phase(unit, definition):
    """PURPOSE: Identify an explicit actual-occurrence endpoint. INPUT: Timestamp unit and DD prose. OUTPUT: Phase or None."""
    if (unit.get('json_path') or len(unit['columns']) != 1 or unit.get('semantic_role') != 'business_occurrence'
            or not occurrence_time_policy(unit)['eligible']):
        return None
    words = set(name_tokens(definition.split(';', 1)[0]))
    matches = [phase for phase, terms in _PHASE_TERMS.items() if words & terms]
    return matches[0] if len(matches) == 1 else None


def _endpoint_subject(definition, phase):
    """PURPOSE: Extract the subject shared by start and completion clock descriptions.
    INPUT: Public clock prose and its established phase. OUTPUT: Normalized subject tokens.
    """
    return tuple(word for word in name_tokens(definition.split(';', 1)[0])
                 if word not in _PHASE_TERMS[phase] | _CLOCK_WORDS)


def _work_subject(subject):
    """PURPOSE: Compare equivalent generic work-record nouns.
    INPUT: Documented endpoint or carrier subject tokens. OUTPUT: Normalized subject tokens.
    """
    return tuple('work' if word in _WORK_TERMS else word
                 for word in subject if word not in _ENDPOINT_CONNECTORS)


def documented_work_endpoints(table_text, clocks):
    """PURPOSE: Establish paired work-row endpoints before interpreting carrier clock candidates.
    INPUT: Public table definition and its (timestamp unit, clock definition) pairs. OUTPUT: Documented phases.
    """
    if not set(name_tokens(table_text)) & _WORK_TERMS:
        return frozenset()
    return frozenset(phase for unit, definition in clocks
                     if (phase := documented_phase(unit, definition)) and
                     _work_subject(_endpoint_subject(definition, phase)) == ('work',))


def _carrier_action(carrier, alpha, semantics, subject, *, paired_work_endpoint):
    """PURPOSE: Ground a carrier value as an action of the documented endpoint subject.
    INPUT: Carrier documentation, selector, supported meaning, and paired same-row endpoint evidence.
    OUTPUT: Base action, or None if the link or action is unsupported.
    """
    description = carrier.get('definition', '')
    domain = carrier.get('value_domain', {}).get(str(alpha['value']), {})
    documents_action = re.search(r'\b(?:business[- ]action|activity|operation|work type|action type)\b',
                                 description, re.I)
    carrier_subject = tuple(word for word in name_tokens(alpha['column'])
                            if word not in {'type', 'code', 'kind', 'category'})
    same_subject = (carrier_subject == subject or
                    (paired_work_endpoint and _work_subject(carrier_subject) == _work_subject(subject) == ('work',)))
    if not documents_action and not (semantics['status'] == 'supported' and same_subject):
        return None
    action = domain.get('label') or semantics.get('code_meaning')
    if action and not re.search(r'\b(?:estimated?|planned|scheduled|expected)\b', action, re.I):
        return action
    return None


def endpoint_label(action, phase):
    """PURPOSE: Give independently established endpoints different canonical labels.
    INPUT: Supported activity meaning and optional phase. OUTPUT: Activity with its actual phase.
    """
    if phase is None:
        return action
    base = re.sub(r'\s+(?:completed|started|finished|ended|closed|start|completion|finish|end|close)$',
                  '', action, flags=re.I)
    return f"{base} {'started' if phase == 'start' else 'completed'}"


def carrier_clock_relationship(unit, clock, carrier, alpha, resolution, statistic, *, work_endpoints=()):
    """PURPOSE: Independently validate one value/clock relationship.
    INPUT: Clock evidence, carrier selector, observed support and documented same-row work endpoints.
    OUTPUT: Auditable status, occurrence phase, optional canonical label and cited clock basis.
    """
    role = unit.get('semantic_role', 'unknown')
    phase = documented_phase(unit, clock.get('definition', ''))
    meaning = resolution['code_meaning']
    result = {'clock_role':role, 'phase':None, 'status':'unresolved',
              'reason':'clock_does_not_document_the_value_event', 'clock_evidence_id':clock.get('id')}
    if unit.get('row_value_scope') and role in {'scheduled_time','estimated_time'}:
        return {**result, 'status':'non_occurrence', 'reason':'represented_non_actual_time'}
    if role in {'scheduled_time','estimated_time','recorded_time','ingestion_time','non_event_time'}:
        return {**result, 'status':'excluded', 'reason':'documented_non_occurrence_role'}
    if documented_message_receipt_clock(clock.get('definition','')):
        return {**result, 'status':'independent_clock', 'reason':'separate_documented_message_receipt'}
    if resolution['status'] != 'supported':
        return {**result, 'reason': 'carrier_value_semantics_' + resolution['status']}
    if not occurrence_time_policy(unit)['eligible']:
        return result
    if unit.get('row_value_scope'):
        return {**result, 'status':'supported', 'label':meaning,
                'reason':'documented_value_scoped_represented_time'}
    lifecycle = carrier.get('code_lifecycle', {}).get(str(alpha.get('value')))
    if lifecycle is not None and (phase is None or phase not in lifecycle):
        return {**result, 'status': 'excluded', 'reason': 'documented_code_lifecycle_excludes_clock'}
    if phase:
        subject = _endpoint_subject(clock.get('definition', ''),phase)
        action = _carrier_action(carrier, alpha, resolution, subject,
                                 paired_work_endpoint={'start', 'complete'} <= set(work_endpoints))
        if action:
            return {**result, 'status':'supported', 'phase':phase, 'label':endpoint_label(action, phase),
                    'reason':'documented_actual_action_endpoint'}
    action_clock = documented_action_clock(clock.get('definition',''))
    activity_evidence = resolution['status'] == 'supported' and bool(resolution.get('candidates') or resolution.get('citations'))
    if action_clock and (activity_evidence or re.search(
            r'\b(?:event|activity|transition|action|operation)\b',carrier.get('definition',''),re.I)):
        return {**result, 'status':'supported', 'label':meaning,
                'reason':'documented_physical_row_action_time'}
    return result
