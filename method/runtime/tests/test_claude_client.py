"""Offline transport checks for native Claude structured output and effort."""

import copy
import json
import unittest

import httpx
from jsonschema import ValidationError

from src.common.claude_client import ClaudeChatClient


class ClaudeClientTests(unittest.TestCase):
    """Exercise HTTP request mapping and fail-closed response validation."""

    def test_native_request_preserves_schema_and_medium_effort(self):
        """PURPOSE: Verify the actual native wire request and normalized usage without network.
        INPUT: Mock HTTP response containing thinking and one structured tool call.
        OUTPUT: Explicit adaptive/medium settings, unchanged schema and complete token accounting.
        """
        schema = {'type': 'object', 'properties': {'value': {'type': 'integer'}},
                  'required': ['value'], 'additionalProperties': False}
        original = copy.deepcopy(schema)
        requests = []

        def respond(request):
            """PURPOSE: Capture one test HTTP request and return a native Claude response.
            INPUT: httpx request. OUTPUT: In-memory response; no external I/O.
            """
            requests.append(request)
            return httpx.Response(200, json={
                'id': 'msg_test', 'model': 'claude-haiku-5-5', 'stop_reason': 'tool_use',
                'content': [{'type': 'thinking', 'thinking': 'omitted'},
                            {'type': 'tool_use', 'name': 'test_role', 'input': {'value': 7}}],
                'usage': {'input_tokens': 10, 'output_tokens': 5,
                          'cache_read_input_tokens': 3, 'cache_creation_input_tokens': 2}})

        client = ClaudeChatClient('test-key', transport=httpx.MockTransport(respond))
        self.addCleanup(client.close)
        result = client.chat.completions.create(
            model='claude-haiku-5-5', temperature=0, max_completion_tokens=100,
            messages=[{'role': 'system', 'content': 'Role instructions'},
                      {'role': 'user', 'content': 'Public input'}],
            response_format={'type': 'json_schema', 'json_schema': {
                'name': 'test_role', 'strict': True, 'schema': schema}})
        wire = json.loads(requests[0].content)
        self.assertEqual(str(requests[0].url), 'https://api.anthropic.com/v1/messages')
        self.assertEqual(requests[0].headers['x-api-key'], 'test-key')
        self.assertNotIn('authorization', requests[0].headers)
        self.assertEqual(wire['output_config'], {'effort': 'medium'})
        self.assertEqual(wire['thinking'], {'type': 'adaptive'})
        self.assertNotIn('temperature', wire)
        self.assertTrue(wire['tools'][0]['strict'])
        self.assertEqual(wire['tools'][0]['input_schema'], original)
        self.assertEqual(schema, original)
        self.assertEqual(json.loads(result.choices[0].message.content), {'value': 7})
        self.assertEqual(result.usage.prompt_tokens, 15)
        self.assertEqual(result.usage.total_tokens, 20)

    def test_large_grammar_fallback_is_counted_and_locally_validated(self):
        """PURPOSE: Recover only the known provider grammar limit without weakening output checks.
        INPUT: One HTTP 400 grammar rejection followed by a valid native tool response.
        OUTPUT: Same schema in both requests, bounded fallback and an accurate two-request ledger.
        """
        requests = []

        def respond(request):
            """PURPOSE: Simulate a grammar-limit rejection followed by one valid tool result.
            INPUT: Captured request. OUTPUT: Deterministic HTTP test response; no external I/O.
            """
            requests.append(json.loads(request.content))
            if len(requests) == 1:
                return httpx.Response(400, json={'error': {'message': 'The compiled grammar is too large'}})
            return httpx.Response(200, json={'id': 'msg_test', 'model': 'claude-haiku-5-5',
                'stop_reason': 'tool_use', 'usage': {}, 'content': [
                    {'type': 'tool_use', 'name': 'test_role', 'input': {'value': 7}}]})

        client = ClaudeChatClient('test-key', transport=httpx.MockTransport(respond))
        self.addCleanup(client.close)
        schema = {'type': 'object', 'properties': {'value': {'type': 'integer'}},
                  'required': ['value'], 'additionalProperties': False}
        result = client.chat.completions.create(model='claude-haiku-5-5',
            messages=[{'role': 'user', 'content': 'Public input'}],
            response_format={'type': 'json_schema', 'json_schema': {'name': 'test_role', 'schema': schema}})
        self.assertEqual(json.loads(result.choices[0].message.content), {'value': 7})
        self.assertEqual(len(client.requests), 2)
        self.assertTrue(requests[0]['tools'][0]['strict'])
        self.assertNotIn('strict', requests[1]['tools'][0])
        self.assertEqual(requests[0]['tools'][0]['input_schema'], requests[1]['tools'][0]['input_schema'])
        self.assertTrue(client.requests[-1]['schema_validated'])

    def test_invalid_or_truncated_outputs_are_rejected(self):
        """PURPOSE: Reject provider results that cannot satisfy the original output contract.
        INPUT: Wrong property type, unexpected tool, duplicate tools, and token-truncated replies.
        OUTPUT: Local validation errors rather than fabricated valid completions; no network.
        """
        schema = {'type': 'object', 'properties': {'value': {'type': 'integer'}},
                  'required': ['value'], 'additionalProperties': False}
        valid = {'type': 'tool_use', 'name': 'test_role', 'input': {'value': 7}}
        cases = [
            ('tool_use', [{**valid, 'input': {'value': 'wrong'}}], ValidationError),
            ('tool_use', [{**valid, 'name': 'other_role'}], ValueError),
            ('tool_use', [valid, valid], ValueError),
            ('max_tokens', [valid], ValueError),
            ('end_turn', [{'type': 'text', 'text': '```json\n{"value":"wrong"}\n```'}], ValidationError),
        ]
        for reason, content, exception in cases:
            with self.subTest(reason=reason, content=content):
                native = {'id': 'msg_test', 'model': 'claude-haiku-5-5',
                          'stop_reason': reason, 'content': content, 'usage': {}}
                transport = httpx.MockTransport(lambda request: httpx.Response(200, json=native))
                client = ClaudeChatClient('test-key', transport=transport)
                try:
                    with self.assertRaises(exception):
                        client.chat.completions.create(model='claude-haiku-5-5',
                            messages=[{'role': 'user', 'content': 'Public input'}],
                            response_format={'type': 'json_schema', 'json_schema': {
                                'name': 'test_role', 'strict': True, 'schema': schema}})
                finally:
                    client.close()

    def test_fenced_text_response_still_uses_original_schema(self):
        """PURPOSE: Read a complete JSON code block when auto tool choice returns text.
        INPUT: Native end-turn response containing one fenced JSON object.
        OUTPUT: Schema-validated completion, without modifying the returned data.
        """
        native = {'id': 'msg_test', 'model': 'claude-haiku-5-5', 'stop_reason': 'end_turn',
                  'content': [{'type': 'text', 'text': '```json\n{"value":7}\n```'}], 'usage': {}}
        client = ClaudeChatClient('test-key', transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json=native)))
        self.addCleanup(client.close)
        result = client.chat.completions.create(model='claude-haiku-5-5',
            messages=[{'role': 'user', 'content': 'Public input'}],
            response_format={'type': 'json_schema', 'json_schema': {'name': 'test_role',
                'schema': {'type': 'object', 'properties': {'value': {'type': 'integer'}},
                           'required': ['value'], 'additionalProperties': False}}})
        self.assertEqual(json.loads(result.choices[0].message.content), {'value': 7})
