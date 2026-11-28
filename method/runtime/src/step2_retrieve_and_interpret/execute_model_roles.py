"""Versioned, independently validated Step 2 model roles."""

from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
from src.common.prompt_loader import load_prompt
import time
from jsonschema import Draft202012Validator
from src.common.runtime_input_contract import POLICY_VERSION, require_no_oracle_payload
from src.step2_retrieve_and_interpret.serialize_role_payloads import prepare_payload, reject_output_pool_ids, validate_quoted_evidence, VERSION as WIRE_VERSION
VERSION = 'step2-independent-eeg-crosscheck-v5'
EXAMPLE_VERSION = 'step2-illustrative-v1'
PROMPT_FILES = {'pi_cases': 'select_case_notion', 'pi_events': 'select_event_definitions', 'pi_focus': 'classify_process_focus', 'pi_crosscheck': 'verify_process_information', 'pi_revise': 'revise_process_information', 'semantic_decomposer': 'parse_process_request', 'interpretation_comparator': 'compare_process_interpretations'}
PROMPT_FILES.update(pi_revise_requirement='revise_activity_requirements',
                    pi_unified='interpret_unified', pi_unified_revision='revise_unified_interpretation')
PROMPT_FILES.update(minimal_intent='minimal_intent', minimal_case='minimal_case',
                    minimal_events='minimal_events', minimal_review='minimal_review')
ROLE_VERSIONS = {'semantic_decomposer': 'literal-evidence-v2', 'pi_crosscheck': 'selection-accountability-v1',
                 'pi_revise_requirement': 'grounded-requirement-edit-v1'}
INDEPENDENT_SELECTOR_PROMPTS = {'pi_cases': 'select_case_from_request', 'pi_events': 'select_events_from_request'}
QUOTATION_EXEMPT_ROLES = {'minimal_intent', 'minimal_case', 'minimal_events', 'minimal_review'}
from src.common.llm_usage import chat_settings
from src.common.json_schema import record


def array(items):
    """PURPOSE: Define an array schema. INPUT: Item schema. OUTPUT: Array schema."""
    return {'type': 'array', 'items': items}


def choice(values):
    """PURPOSE: Restrict enum values. INPUT: Allowed strings. OUTPUT: String schema."""
    return {'type': 'string', 'enum': list(values)}


TEXT = {'type': 'string'}
IDS = array(TEXT)
SCOPE = choice(['own', 'desc', 'unresolved', 'attributable_history', 'process_focus'])
ACTIVITY_SCOPE = choice(['explicit', 'implicit'])
GRANULARITY = choice(['coarse', 'distinct'])
COVERAGE = choice(['one', 'all'])
ACTIVITY_REQUIREMENT = dict(span=TEXT, meaning=TEXT, qualifiers=IDS, coverage=COVERAGE, granularity=GRANULARITY)
EXCLUSION_REASONS = ('different_occurrence', 'wrong_phase', 'wrong_role', 'duplicate_occurrence')
FOCUS = {'anyOf':[record(span=TEXT,meaning=TEXT),{'type':'null'}]}
SCHEMAS = {'interpretation_comparator': record(decision=choice(['select', 'abstain']), target_ot_id=TEXT, selected_candidate_ids=IDS, reason_kind=choice(['supported_interpretation', 'request_ambiguity', 'missing_evidence']), reason=TEXT), 'semantic_decomposer': record(activity_scope=ACTIVITY_SCOPE, process_focus=FOCUS, case_requirement=record(span=TEXT, meaning=TEXT), scope_requirement=record(span=TEXT, object_scope=SCOPE, granularity=GRANULARITY), activity_requirements=array(record(id=TEXT, **ACTIVITY_REQUIREMENT)))}
PI_CASE = dict(et=TEXT, mode=ACTIVITY_SCOPE, focus=TEXT)
PI_TYPES = ['case_mismatch','mode_mismatch','unrequested','unmatched','focus_conflict','uncertain']
REQUIREMENT_MATCH = record(requirement_id=TEXT, event_definition_ids=IDS)
REQUIREMENT_REVIEW = record(requirement_id=TEXT, event_definition_ids=IDS,
    reviewed_coverage=choice(['one','all']), reviewed_granularity=GRANULARITY,
    semantic_status=choice(['matched', 'missing', 'time_mismatch', 'ambiguous']),
    source_attribution_gap={'type': 'boolean'}, reason=TEXT)
