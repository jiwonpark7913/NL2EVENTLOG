"""Three-role control and two-role candidate sharing one deterministic execution contract."""

import json
from pathlib import Path
from time import perf_counter

from jsonschema import Draft202012Validator

from development.case_catalog_m0.runtime import load_case, load_catalog
from development.scope_attribution_m0.runtime import SCOPE_PROMPT, event_payload
from development.s2.evidence import activity_aware_catalog, attach_path_reviews
from development.s2.extraction import execute_selection
from src.common.json_schema import record
from src.common.llm_usage import DEFAULT_MODEL, MeteredClient, chat_settings
from src.common.runtime_input_contract import require_no_oracle_payload, require_public_path
from src.eeg.eeg_store import EEGStore
from src.step2_retrieve_and_interpret.execute_model_roles import PIRequestBudget, SCHEMAS, _input_tokens, call_role
from src.step2_retrieve_and_interpret.serialize_role_payloads import prepare_payload, reject_output_pool_ids

JOINT_ROLE = 'joint_intent_case'
JOINT_PROMPT = Path(__file__).with_name('joint_case.md')
PATH_PROMPT = Path(__file__).with_name('path_review.md')
JOINT_SCHEMA = record(intent=SCHEMAS['minimal_intent'], case=SCHEMAS['minimal_case'])


def joint_request(question, catalog):
    """PURPOSE: Assemble the isolated S2 role in the existing compact wire format.
    INPUT: Original question and snapshot capability catalog. OUTPUT: Exact system/user/schema.
    """
    payload = {'original_request': question, 'cases': catalog}
    require_no_oracle_payload(payload)
    wire = prepare_payload(payload, 'compact')
    return {'system': JOINT_PROMPT.read_text().strip(),
            'user': '<runtime_data>\n' + wire['serialized'] + '\n</runtime_data>',
            'schema': JOINT_SCHEMA}


def choose_joint(question, catalog, client, model, audits):
    """PURPOSE: Obtain one closed Intent/Case response through the metered SDK adapter.
    INPUT: Public request, complete capability cards and metered model client. OUTPUT: Intent and Case objects.
    """
    prompt = joint_request(question, catalog)
    messages = [{'role': role, 'content': prompt[key]} for role, key in [('system', 'system'), ('user', 'user')]]
    audit = {'role': JOINT_ROLE, 'model': model, 'prompt': prompt, 'status': 'failed',
             'input_tokens': 0, 'output_tokens': 0}
    audits.append(audit)
    started = perf_counter()
    try:
        client.pi_request_budget.reserve(_input_tokens(model, messages, JOINT_SCHEMA))
        response = client.chat.completions.create(
            model=model, **chat_settings(model), max_completion_tokens=16000, messages=messages,
            response_format={'type': 'json_schema',
                             'json_schema': {'name': JOINT_ROLE, 'strict': True, 'schema': JOINT_SCHEMA}})
        usage = getattr(response, 'usage', None)
        audit.update(input_tokens=getattr(usage, 'prompt_tokens', 0),
                     output_tokens=getattr(usage, 'completion_tokens', 0))
        message = response.choices[0].message
        audit['raw_response'] = message.content
        if getattr(message, 'refusal', None):
            raise ValueError('Step 2 role refused: ' + JOINT_ROLE)
        if not isinstance(message.content, str):
            raise ValueError('Missing joint_intent_case response text')
        reply = json.loads(message.content)
        require_no_oracle_payload(reply)
        reject_output_pool_ids(reply)
        error = next(Draft202012Validator(JOINT_SCHEMA).iter_errors(reply), None)
        if error is not None:
            raise ValueError('Invalid joint_intent_case response: ' + error.message)
        audit.update(status='valid_response', parsed_response=reply)
        return reply['intent'], reply['case']
    finally:
        audit['elapsed_seconds'] = perf_counter() - started


