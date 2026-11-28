"""Value-scoped clock evidence for records containing actual and planned messages."""

from copy import deepcopy
import re

NON_OCCURRENCE_ROLES = frozenset({
    "recorded_time", "ingestion_time", "scheduled_time", "estimated_time", "non_event_time",
})


def documented_represented_clock(text):
    """PURPOSE: Recognize a clock whose value is carried by a record or message.
    INPUT: Public clock definition. OUTPUT: True when the prose explicitly describes a represented time.
    """
    return bool(re.search(r'\b(?:time|timestamp)\b[^.;]{0,40}\b(?:represented|specified|reported|indicated)\b'
                          r'[^.;]{0,40}\b(?:message|record|event)\b', text, re.I))


def documented_message_receipt_clock(text):
    """PURPOSE: Recognize explicit receipt of a message or report as a separate action.
    INPUT: Public clock definition. OUTPUT: True when the prose directly names a receipt occurrence.
    """
    return bool(re.search(r'^\s*(?:the )?(?:(?:date and )?time (?:when |at which )?(?:the |an? )?'
                          r'(?:message|report) (?:was |is )?received|'
                          r'actual (?:message|report) receipt (?:date and )?time)\s*\.?\s*$', text, re.I))


def scoped_event_clock(binding, timestamp, carrier=None, clock=None, *, resolution=None):
    """PURPOSE: Interpret a represented message clock under an explicit code-value predicate.
    INPUT: Binding, immutable TimestampUnit, optional public carrier/clock dictionary records.
    OUTPUT: Scoped clock copy when literal actual/planned code evidence supports it; otherwise original.
    SIDE EFFECTS: Store a selector-bound evidence receipt only when deriving it from public dictionary text.
    """
    alpha = binding.get('alpha', {})
    if alpha.get('kind') != 'value':
        return timestamp
    scope = {'table': binding.get('table', binding.get('source_table')),
             'column': alpha.get('column'), 'value': alpha.get('value'),
             'timestamp_unit_id': timestamp.get('ts_id', timestamp.get('id'))}
    proof = binding.get('scoped_clock_evidence')
    if not proof and carrier is not None and clock is not None:
        resolved = resolution if resolution and resolution["status"] == "supported" else {}
        documented = carrier.get('code_meanings', {}).get(str(alpha.get('value')), '')
        meaning = str(documented or resolved.get("code_meaning", ""))
        raw = str(alpha.get("value"))
        text = str(clock.get('definition', ''))
        role = ('estimated_time' if re.search(r'\b(?:estimat(?:e|ed)|forecast|predicted)\b', meaning, re.I)
                else 'scheduled_time' if re.search(r'\b(?:planned|scheduled|expected)\b', meaning, re.I)
                else 'business_occurrence' if re.search(r'\bactual\b', meaning, re.I) else None)
        denied = (timestamp.get('role_status') == 'supported'
                  and timestamp.get('semantic_role') in NON_OCCURRENCE_ROLES)
        if not documented_represented_clock(text) or role is None or denied:
            return timestamp
        value_evidence = ([{"id": carrier['id'] + ':code:' + raw, "text": documented}] if documented else
                          [{"id": e["id"], "text": e["text"]} for e in resolved.get("evidence", [])
                           if e["id"].endswith(":" + raw)] or
                          [c["evidence"] for c in resolved.get("candidates", [])])
        if not value_evidence:
            return timestamp
        proof = {'scope': scope, 'semantic_role': role, 'evidence': [
            *value_evidence, {'id': clock['id'], 'text': text}]}
        binding['scoped_clock_evidence'] = deepcopy(proof)
    if not proof or proof.get('scope') != scope or proof.get('semantic_role') not in {
            'business_occurrence', 'scheduled_time', 'estimated_time'}:
        return timestamp
    role = proof['semantic_role']
    time_role = {'business_occurrence':'valid_time','scheduled_time':'planned_time','estimated_time':'estimated_time'}[role]
    return {**timestamp, 'semantic_role': role, 'role_status': 'supported', 'time_role':time_role,
            'row_value_scope': deepcopy(scope), 'confidence_basis': 'explicit_code_and_represented_clock',
            'role_evidence': [{'source': 'dictionary_description', 'detail': e['text'],
                               'evidence_id': e['id']} for e in proof['evidence']]}