SCHEMAS.update(
    pi_cases=record(candidates=array(record(**PI_CASE))),
    pi_events=record(matches=array(REQUIREMENT_MATCH)),
    pi_focus=record(decisions=array(record(id=TEXT, decision=choice(['INCLUDE','EXCLUDE','UNCERTAIN'])))),
    pi_crosscheck=record(differences=array(record(kind=choice(PI_TYPES),target=TEXT,reason=TEXT))),
    pi_revise_requirement=record(edits=array(record(requirement_id=TEXT, **ACTIVITY_REQUIREMENT,
                                                     event_definition_ids=IDS))),
    pi_revise=record(action=choice(['keep','change','abstain']), **PI_CASE, ids=IDS,
        resolutions=array(record(kind=choice(PI_TYPES),target=TEXT,span=TEXT,reason=TEXT))))
UNIFIED_SCHEMA = record(
    case_et_id=TEXT, case_span=TEXT, case_scope_id=TEXT,
    request_mode=choice(('explicit', 'implicit')), process_focus=TEXT,
    object_scope=choice(('own', 'attributable_history', 'process_focus', 'unresolved')),
    selections=array(record(span=TEXT, activities=array(record(activity_id=TEXT, role=TEXT)))),
    unresolved_requirements=array(TEXT),
)
SCHEMAS.update(pi_unified=UNIFIED_SCHEMA, pi_unified_revision=UNIFIED_SCHEMA)
MINIMAL_SELECTION = choice(('selected', 'insufficient_evidence'))
MINIMAL_CASE_FIELDS = dict(selection_status=MINIMAL_SELECTION, case_et_id=TEXT, case_scope_id=TEXT, reason=TEXT)
MINIMAL_EVENTS = array(record(event_definition_id=TEXT, path_id=TEXT))
SCHEMAS.update(
    minimal_intent=record(objective=TEXT, case_intent=TEXT, activity_intent=TEXT, activity_mode=ACTIVITY_SCOPE),
    minimal_case=record(**MINIMAL_CASE_FIELDS),
    minimal_events=record(selection_status=MINIMAL_SELECTION, events=MINIMAL_EVENTS, reason=TEXT),
    minimal_review=record(**MINIMAL_CASE_FIELDS, events=MINIMAL_EVENTS),
)

CONTEXT_LIMITS = {'gpt-4o-mini': 128000, 'gpt-4o': 128000}


class Step2ContextLimitExceeded(RuntimeError):
    """A request too large for the model's context window; never sent and not a semantic-selection failure."""


class PIRequestBudget:
    """Bound all actual PI calls across initial selection, expansion and recovery."""

    def __init__(self, max_calls, max_input_tokens):
        """PURPOSE: Initialize per-request limits. INPUT: Positive call and estimated input budgets.
        OUTPUT: Independent accounting state for a single request.
        """
        if min(max_calls, max_input_tokens) < 1:
            raise ValueError('invalid_pi_request_budget')
        self.max_calls = max_calls
        self.max_input_tokens = max_input_tokens
        self.max_lookups = min(12, max_calls)
        self.lookups = 0
        self.calls = 0
        self.estimated_input_tokens = 0
        self.exhausted = None

    def reserve(self, tokens):
        """PURPOSE: Reserve an SDK call before transmission. INPUT: Estimated wire input tokens.
        OUTPUT: None, or a typed unresolved diagnostic before any provider invocation.
        """
        if tokens is None:
            self.exhausted = 'pi_token_estimator_unavailable'
        elif self.calls >= self.max_calls:
            self.exhausted = 'pi_call_budget_exhausted'
        elif self.estimated_input_tokens + tokens > self.max_input_tokens:
            self.exhausted = 'pi_input_token_budget_exhausted'
        if self.exhausted:
            raise ValueError(self.exhausted)
        self.calls += 1
        self.estimated_input_tokens += tokens

    def reserve_lookup(self):
        """PURPOSE: Charge one additional PI lookup under this request's limits.
        INPUT: None. OUTPUT: None, or a diagnostic when another lookup is unavailable.
        """
        if not self.exhausted and self.lookups >= self.max_lookups:
            self.exhausted = 'pi_lookup_budget_exhausted'
        if self.exhausted:
            raise ValueError(self.exhausted)
        self.lookups += 1

    def allow_lookup(self):
        """PURPOSE: Guard optional lookups while retaining the terminal diagnostic.
        INPUT: None. OUTPUT: True after reserving one lookup, false on exhaustion.
        """
        try:
            self.reserve_lookup()
        except ValueError:
            return False
        return True


