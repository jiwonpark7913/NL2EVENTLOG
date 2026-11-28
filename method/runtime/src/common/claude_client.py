"""Anthropic Messages transport for the pipeline's structured chat interface."""

from copy import deepcopy
import json
import hashlib
import re
import time
from types import SimpleNamespace

import httpx
from jsonschema import Draft202012Validator, ValidationError
from openai.types.chat import ChatCompletion

from src.common.llm_usage import PI_NATIVE_RETRY_BUDGET


class ClaudeChatClient:
    """Expose native Claude tool responses as locally validated chat completions."""

    def __init__(self, api_key, *, effort='medium', timeout=180, workspace=None, transport=None,
                 max_requests=200):
        """PURPOSE: Configure native Anthropic requests without exposing credentials in artifacts.
        INPUT: API key, effort level, timeout seconds, optional workspace and HTTP test transport.
        OUTPUT: SDK-shaped chat client; credentials remain only in the private HTTP client.
        """
        self.base_url = 'https://api.anthropic.com/v1/'
        self.effort = effort
        self.last_invalid_response = None
        self.requests = []
        self.max_requests = max_requests
        self._local_schemas = set()
        headers = {'x-api-key': api_key, 'anthropic-version': '2023-06-01'}
        if workspace:
            headers['anthropic-workspace-id'] = workspace
        self._http = httpx.Client(base_url=self.base_url, headers=headers,
                                  timeout=timeout, transport=transport)
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def reset_request_state(self):
        """PURPOSE: Start a comparison condition before any schema fallback.
        INPUT: Native client. OUTPUT: Request-local compatibility state reset, with usage history retained.
        """
        self._local_schemas.clear()
        self.last_invalid_response = None

    def _send(self, request, role, *, retry=False):
        """PURPOSE: Bound and account for every real HTTP request, including grammar fallbacks.
        INPUT: Native Messages body, public role name and whether the SDK call already sent an attempt. OUTPUT: Parsed provider response.
        SIDE EFFECTS: Append sanitized usage/status ledger; raises on request or budget failure.
        """
        if len(self.requests) >= self.max_requests:
            raise RuntimeError('native_model_request_budget_exhausted')
        wire = json.dumps(request, ensure_ascii=False, separators=(',', ':'))
        from src.step2_retrieve_and_interpret.execute_model_roles import _input_tokens
        estimate = _input_tokens(request['model'], [{'content': wire}], {})
        budget = PI_NATIVE_RETRY_BUDGET.get()
        if budget and retry:
            budget.reserve(estimate)
        record = {'prompt_sha256': hashlib.sha256(wire.encode()).hexdigest(),
                  'estimated_input_tokens': estimate, 'role': role, 'model': request['model'], 'effort': self.effort,
                  'schema_enforcement': 'provider_strict' if request['tools'][0].get('strict') else 'local',
                  'status': 'started'}
        self.requests.append(record)
        started = time.perf_counter()
        try:
            response = self._http.post('messages', json=request)
            response.raise_for_status()
            native = response.json()
            usage = native.get('usage', {})
            record.update(status='completed', response_model=native.get('model'),
                          input_tokens=sum(usage.get(k, 0) for k in (
                              'input_tokens', 'cache_read_input_tokens', 'cache_creation_input_tokens')),
                          output_tokens=usage.get('output_tokens', 0))
            return native
        except Exception as error:
            record.update(status='failed', error_type=type(error).__name__)
            if isinstance(error, httpx.HTTPStatusError):
                record['http_status'] = error.response.status_code
                try:
                    detail = error.response.json().get('error', {})
                    record['provider_message'] = str(detail.get('message', '')).replace(
                        self._http.headers['x-api-key'], '[REDACTED]')[:1000]
                except ValueError:
                    pass
            raise
        finally:
            record['seconds'] = round(time.perf_counter() - started, 6)

    def create(self, **options):
        """PURPOSE: Preserve role schemas and enforce them locally without compiled-grammar limits.
        INPUT: Existing model/messages/json_schema chat options and optional output-token limit.
        OUTPUT: Validated OpenAI-shaped completion with native usage; invalid/partial output raises.
        """
        specification = options['response_format']['json_schema']
        schema = specification['schema']
        role = specification['name']
        schema_key = hashlib.sha256(json.dumps(schema, sort_keys=True).encode()).hexdigest()
        systems = [message['content'] for message in options['messages']
                   if message['role'] in {'system', 'developer'}]
        systems.append(f'Return your complete structured response by calling the {role} tool '
                       'exactly once. Follow every field and constraint in its input schema.')
        messages = [deepcopy(message) for message in options['messages']
                    if message['role'] not in {'system', 'developer'}]
        request = {
            'model': options['model'],
            'max_tokens': options.get('max_completion_tokens', options.get('max_tokens', 16000)),
            'system': '\n\n'.join(systems),
            'messages': messages,
            'thinking': {'type': 'adaptive'},
            'output_config': {'effort': self.effort},
            'tools': [{'name': role, 'description': 'Return the requested structured result.',
                       'input_schema': deepcopy(schema)}],
            'tool_choice': {'type': 'auto'},
        }
        if schema_key not in self._local_schemas:
            request['tools'][0]['strict'] = True
        for attempt in range(2):
            try:
                native = self._send(request, role, retry=attempt > 0)
            except httpx.HTTPStatusError as error:
                if error.response.status_code != 400 or not request['tools'][0].get('strict'):
                    raise
                self._local_schemas.add(schema_key)
                self.requests[-1]['recovered_by'] = 'unchanged_schema_with_local_validation'
                request['tools'][0].pop('strict')
                native = self._send(request, role, retry=True)
            try:
                value = self._structured_value(native, role, schema)
                self.requests[-1]['schema_validated'] = True
                break
            except (ValueError, ValidationError) as error:
                self.requests[-1]['schema_validated'] = False
                if attempt:
                    raise
                self.requests[-1]['recovered_by'] = 'one_format_correction_request'
                request['messages'] = [*messages, {'role': 'user', 'content':
                    'The previous response failed output-format validation: ' + str(error)[:1000] +
                    '\nReturn one complete corrected response for the same task using the supplied '
                    'tool schema. Do not encode arrays or objects as JSON strings. Include every '
                    'required field. Previous response data:\n' + json.dumps(
                        self.last_invalid_response, ensure_ascii=False)}]
        usage = native.get('usage', {})
        cached = usage.get('cache_read_input_tokens', 0)
        prompt = usage.get('input_tokens', 0) + cached + usage.get('cache_creation_input_tokens', 0)
        completion = usage.get('output_tokens', 0)
        return ChatCompletion(
            id=native['id'], object='chat.completion', created=int(time.time()), model=native['model'],
            choices=[{'index': 0, 'finish_reason': 'stop', 'message': {
                'role': 'assistant', 'content': json.dumps(value, ensure_ascii=False), 'refusal': None}}],
            usage={'prompt_tokens': prompt, 'completion_tokens': completion,
                   'total_tokens': prompt + completion, 'prompt_tokens_details': {'cached_tokens': cached}},
        )

    def _structured_value(self, native, role, schema):
        """PURPOSE: Parse one native result and apply the caller's unchanged JSON Schema.
        INPUT: Provider response, expected role and original schema.
        OUTPUT: Valid JSON value; rejects partial responses, unexpected tools and invalid types.
        """
        if native.get('stop_reason') in {'max_tokens', 'refusal'}:
            raise ValueError('Claude structured response incomplete: ' + native['stop_reason'])
        blocks = native.get('content', [])
        tools = [block for block in blocks if block.get('type') == 'tool_use']
        if tools:
            if len(tools) != 1 or tools[0].get('name') != role:
                raise ValueError('Claude returned an unexpected structured response tool')
            value = tools[0]['input']
        else:
            text = ''.join(block.get('text', '') for block in blocks if block.get('type') == 'text')
            fenced = re.fullmatch(r'\s*```(?:json)?\s*\n(.*?)\n```\s*', text, flags=re.DOTALL)
            try:
                value = json.loads(fenced.group(1) if fenced else text)
            except json.JSONDecodeError:
                self.last_invalid_response = {'role': role, 'stop_reason': native.get('stop_reason'),
                                              'text': text, 'error': 'invalid_json'}
                raise
        try:
            Draft202012Validator(schema).validate(value)
        except ValidationError:
            self.last_invalid_response = {'role': role, 'stop_reason': native.get('stop_reason'),
                                          'value': value, 'error': 'schema_validation_failed'}
            raise
        return value

    def close(self):
        """PURPOSE: Release the native HTTP connection pool.
        INPUT: None. OUTPUT: Closed HTTP client; no artifact or source data writes.
        """
        self._http.close()
