"""Version-independent Pilot spend guard, based on the frozen Haiku transport policy."""

from decimal import Decimal
import fcntl
import json
from pathlib import Path
from time import perf_counter, time

import httpx

from evaluation_harness.contract import read as read_json, write as save_json

class ProvidersBlocked(RuntimeError):
    """An approved execution boundary stopped a request before transport."""


class ClaudeSpendGuard(httpx.BaseTransport):
    """Reserve worst-case dollars before each native request and persist its settled usage."""

    def __init__(self, ledger, cap, transport=None):
        """PURPOSE: Configure cumulative billing guard. INPUT: Shared ledger, USD cap, optional test transport. OUTPUT: HTTP transport."""
        self.ledger=Path(ledger)
        self.cap=Decimal(str(cap))
        self.inner=transport or httpx.HTTPTransport(retries=0)
        self.blocked=None
        self.last_provider_failure = None

    def handle_request(self, request):
        """PURPOSE: Enforce spend globally, including retries and ambiguous transport outcomes.
        INPUT: Native request. OUTPUT: Provider response or preflight failure without sending a request.
        """
        body=json.loads(request.content)
        if body.get('model')!='claude-haiku-5-5' or request.url.host!='api.anthropic.com' or request.url.path!='/v1/messages':
            raise ProvidersBlocked('Unexpected Anthropic model or path')
        # Reserve the full 1M context at the highest applicable cache-write rate and the actual output cap.
        maximum=Decimal(1)+Decimal(int(body['max_tokens']))*Decimal('2.50')/1_000_000
        self.ledger.parent.mkdir(parents=True,exist_ok=True)
        with self.ledger.with_suffix('.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            records=read_json(self.ledger) if self.ledger.exists() else []
            spent=sum(Decimal(x['reserved_or_metered_usd']) for x in records)
            if spent+maximum>self.cap:
                self.blocked='claude_budget_reservation_unavailable'
                raise ProvidersBlocked(self.blocked)
            record = {'model': body['model'], 'status': 'unsettled', 'reserved_or_metered_usd': str(maximum),
                      'role': body['tools'][0]['name'] if body.get('tools') else None, 'started_epoch_seconds': time()}
            started = perf_counter()
            records.append(record)
            save_json(self.ledger,records)
            try:
                response=self.inner.handle_request(request)
                response.read()
                record['http_status']=response.status_code
                if response.status_code != 400 and not response.is_success:
                    self.last_provider_failure = str(response.status_code)
                try:
                    data = response.json()
                except ValueError:
                    data = {}
                    if response.is_success:
                        self.last_provider_failure = 'invalid_provider_json'
                record['response_model'] = data.get('model')
                usage = data.get('usage') or {}
                if usage:
                    cash=claude_usage_usd(usage)
                    if cash>maximum:
                        raise ProvidersBlocked('Claude billing usage exceeded the frozen reservation')
                    record.update(status='metered',usage=usage,reserved_or_metered_usd=str(cash))
                elif response.status_code == 400 and (data.get('error') or {}).get('type') == 'invalid_request_error':
                    # Match the audited policy for a definite pre-inference rejection with no provider usage.
                    record.update(status='rejected_unbilled', original_reservation_usd=str(maximum),
                                  reserved_or_metered_usd='0')
            except httpx.RequestError as error:
                self.last_provider_failure = type(error).__name__
                record['transport_error'] = self.last_provider_failure
                raise
            finally:
                record['api_seconds'] = round(perf_counter() - started, 6)
                save_json(self.ledger,records)
            return response

    def close(self):
        """PURPOSE: Release HTTP resources. INPUT: Active transport. OUTPUT: Closed transport."""
        self.inner.close()


def claude_usage_usd(usage):
    """PURPOSE: Price usage conservatively under the recorded Haiku 5.5 rates.
    INPUT: Native token usage. OUTPUT: Decimal USD, with cache writes charged at the longer TTL rate.
    """
    inputs=usage.get('input_tokens',0)
    writes=usage.get('cache_creation_input_tokens',0)
    reads=usage.get('cache_read_input_tokens',0)
    outputs=usage.get('output_tokens',0)
    multiplier=5 if inputs+writes+reads>100000 else 1
    return (inputs*Decimal('.10')+writes*Decimal('.20')+reads*Decimal('.01')+outputs*Decimal('.50'))*multiplier/1_000_000