def _input_tokens(model, messages, schema):
    """PURPOSE: Count request input tokens (messages + structured-output schema) before sending.
    INPUT: Model, chat messages and schema. OUTPUT: Token count, or None without a tokenizer for the model.
    shortcut: o200k_base text count; the provider adds a few framing tokens per message.
    """
    try:
        import tiktoken
        encoding = tiktoken.get_encoding('o200k_base')
    except Exception:
        return None
    text = ''.join(m['content'] for m in messages) + json.dumps(schema)
    return len(encoding.encode(text)) + 4 * len(messages)


def _record(kind, role, audit, value):
    """PURPOSE: Persist one Step 2 request or raw response before any validation, when NL2EL_STEP2_RECORD_DIR is set.
    INPUT: 'request'|'response', role, call audit (cache key/sequence) and JSON value. OUTPUT: File path or None.
    """
    directory = os.environ.get('NL2EL_STEP2_RECORD_DIR')
    if not directory:
        return None
    folder = Path(directory); folder.mkdir(parents=True, exist_ok=True)
    if 'record_sequence' not in audit:
        audit['record_sequence'] = len(list(folder.glob('*_request.json'))) + 1
    path = folder / f"{audit['record_sequence']:03d}_{role}_{kind}.json"
    path.write_text(json.dumps(value, ensure_ascii=False, indent=1, default=str) + '\n')
    audit[kind + '_record'] = str(path)
    return path


