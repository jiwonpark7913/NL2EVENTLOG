"""Use the frozen provider adapters with one explicit study budget."""

from copy import deepcopy
from decimal import Decimal
import importlib.util
import json
from pathlib import Path
from time import perf_counter, time

import httpx

from evaluation_harness.contract import digest, read, write
from evaluation_harness.native_metering import ClaudeSpendGuard, ProvidersBlocked

GEMINI = 'gemini-3.5-flash-lite'
GEMINI_SOURCE = Path(__file__).with_name('gemini_transport.py')
GEMINI_SOURCE_SHA256 = 'bc5433759067a2c784946f9447ddd8c94e92eaa97dbe175ec33967cac8543bef'
HAIKU = 'claude-haiku-5-5'
SETTINGS = {
    'haiku': {'id':HAIKU,'thinking':'adaptive','effort':'medium','endpoint':'messages',
              'input_limit':1_000_000,'provider_output_limit':128_000,'pi_output_limit':16_000},
    'gemini': {'id':GEMINI,'thinking_level':'MINIMAL','temperature':0,'endpoint':'generateContent',
               'input_limit':1_048_576,'provider_output_limit':65_536,'pi_output_limit':16_000,
               'local_rpm':10,'http_attempt_limit':240,'rolling_wire_plus_output_limit':250_000},
}


def entries(path):
    """PURPOSE: Read an append-only provider ledger. INPUT: JSON path. OUTPUT: Ordered attempts."""
    return read(path) if path.exists() else []


def reserved(path):
    """PURPOSE: Count unsettled exposure along with settled usage. INPUT: Ledger. OUTPUT: Decimal USD ceiling."""
    return sum((Decimal(r['reserved_or_metered_usd']) for r in entries(path)),Decimal(0))


class GeminiSpendGuard(httpx.BaseTransport):
    """Charge the conservative paid tariff unless free billing was explicitly verified for this scope."""

    def __init__(self, ledger, total, claude_ledger, billing, inner=None):
        """PURPOSE: Bind Gemini transport and total cap. INPUT: Local ledgers, USD and verified billing mode. OUTPUT: Guard."""
        self.ledger, self.total, self.claude_ledger = ledger, Decimal(total), claude_ledger
        self.billing = billing
        self.inner = inner if inner is not None else httpx.HTTPTransport(retries=0)
        self.blocked = None
        self.role = None
        self.observe = None

    def handle_request(self, request):
        """PURPOSE: Reserve a conservative native charge before transmission.
        INPUT: Approved Gemini native request. OUTPUT: Native response and durable normalized receipt.
        """
        if (request.url.scheme,request.url.host,request.url.path)!=(
                'https','generativelanguage.googleapis.com',f'/v1beta/models/{GEMINI}:generateContent'):
            raise ProvidersBlocked('Unexpected Gemini endpoint')
        body = json.loads(request.content)
        options = body.get('generationConfig') or {}
        if (request.method!='POST' or body.keys()-{'contents','systemInstruction','generationConfig'}
                or options.get('candidateCount')!=1 or not 0 < options.get('maxOutputTokens',0) <= 16_000
                or options.get('thinkingConfig')!={'thinkingLevel':'MINIMAL'}):
            raise ProvidersBlocked('Unexpected Gemini paid request shape')
        at_paid_rate = self.billing != 'verified_free_only'
        maximum = (Decimal('0.30')*1_048_576+Decimal('2.50')*131_072)/1_000_000 if at_paid_rate else Decimal(0)
        current = entries(self.ledger)
        if reserved(self.ledger)+reserved(self.claude_ledger)+maximum>self.total:
            self.blocked='combined_budget_reservation_unavailable'
            raise ProvidersBlocked(self.blocked)
        record = {'model':GEMINI,'role':self.role,'status':'unsettled','billing_mode':self.billing,
                  'reserved_or_metered_usd':str(maximum),'started_epoch_seconds':time()}
        current.append(record)
        write(self.ledger,current)
        started=perf_counter()
        try:
            response=self.inner.handle_request(request)
            response.read()
            record['http_status']=response.status_code
            try:
                payload=response.json()
            except ValueError:
                payload={}
            if payload.get('usageMetadata'):
                usage=payload['usageMetadata']
                raw=usage.get('promptTokenCount',0)
                cached=usage.get('cachedContentTokenCount',0)
                out=usage.get('candidatesTokenCount',0)+usage.get('thoughtsTokenCount',0)
                paid=(Decimal(raw)*Decimal('.30')+Decimal(out)*Decimal('2.50'))/1_000_000
                if at_paid_rate and paid>maximum:
                    self.blocked='gemini_usage_above_reserved_bound'
                    raise ProvidersBlocked(self.blocked)
                record.update(status='metered',response_model=payload.get('modelVersion'),
                              stop_reason=next(iter(payload.get('candidates',[])),{}).get('finishReason'),
                              usage={'input_tokens':raw-cached,'cache_read_input_tokens':cached,'output_tokens':out},
                              reserved_or_metered_usd=str(paid if at_paid_rate else Decimal(0)),
                              paid_list_equivalent_usd=str(paid))
            elif response.status_code==400 and (payload.get('error') or {}).get('status')=='INVALID_ARGUMENT':
                record.update(status='rejected_unbilled',reserved_or_metered_usd='0')
            if self.observe is not None:
                self.observe(self.role, payload, {'http_status':response.status_code})
            return response
        except httpx.RequestError as error:
            record['transport_error']=type(error).__name__
            raise
        finally:
            record['api_seconds']=round(perf_counter()-started,6)
            write(self.ledger,current)

    def close(self):
        """PURPOSE: Close the underlying connection. INPUT: Self. OUTPUT: Closed HTTP transport."""
        self.inner.close()


