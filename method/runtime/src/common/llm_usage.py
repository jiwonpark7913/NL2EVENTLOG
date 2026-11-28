"""Actual SDK request accounting, independent of semantic audit records."""

from types import SimpleNamespace
import time
from contextvars import ContextVar

PI_NATIVE_RETRY_BUDGET = ContextVar("pi_native_retry_budget", default=None)
DEFAULT_MODEL = "gpt-5-mini-2025-08-07"


def experiment_settings(model):
    """PURPOSE: Freeze the two poster models' decoding settings.
    INPUT: Requested model identifier. OUTPUT: Effective Chat Completions options.
    """
    if model in {'gpt-5-mini', DEFAULT_MODEL}:
        return {'reasoning_effort': 'medium'}
    if model in {'gpt-4o-mini', 'gpt-4o-mini-2024-07-18'}:
        return {'temperature': 0}
    return {}


def chat_settings(model):
    """PURPOSE: Select decoding options for raw SDK clients used in the pipeline.
    INPUT: Model ID. OUTPUT: Model settings; Claude uses provider defaults without temperature.
    """
    if model.startswith('claude-'):
        return {}
    return experiment_settings(model) or {'temperature': 0}


class MeteredClient:
    """SDK-compatible client with bounded requests and no prompt/credential logging."""
    def __init__(self, client, *, max_requests=200, stop_after_failure=False):
        """PURPOSE: Meter calls without changing role payloads or exposing secrets.
        INPUT: SDK client, request ceiling and optional provider failure circuit breaker.
        OUTPUT: Proxy sharing client endpoint and a public ordered usage ledger.
        """
        self.client=client
        self.base_url=getattr(client,'base_url','')
        self.max_requests=max_requests
        self.stop_after_failure=stop_after_failure
        self.failed=False
        self.requests=[]
        self.chat=SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **kwargs):
        """PURPOSE: Count each actual SDK invocation including structured-output retries.
        INPUT: Unmodified SDK arguments. OUTPUT: Original response; sanitized failure on provider error.
        Raises before calling SDK if the bounded request budget or failure circuit is reached.
        """
        if len(self.requests)>=self.max_requests:
            raise RuntimeError('model_request_budget_exhausted')
        if self.failed and self.stop_after_failure:
            raise RuntimeError('model_provider_failure_circuit_open')
        role=kwargs.get('response_format',{}).get('json_schema',{}).get('name','json_object')
        model = kwargs.get('model')
        settings = experiment_settings(model)
        if 'reasoning_effort' in settings:
            kwargs.pop('temperature', None)
            if 'max_tokens' in kwargs:
                kwargs['max_completion_tokens'] = kwargs.pop('max_tokens')
        kwargs.update(settings)
        record={'role':role,'model':model,'requested_model':model,'response_model':None,
                'settings':settings,'status':'started'}
        self.requests.append(record)
        started=time.perf_counter()
        budget = getattr(self, 'pi_request_budget', None) if getattr(self, 'pi_active', False) else None
        token = PI_NATIVE_RETRY_BUDGET.set(budget)
        try:
            response=self.client.chat.completions.create(**kwargs)
            usage=getattr(response,'usage',None)
            record.update(status='completed',response_model=getattr(response,'model',None),
                          cached_input_tokens=getattr(getattr(usage,'prompt_tokens_details',None),'cached_tokens',0) or 0,
                          reasoning_tokens=getattr(getattr(usage,'completion_tokens_details',None),'reasoning_tokens',0) or 0,
                          input_tokens=getattr(usage,'prompt_tokens',0) or 0,
                          output_tokens=getattr(usage,'completion_tokens',0) or 0)
            return response
        except Exception as error:
            self.failed=True
            record.update(status='failed',error_type=type(error).__name__)
            raise RuntimeError('model_provider_error:'+type(error).__name__) from None
        finally:
            PI_NATIVE_RETRY_BUDGET.reset(token)
            record['seconds']=round(time.perf_counter()-started,6)