def constrained_role_schema(role, payload):
    """PURPOSE: Constrain replies to this request. INPUT: Role and public evidence. OUTPUT: Closed schema."""
    import copy
    schema = copy.deepcopy(SCHEMAS[role])
    fields = schema['properties']
    def enum(values):
        """PURPOSE: Encode a finite vocabulary. INPUT: Allowed strings. OUTPUT: Provider string schema."""
        return choice(sorted(set(values)))
    if role=='pi_cases':
        choices = fields['candidates']
        choices['maxItems'] = payload['max_candidates']
        candidate = choices['items']
        candidate['properties']['et'] = enum(e['id'] for e in payload['entity_types'])
        if payload.get('initial_choice_only'):
            candidate['properties']['object_scope'] = choice(['own', 'attributable_history', 'process_focus', 'unresolved'])
            candidate['required'].append('object_scope')
        if payload.get('case_scopes'):
            candidate['properties']['scope_id'] = enum(['', *[s['id'] for s in payload['case_scopes']]])
            candidate['required'].append('scope_id')
    if role=='pi_events':
        ids = [a['id'] for a in payload['activities']]
        if payload.get('initial_choice_only'):
            # Offered IDs are checked locally. Repeating enum combinations for ED and path
            # IDs makes the provider grammar needlessly complex.
            return record(selected_events=array(record(event_definition_id=TEXT, path_id=TEXT)))
        match = fields['matches']['items']['properties']
        match['requirement_id'] = enum(r['id'] for r in payload['activity_requirements'])
        if ids: match['event_definition_ids']['items'] = enum(ids)
        else: fields['matches']['maxItems'] = 0
    if role=='pi_focus':
        fields['decisions']['items']['properties']['id'] = enum(a['id'] for a in payload['activities'])
    if role=='pi_crosscheck':
        state = payload['selection']
        parsed = payload['request_interpretation']
        if 'complete_tier1_inventory' in payload:
            fields['absent_from_tier1'] = array(TEXT)
            schema['required'].append('absent_from_tier1')
        if payload.get('case_scope_options'):
            fields['required_case_scope_id'] = enum(['', *[c['id'] for c in payload['case_scope_options']]])
            schema['required'].append('required_case_scope_id')
        if payload.get('implicit_role_review'):
            ids = [card['id'] for card in payload['implicit_role_review']]
            fields['implicit_role_reviews'] = array(record(
                event_definition_id=enum(ids), path_ids=array(TEXT), span=TEXT, reason=TEXT))
            schema['required'].append('implicit_role_reviews')
        if payload.get('implicit_pair_review'):
            ids = [card['id'] for card in payload['implicit_pair_review']]
            fields['implicit_pair_reviews'] = array(record(
                pair_id=enum(ids), decision=choice(['distinct', 'unresolved']), reason=TEXT,
                evidence=array(record(event_definition_id=TEXT, quote=TEXT))))
            schema['required'].append('implicit_pair_reviews')
        activity_review = payload.get('activity_review')
        if activity_review is not None:
            requirements = activity_review['requirements']
            reviews = fields['requirement_reviews'] = array(copy.deepcopy(REQUIREMENT_REVIEW))
            schema['required'].append('requirement_reviews')
            if not requirements:
                reviews['maxItems'] = 0
            else:
                review = reviews['items']['properties']
                review['requirement_id'] = enum(r['id'] for r in requirements)
                if activity_review.get('scope_verification'):
                    review['candidate_decisions'] = array(record(
                        event_definition_id=TEXT, decision=choice(('include', 'exclude', 'unresolved')),
                        span=TEXT, quote=TEXT))
                    reviews['items']['required'].append('candidate_decisions')
                ids = [a['id'] for a in activity_review['candidates']]
                if ids: review['event_definition_ids']['items'] = enum(ids)
                else: review['event_definition_ids']['maxItems'] = 0
                proposed_ids = {identifier for item in activity_review.get('initial_proposals', [])
                                for identifier in item['event_definition_ids']}
                proposed_ids.update(identifier for values in activity_review.get('revised_proposals', {}).values()
                                    for identifier in values)
                independent_ids = activity_review.get('independent_proposal_ids', [])
                if independent_ids:
                    review['aligned_proposal_ids'] = array(TEXT)
                    reviews['items']['required'].append('aligned_proposal_ids')
                    proposed_ids.update(independent_ids)
                if proposed_ids:
                    review['exclusions'] = array(record(event_definition_id=enum(proposed_ids),
                                                        kind=choice(EXCLUSION_REASONS), span=TEXT, reason=TEXT))
                    reviews['items']['required'].append('exclusions')
                projections = [(a['id'], p['path_id']) for a in activity_review['candidates']
                               for p in a.get('role_projections', [])]
                if projections:
                    review['role_path_choices'] = array(record(
                        event_definition_id=enum(e for e, _ in projections),
                        path_id=enum(p for _, p in projections)))
                    reviews['items']['required'].append('role_path_choices')
        targets = {'case_mismatch':[state['et']]}
        if state['mode']!=parsed['activity_scope']: targets['mode_mismatch']=[state['et']]
        if state['mode']=='explicit' and activity_review is None:
            targets.update(unrequested=state['ids'],unmatched=[a['span'] for a in parsed['activity_requirements']])
        if state['mode']=='implicit' and state['classifications']:
            targets.update(focus_conflict=list(state['classifications']) or [state['et']],
                           uncertain=[i for i,d in state['classifications'].items() if d=='UNCERTAIN'])
        fields['differences']['items'] = {'anyOf':[record(kind=choice([kind]),target=enum(values),reason=TEXT)
                                                  for kind,values in targets.items() if values]}
        if payload.get('case_is_locked'):
            fields['differences']['maxItems'] = 0
    if role == 'pi_revise_requirement':
        edits = fields['edits']
        items = edits['items']['properties']
        edits['maxItems'] = len(payload['unresolved_requirements'])
        items['requirement_id'] = enum(r['id'] for r in payload['unresolved_requirements'])
        ids = [card['id'] for card in payload['activities']]
        if ids:
            items['event_definition_ids'] = array(enum(ids))
        else:
            edits['maxItems'] = 0
    if role=='pi_revise':
        import re
        words = payload['original_request'].split()
        spans = {'', *( ' '.join(words[i:j]) for i in range(len(words)) for j in range(i+1,len(words)+1))}
        if len(spans)<=250: fields['focus']=enum(spans | {payload['selection']['focus']})
        paragraph = payload['eeg_summary']
        fields['et'] = enum(re.findall(r'\bET\d+\b',paragraph))
        acts = set(re.findall(r'\bA\d+\b',paragraph)) | set(payload['selection']['ids'])
        if acts: fields['ids']['items'] = enum(acts)
        else: fields['ids']['maxItems'] = 0
    return schema


