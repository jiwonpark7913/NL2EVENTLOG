"""Native Gemini adapter for the isolated, free-tier NL2EventLog benchmark."""

from collections import deque
from itertools import chain
import json
from threading import BoundedSemaphore, Lock
from time import monotonic, sleep
from types import SimpleNamespace

import httpx

MODEL = "gemini-3.5-flash-lite"
BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
SCHEMA_KEYWORDS = frozenset({"type", "format", "title", "description", "enum", "properties",
                            "required", "items", "prefixItems", "minItems", "maxItems", "minimum",
                            "maximum", "anyOf", "oneOf", "additionalProperties"})


class GeminiError(RuntimeError):
    """Report a sanitized Gemini provider failure without a credential-bearing URL."""


def translate_schema(schema):
    """PURPOSE: Send Gemini's documented JSON Schema subset, leaving strict local validation intact.
    INPUT: Pipeline output schema. OUTPUT: Provider subset with unchanged field names and enum values.
    """
    output = {}
    for key, value in schema.items():
        if key not in SCHEMA_KEYWORDS:
            continue
        if key == "properties":
            output[key] = {name: translate_schema(field) for name, field in value.items()}
        elif key in {"items", "additionalProperties"} and isinstance(value, dict):
            output[key] = translate_schema(value)
        elif key in {"anyOf", "oneOf", "prefixItems"}:
            output[key] = [translate_schema(field) for field in value]
        else:
            output[key] = value
    return output