def gemini_client(key, guard):
    """PURPOSE: Reuse the archived native Gemini adapter with a study-bound HTTP transport.
    INPUT: API key and approved native transport. OUTPUT: Same SDK-shaped PI interface as Haiku.
    """
    if digest(GEMINI_SOURCE) != GEMINI_SOURCE_SHA256:
        raise ValueError('The released Gemini adapter differs from its measured source')
    spec=importlib.util.spec_from_file_location('frozen_gemini_transport',GEMINI_SOURCE)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    class Client(module.GeminiClient):
        """Configure only native reasoning, output limits, logging and retry accounting."""

        def create(self, **options):
            """PURPOSE: Check native completeness before shared JSON validation. INPUT: PI role call. OUTPUT: Parsed reply."""
            self._native_attempts_in_call=0
            result=super().create(**options)
            if result.choices[0].finish_reason!='stop':
                raise module.GeminiError('generation_truncated')
            return result

        def _post(self, body, role, model, schema_used):
            """PURPOSE: Freeze provider settings across the same PI roles and account for native retries.
            INPUT: Gemini adapter body. OUTPUT: Native response and audit.
            """
            from src.common.llm_usage import PI_NATIVE_RETRY_BUDGET
            from src.step2_retrieve_and_interpret.execute_model_roles import _input_tokens
            native=deepcopy(body)
            native['generationConfig'].update(maxOutputTokens=16_000,thinkingConfig={'thinkingLevel':'MINIMAL'})
            budget=PI_NATIVE_RETRY_BUDGET.get()
            if self._native_attempts_in_call and budget:
                wire=json.dumps(native,ensure_ascii=False)
                budget.reserve(_input_tokens(model,[{'content':wire}],{}))
            self._native_attempts_in_call+=1
            guard.role=role
            return super()._post(native,role,model,schema_used)

        def reset_request_state(self):
            """PURPOSE: Start an independent request group. INPUT: Self. OUTPUT: Retry counter reset."""
            self._native_attempts_in_call=0

        def close(self):
            """PURPOSE: Close the active connection. INPUT: Self. OUTPUT: Released transport."""
            self.http.close()

    attempts_used=len(entries(guard.ledger))
    client=Client(key,lambda _:None,interval=6,tokens_per_minute=250_000,
                  max_attempts=max(0,240-attempts_used),retry_attempts=2)
    client.http.close()
    client.http=httpx.Client(headers={'x-goog-api-key':key},timeout=180,
                            follow_redirects=False,transport=guard)
    return client


def haiku_guard(ledger, other_ledger, cap):
    """PURPOSE: Reserve the remaining study envelope for the next serialized Haiku group.
    INPUT: Haiku and Gemini ledgers and shared cap. OUTPUT: Existing Haiku guard with a safe cumulative cap.
    """
    return ClaudeSpendGuard(ledger,Decimal(cap)-reserved(other_ledger))