def call_role(role, payload, client, model, cache=None, *, few_shot=True, audit_sink=None, payload_encoding=None,
              schema=None, defer_cache_write=False, system_appendix=''):
    """PURPOSE: Call one isolated role with versioned prompts and validate even cached responses.
    INPUT: Public runtime payload, SDK client, model/cache, example toggle and an optional request-specific
           output schema replacing the role's generic one. With deferred writes, the caller publishes
           only after its additional role-specific checks pass.
    OUTPUT: Parsed response and call telemetry; optional sink retains failures too.
    """
    independent_role = payload.get('initial_choice_only') and role in INDEPENDENT_SELECTOR_PROMPTS
    name = INDEPENDENT_SELECTOR_PROMPTS[role] if independent_role else PROMPT_FILES[role]
    prompt = load_prompt('step2_retrieve_and_interpret', name)
    role_version = 'independent-initial-choice-v2' if independent_role else ROLE_VERSIONS.get(role)
    require_no_oracle_payload(payload)
    instructions, examples = prompt.split('\n<!-- examples -->\n', 1)
    system = instructions + (examples if few_shot else '')
    if system_appendix:
        system += '\n' + system_appendix
    if role == 'pi_crosscheck' and (payload.get('implicit_role_review') or payload.get('implicit_pair_review')):
        system += '\n' + load_prompt('step2_retrieve_and_interpret', 'verify_implicit_attribution_roles')
    if role == 'pi_crosscheck' and payload.get('activity_review', {}).get('independent_proposal_ids'):
        system += '\n' + load_prompt('step2_retrieve_and_interpret', 'align_independent_selection')
    if role == 'pi_crosscheck' and 'complete_tier1_inventory' in payload:
        system += (load_prompt('step2_retrieve_and_interpret', 'check_missing_activity_inventory'))
    if role in ('pi_events', 'pi_crosscheck', 'pi_focus') and payload.get('event_families'):
        system += load_prompt('step2_retrieve_and_interpret', 'carrier_event_selection')
    schema = schema if schema is not None else SCHEMAS[role]
    transport = prepare_payload(payload, payload_encoding or os.environ.get('NL2EL_STEP2_PAYLOAD_ENCODING', 'compact'))
    system += transport['system_suffix']
    if role.startswith('pi_') and payload.get('original_request'):
        system += load_prompt('step2_retrieve_and_interpret', 'quote_analyst_request').format(request=json.dumps(payload['original_request'], ensure_ascii=False))
    serialized = transport['serialized']
    identity = [POLICY_VERSION, VERSION, EXAMPLE_VERSION, model, system,
                schema, payload, WIRE_VERSION, transport['requested_encoding'], serialized]
    if role_version:
        identity.append(role_version)
    digest = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    key = VERSION + ':' + digest
    audit = {'role': role, 'model': model,
             'prompt_version': VERSION + ':' + role + (':' + role_version if role_version else ''),
             'example_set_version': EXAMPLE_VERSION if few_shot else 'disabled',
             'cache_key': key, 'cache_hit': cache is not None and key in cache,
             'input_tokens': 0, 'output_tokens': 0, 'total_tokens': 0,
             'elapsed_seconds': 0.0, 'payload_bytes': len(serialized.encode()),
             'payload_transport': {k: v for k, v in transport.items() if k not in {'serialized', 'wire', 'system_suffix'}},
             'cached_input_tokens': None}
    audit['prompt'] = {'system':system,'user':'<runtime_data>\n'+serialized+'\n</runtime_data>','schema':schema}
    started = time.perf_counter()
    if audit_sink is not None:
        audit_sink.append(audit)
    try:
        if audit['cache_hit']:
            value = json.loads(json.dumps(cache[key]))
        else:
            messages = [{'role': 'system', 'content': system}, {'role': 'user',
                         'content': '<runtime_data>\n' + serialized + '\n</runtime_data>'}]
            limit = CONTEXT_LIMITS.get(model)
            budget = getattr(client, 'pi_request_budget', None)
            estimate = _input_tokens(model, messages, schema) if limit or budget else None
            audit['context_precheck'] = ({'limit': limit, 'estimated_input_tokens': estimate}
                                         if limit and estimate is not None else 'not_configured')
            _record('request', role, audit, {'role': role, 'model': model, 'cache_key': key,
                    'context_precheck': audit['context_precheck'], 'messages': messages, 'schema': schema,
                    'payload_transport': audit['payload_transport']})
            if limit and estimate is not None and estimate > limit:
                audit['status_detail'] = 'context_limit_exceeded_not_sent'
                raise Step2ContextLimitExceeded(f'{role}: {estimate} input tokens > {model} limit {limit}')
            if budget:
                budget.reserve(estimate)
            response = client.chat.completions.create(
                model=model, **chat_settings(model), max_completion_tokens=16000,
                response_format={'type': 'json_schema', 'json_schema': {
                    'name': role, 'strict': True, 'schema': schema}},
                messages=messages)
            _record('response', role, audit, response.model_dump(mode='json') if hasattr(response, 'model_dump')
                    else {'content': response.choices[0].message.content})
            usage = getattr(response, 'usage', None)
            audit.update(input_tokens=getattr(usage, 'prompt_tokens', 0),
                         output_tokens=getattr(usage, 'completion_tokens', 0),
                         total_tokens=getattr(usage, 'total_tokens', 0))
            details = getattr(usage, 'prompt_tokens_details', None)
            audit['cached_input_tokens'] = (details.get('cached_tokens') if isinstance(details, dict)
                else getattr(details, 'cached_tokens', None))
            message = response.choices[0].message
            audit['raw_response'] = message.content
            if getattr(message, 'refusal', None):
                raise ValueError('Step 2 role refused: ' + role)
            content = message.content
            if role in {'pi_unified', 'pi_unified_revision'}:
                stripped = content.strip()
                lines = stripped.splitlines()
                if len(lines) >= 3 and lines[0] in {'```json', '```'} and lines[-1] == '```':
                    content = '\n'.join(lines[1:-1])
                    audit['format_recovery'] = 'single_json_code_fence'
            value = json.loads(content)
        audit['parsed_response'] = value
        errors = sorted(Draft202012Validator(schema).iter_errors(value), key=lambda e: str(e.path))
        require_no_oracle_payload(value)
        reject_output_pool_ids(value)
        if role not in QUOTATION_EXEMPT_ROLES:
            validate_quoted_evidence(value, payload)
        if errors:
            if role == 'pi_revise':
                audit['invalid_response'] = value
            raise ValueError('Invalid ' + role + ' response: ' + errors[0].message)
        if cache is not None and not defer_cache_write:
            cache[key] = json.loads(json.dumps(value))
        audit['status'] = 'valid_response'
        return value, audit
    except Exception as exc:
        audit.update(status='failed', error_type=type(exc).__name__, rejection=str(exc))
        raise
    finally:
        audit['elapsed_seconds'] = time.perf_counter() - started