class GeminiClient:
    """Present one locked model and bounded request policy through the pipeline SDK surface."""

    def __init__(self, key, on_attempt, *, interval=1.4, max_attempts=170,
                 tokens_per_minute=None, max_concurrency=1, retry_attempts=3, backoff_base=2,
                 backoff_cap=60, on_start=None, recent_reservations=()):
        """PURPOSE: Create a shared Gemini connection and request governor.
        INPUT: Previously used free-tier API key and audit sink. OUTPUT: Chat Completions-style client.
        """
        self.base_url = BASE_URL
        self.http = httpx.Client(headers={"x-goog-api-key": key}, timeout=90, follow_redirects=False,
                                 transport=httpx.HTTPTransport(retries=0))
        self.chat = SimpleNamespace(completions=self)
        self.on_attempt = on_attempt
        self.on_start = on_start
        self.interval, self.max_attempts = interval, max_attempts
        self.lock, self.next_send, self.attempts = Lock(), 0.0, 0
        self.blocked = None
        self.last_provider_failure = None
        self.inflight = BoundedSemaphore(max_concurrency)
        self.tokens_per_minute = tokens_per_minute
        now = monotonic()
        self.token_window = deque((now - age, tokens) for age, tokens in recent_reservations)
        if recent_reservations:
            self.next_send = now - recent_reservations[-1][0] + interval
        self.token_lock = Lock()
        self.retry_attempts, self.backoff_base, self.backoff_cap = retry_attempts, backoff_base, backoff_cap

    def _reserve_tokens(self, body):
        """PURPOSE: Bound rolling-minute text-token demand conservatively.
        INPUT: Native JSON payload. OUTPUT: Reservation, or an error before transmission.
        """
        tokens = len(json.dumps(body, ensure_ascii=False).encode()) + body['generationConfig']['maxOutputTokens']
        if self.tokens_per_minute is None:
            return tokens
        if tokens>self.tokens_per_minute:
            self.blocked='configured_tpm_too_low_for_request'
            raise GeminiError(self.blocked)
        while True:
            with self.token_lock:
                now=monotonic()
                while self.token_window and self.token_window[0][0]<=now-60:
                    self.token_window.popleft()
                if sum(amount for _,amount in self.token_window)+tokens<=self.tokens_per_minute:
                    self.token_window.append((now,tokens))
                    return tokens
                delay = max(.01, 60 + self.token_window[0][0] - now)
            sleep(delay)

    def _slot(self):
        """PURPOSE: Rate-limit and bound provider invocations. INPUT: Current client state. OUTPUT: Attempt number."""
        with self.lock:
            if self.blocked:
                raise GeminiError(self.blocked)
            if self.attempts >= self.max_attempts:
                self.blocked = "free_tier_daily_attempt_cap"
                raise GeminiError(self.blocked)
            sleep(max(0.0, self.next_send - monotonic()))
            self.next_send = monotonic() + self.interval
            self.attempts += 1
            return self.attempts

    def _post(self, body, role, model, schema_used):
        """PURPOSE: Deliver one native request and record transport and usage metadata.
        INPUT: JSON request and role. OUTPUT: Provider document and audit; failures carry a sanitized status.
        """
        with self.inflight:
            number = self._slot()
            tokens = self._reserve_tokens(body)
            record = {"attempt": number, "role": role, "requested_model": model,
                      "provider_schema": schema_used, "reserved_tokens": tokens}
            if self.on_start:
                self.on_start(record)
            return self._send(body, model, record)

    def _send(self, body, model, record):
        """PURPOSE: Record one metered HTTP attempt and interpret quota details.
        INPUT: Native request and started attempt. OUTPUT: Response and completed audit row.
        """
        start = monotonic()
        try:
            response = self.http.post(f"{BASE_URL}/models/{model}:generateContent", json=body)
            data = response.json()
            record["http_status"] = response.status_code
            if response.is_success:
                response_model = data.get("modelVersion", "")
                record.update(response_model=response_model, usage=data.get("usageMetadata", {}),
                              finish_reason=next(iter(data.get("candidates", [])), {}).get("finishReason"))
                if not (response_model == MODEL or response_model.startswith(MODEL + "-")):
                    with self.lock:
                        self.blocked = "unexpected_response_model"
                    raise GeminiError(self.blocked)
                return data, record
            error = data.get("error", {})
            quota_rows = list(chain.from_iterable(d.get("violations", []) for d in error.get("details", [])))
            quota = [q.get("quotaMetric", "") for q in quota_rows]
            delay = [d.get("retryDelay", "").rstrip("s") for d in error.get("details", []) if d.get("retryDelay")]
            if not delay and response.headers.get("retry-after"):
                delay = [response.headers["retry-after"]]
            wait = max((float(d) for d in delay if d.replace(".", "", 1).isdigit()), default=0.0)
            record.update(error_status=error.get("status"), quota_metrics=quota, retry_wait=wait,
                          quota_window=[q.get("quotaId", "") for q in quota_rows],
                          schema_error=("schema" in error.get("message", "").casefold()))
            if any("paid_tier" in q.lower() and "free_tier" not in q.lower() for q in quota):
                with self.lock:
                    self.blocked = "unexpected_paid_tier_quota"
            quota_identifiers = quota + record["quota_window"]
            daily = any("perday" in ''.join(c for c in item.lower() if c.isalnum())
                        for item in quota_identifiers)
            if response.status_code == 429 and daily:
                with self.lock:
                    self.blocked = "free_tier_provider_daily_quota"
            elif response.status_code in {401, 403, 404}:
                with self.lock:
                    self.blocked = f"http_{response.status_code}_provider_block"
            if self.blocked:
                record["provider_block"] = self.blocked
            if response.status_code == 429:
                with self.lock:
                    self.next_send = max(self.next_send, monotonic() + min(wait + 1, 60))
            return None, record
        except (httpx.RequestError, json.JSONDecodeError) as error:
            record["transport_error"] = type(error).__name__
            return None, record
        finally:
            record["api_seconds"] = round(monotonic() - start, 4)
            self.on_attempt(record)

    def create(self, *, model, messages, response_format, **settings):
        """PURPOSE: Adapt native Gemini generation to existing validated pipeline role calls.
        INPUT: Locked model, ordered chat messages and original schema. OUTPUT: SDK-shaped JSON and tokens.
        """
        if model != MODEL:
            raise GeminiError("model_id_changed")
        schema = response_format.get("json_schema", {}).get("schema")
        role = response_format.get("json_schema", {}).get("name", "json_object")
        system = [dict(text=m["content"]) for m in messages if m["role"] in {"system", "developer"}]
        contents = [dict(role="model" if m["role"] == "assistant" else "user",
                         parts=[dict(text=m["content"])])
                    for m in messages if m["role"] not in {"system", "developer"}]
        config = {"responseMimeType": "application/json", "candidateCount": 1, "maxOutputTokens": 8192}
        if "temperature" in settings:
            config["temperature"] = settings["temperature"]
        if schema:
            config["responseJsonSchema"] = translate_schema(schema)
        body = {"contents": contents, "generationConfig": config}
        if system:
            body["systemInstruction"] = {"parts": system}
        data = None
        for turn in range(self.retry_attempts):
            data, record = self._post(body, role, model, "responseJsonSchema" in config)
            if data is not None:
                break
            status = record.get("http_status")
            if self.blocked:
                break
            if status == 400 and record.get("schema_error") and "responseJsonSchema" in config:
                del config["responseJsonSchema"]
            elif turn + 1 < self.retry_attempts and (status in {429,500,503} or record.get("transport_error")):
                delay=max(self.backoff_base*2**turn,record.get('retry_wait',0) if status==429 else 0)
                sleep(min(self.backoff_cap,delay))
            else:
                break
        if data is None:
            self.last_provider_failure = self.blocked or str(record.get("http_status") or record.get("transport_error"))
            raise GeminiError(self.last_provider_failure)
        native = next(iter(data.get("candidates", [])), {})
        if native.get("finishReason") not in {"STOP", "MAX_TOKENS"}:
            raise GeminiError("generation_incomplete")
        usage = data.get("usageMetadata", {})
        input_tokens = usage.get("promptTokenCount", 0)
        reasoning = usage.get("thoughtsTokenCount", 0)
        output = usage.get("candidatesTokenCount", 0) + reasoning
        message = "".join(p.get("text", "") for p in native.get("content", {}).get("parts", []) if not p.get("thought"))
        return SimpleNamespace(model=data["modelVersion"], choices=[SimpleNamespace(
            message=SimpleNamespace(content=message, refusal=None),
            finish_reason="length" if native["finishReason"] == "MAX_TOKENS" else "stop")], usage=SimpleNamespace(
                prompt_tokens=input_tokens, completion_tokens=output, total_tokens=usage.get("totalTokenCount", input_tokens + output),
                completion_tokens_details=SimpleNamespace(reasoning_tokens=reasoning),
                prompt_tokens_details=SimpleNamespace(cached_tokens=usage.get("cachedContentTokenCount", 0))))