def run(database, question, *, index, client, arm, model=DEFAULT_MODEL, checkpoint=None, replay=None):
    """PURPOSE: Execute S0 or S2 with common Event delivery, scope proof and Stage 3.
    INPUT: Public SQLite DB, original request, EEG Index and a bound model client.
    OUTPUT: Condition receipt. Optional replay accepts only exact saved S0 upstream data.
    """
    require_public_path(database)
    if not isinstance(index, EEGStore) or not question.strip() or arm not in ('S0', 'S2'):
        raise ValueError('A shared EEG index, valid arm and original request are required')
    if replay is not None and arm != 'S0':
        raise ValueError('Saved upstream checkpoints are only for S0 regression')
    metered = MeteredClient(client)
    metered.pi_request_budget = PIRequestBudget(32, 240_000)
    metered.pi_active = True
    started, calls, stages = perf_counter(), [], {}

    def record_stage(key, value):
        """PURPOSE: Capture exact public stage results. INPUT: Stage key and result. OUTPUT: Local checkpoint."""
        stages[key] = value
        if checkpoint is not None:
            checkpoint(key, value)

    with index.open(database) as lookup:
        try:
            if arm == 'S0':
                catalog, scopes = load_catalog(lookup)
            else:
                catalog = activity_aware_catalog(database, index)
                scopes = {card['id']: {entry['id'] for entry in card['scopes']} for card in catalog}
            record_stage('case_catalog', catalog)
            if replay is not None:
                intent, case = replay['intent'], replay['case']
                record_stage('intent', intent)
            elif arm == 'S2':
                intent, case = choose_joint(question, catalog, metered, model, calls)
                record_stage('intent', intent)
            else:
                intent, _ = call_role('minimal_intent', {'original_request': question}, metered, model, few_shot=False,
                                      payload_encoding='compact', audit_sink=calls)
                record_stage('intent', intent)
                case, _ = call_role('minimal_case', {'original_request': question, 'intent': intent, 'cases': catalog},
                                     metered, model, few_shot=False, payload_encoding='compact', audit_sink=calls)
            record_stage('case', case)
            target, scope = case['case_et_id'], case['case_scope_id']
            initial, projection, evidence = {**case, 'events': []}, {}, {'cases': [], 'events': []}
            if case['selection_status'] == 'selected' and target in scopes and (not scope or scope in scopes[target]):
                projection, evidence, scopes, retrieval = load_case(lookup, target)
                if replay is not None and retrieval != replay['retrieval']:
                    raise ValueError('Saved retrieval differs from the frozen Index')
                payload = event_payload(question, intent, case, evidence, scopes)
                payload = attach_path_reviews(payload, projection, target)
                record_stage('retrieval', retrieval)
                appendix = SCOPE_PROMPT.read_text().strip() + '\n\n' + PATH_PROMPT.read_text().strip()
                events, _ = call_role('minimal_events', payload, metered, model, few_shot=False,
                                      payload_encoding='compact', system_appendix=appendix, audit_sink=calls)
                initial.update(events)
                selected = {(event['event_definition_id'],event['path_id']) for event in events['events']}
                record_stage('selected_attribution', [
                    {'event_definition_id':event['id'], 'path_id':path['id'],
                     'role':path['role'], 'role_evidence':path['role_evidence']}
                    for event in payload['events'] for path in event['paths']
                    if (event['id'],path['id']) in selected])
            elif replay is not None:
                raise ValueError('Saved Case or scope is no longer selectable')
            if not projection:
                # structural_view only needs the ID/scope inventory for an early stop.
                scopes = {identifier: {key: None for key in options} for identifier, options in scopes.items()}
        except (ValueError, RuntimeError) as error:
            outcome = {'status': 'failed', 'reason': str(error), 'sql': None, 'rows': [], 'pi': None}
            return {**stages, 'initial': None, 'calls': calls, 'outcome': outcome,
                    'elapsed_seconds': perf_counter() - started}
        record_stage('initial', initial)
        outcome = execute_selection(database, lookup, projection, evidence, scopes, question, intent, initial)
        record_stage('outcome', outcome)
    return {**stages, 'calls': calls, 'elapsed_seconds': perf_counter() - started}
