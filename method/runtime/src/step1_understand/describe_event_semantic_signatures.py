"""Evidence-grounded semantic signatures for query-independent Event Definitions."""

from __future__ import annotations
from src.common.prompt_loader import load_prompt
from src.common.runtime_input_contract import POLICY_VERSION
from collections import defaultdict
from typing import Any
import hashlib
import json
import time
from src.common.graph_identifiers import content_hash
from src.common.data_dictionary import dictionary_indexes
from src.common.event_clock import NON_OCCURRENCE_ROLES
from src.step1_understand.carrier_timestamp_binding import documented_phase
SIGNATURE_SCHEMA_VERSION = "event-semantic-signature-v1"
PROMPT_VERSION = "event-semantic-signature-batch-v2-entity-terminology"
TEMPORAL_ROLES = {"start", "completion", "occurrence", "recorded", "unknown"}
INTERPRETATION_STATUSES = {"supported", "ambiguous", "unknown", "conflicting"}
from src.common.llm_usage import chat_settings


def _response_schema(event_ids: list[str], evidence_ids: list[str]) -> dict[str, Any]:
    """PURPOSE: Constrain one batch response to existing Event and evidence IDs.
    INPUT: Event Definition IDs and typed evidence IDs exposed in this batch.
    OUTPUT: Strict JSON schema; physical graph fields cannot be returned or rewritten.
    """
    nullable_text = {"anyOf": [{"type": "string", "maxLength": 300}, {"type": "null"}]}
    return {"type": "object", "additionalProperties": False, "properties": {
        "signatures": {"type": "array", "items": {
            "type": "object", "additionalProperties": False, "properties": {
                "event_id": {"type": "string", "enum": event_ids},
                "action": nullable_text,
                "transition": nullable_text,
                "temporal_role": {"type": "string", "enum": sorted(TEMPORAL_ROLES)},
                "description": nullable_text,
                "evidence_refs": {"type": "array", "items": {
                    "type": "string", "enum": evidence_ids or [""]}},
                "interpretation_status": {"type": "string", "enum": sorted(
                    INTERPRETATION_STATUSES)},
                "alternatives": {"type": "array", "items": {"type": "string",
                                                                  "maxLength": 300}},
            }, "required": ["event_id", "action", "transition", "temporal_role",
                              "description", "evidence_refs", "interpretation_status",
                              "alternatives"]}},
    }, "required": ["signatures"]}


def _evidence_context(binding: dict[str, Any], timestamp: dict[str, Any],
                      dd: dict[str, Any]) -> tuple[dict[str, Any], set[str]]:
    """PURPOSE: Package bounded public evidence for one Event without oracle metadata.
    INPUT: Event Definition, TimestampUnit and normalized Data Dictionary.
    OUTPUT: Model payload card and the exact evidence-reference allowlist.
    """
    table_dd = next((item for item in dd.get("tables", [])
                     if item.get("table") == binding.get("table")), {})
    columns = set(timestamp.get("columns", []))
    if binding.get("alpha", {}).get("column"):
        columns.add(binding["alpha"]["column"])
    column_dd = [item for item in dd.get("columns", [])
                 if item.get("table") == binding.get("table") and
                 item.get("column") in columns]
    evidence = []
    if table_dd.get("id"):
        evidence.append({"id": table_dd["id"], "kind": "dd_table",
                         "text": table_dd.get("definition", "")})
    for item in column_dd:
        if item.get("id"):
            evidence.append({"id": item["id"], "kind": "dd_column",
                             "column": item.get("column"),
                             "text": item.get("definition", "")})
    for item in timestamp.get("evidence", []):
        identifier = item.get("ref") or item.get("id")
        if identifier:
            evidence.append({"id": str(identifier), "kind": "timestamp_evidence",
                             "text": item.get("quote") or item.get("name") or ""})
    evidence.extend(binding.get("activity_semantics", {}).get("evidence", []))
    deduplicated = {str(item["id"]): item for item in evidence}
    card = {
        "event_id": binding["id"],
        "original_label": binding.get("activity_label") or binding.get("alpha", {}).get("name"),
        "activity_semantics": binding.get("activity_semantics", {}),
        "source_table": binding.get("table"),
        "activity_source": binding.get("activity_source") or binding.get("alpha"),
        "timestamp_unit": {key: timestamp.get(key) for key in (
            "ts_id", "columns", "semantic_role", "role_status")},
        "evidence": list(deduplicated.values()),
    }
    return card, set(deduplicated)


def _unknown_signature(binding: dict[str, Any], timestamp: dict[str, Any], *,
                       method: str, model: str, schema_fingerprint: str,
                       evidence_refs: list[str] | None = None) -> dict[str, Any]:
    """PURPOSE: Preserve an Event when semantic interpretation is unavailable or invalid.
    INPUT: Physical Event/Timestamp and method/version metadata.
    OUTPUT: Complete signature with explicit unknown status and no physical mutation.
    """
    role = "recorded" if timestamp.get("semantic_role") == "recorded_time" else "unknown"
    return {"schema_version": SIGNATURE_SCHEMA_VERSION, "action": None,
            "transition": None, "temporal_role": role, "description": None,
            "evidence_refs": list(evidence_refs or []), "interpretation_status": "unknown",
            "method": method, "model_version": model, "prompt_version": PROMPT_VERSION,
            "schema_fingerprint": schema_fingerprint, "alternatives": [],
            "original_label": binding.get("activity_label") or binding.get("alpha", {}).get("name")}


def _validate_entry(entry: dict[str, Any], event_id: str,
                    allowed_refs: set[str]) -> list[str]:
    """PURPOSE: Validate one model signature against immutable Event evidence.
    INPUT: Parsed entry, expected Event ID and evidence-reference allowlist.
    OUTPUT: Violation codes; empty means the semantic fields are structurally grounded.
    """
    errors = []
    if entry.get("event_id") != event_id:
        errors.append("event_id_mismatch")
    if entry.get("temporal_role") not in TEMPORAL_ROLES:
        errors.append("invalid_temporal_role")
    if entry.get("interpretation_status") not in INTERPRETATION_STATUSES:
        errors.append("invalid_interpretation_status")
    if not set(map(str, entry.get("evidence_refs", []))) <= allowed_refs:
        errors.append("unknown_evidence_reference")
    return errors


def _preserve_evidence_conflict(entry: dict[str, Any],
                                timestamp: dict[str, Any]) -> dict[str, Any]:
    """PURPOSE: Preserve a conflict between model phase meaning and structured TS evidence.
    INPUT: Structurally valid semantic entry and immutable TimestampUnit metadata.
    OUTPUT: Copied entry marked conflicting when non-occurrence time is asserted as an event phase.
    """
    result = dict(entry)
    physical_role = str(timestamp.get("semantic_role") or "unknown")
    non_occurrence_roles = NON_OCCURRENCE_ROLES | {"planned_time"}
    asserted_occurrence_roles = {"start", "completion", "occurrence"}
    if (physical_role in non_occurrence_roles and
            result.get("temporal_role") in asserted_occurrence_roles):
        result["interpretation_status"] = "conflicting"
        alternatives = list(result.get("alternatives") or [])
        conflict = (f"TimestampUnit semantic_role={physical_role} conflicts with "
                    f"temporal_role={result.get('temporal_role')}.")
        if conflict not in alternatives:
            alternatives.append(conflict)
        result["alternatives"] = alternatives
    return result


def _call_batch(llm: Any, model: str, cards: list[dict[str, Any]],
                evidence_ids: list[str]) -> tuple[dict[str, Any], dict[str, Any]]:
    """PURPOSE: Interpret one bounded table-local Event batch with structured output.
    INPUT: OpenAI-compatible client, model, Event evidence cards and evidence IDs.
    OUTPUT: Parsed response and usage/latency audit.
    """
    started = time.perf_counter()
    response = llm.chat.completions.create(
        model=model, **chat_settings(model),
        response_format={"type": "json_schema", "json_schema": {
            "name": "event_semantic_signatures", "strict": True,
            "schema": _response_schema([item["event_id"] for item in cards], evidence_ids)}},
        messages=[{"role": "system", "content": (
            load_prompt('step1_understand', 'describe_event_semantic_signature'))},
            {"role": "user", "content": json.dumps({"events": cards}, ensure_ascii=False,
                                                       sort_keys=True)}])
    value = json.loads(response.choices[0].message.content)
    usage = getattr(response, "usage", None)
    return value, {"input_tokens": getattr(usage, "prompt_tokens", 0) or 0,
                   "output_tokens": getattr(usage, "completion_tokens", 0) or 0,
                   "latency_seconds": time.perf_counter() - started}


def attach_semantic_signatures(bindings: list[dict[str, Any]],
                               timestamps: list[dict[str, Any]], dd: dict[str, Any], *,
                               llm: Any | None, model: str,
                               cache: dict[str, Any] | None = None,
                               batch_size: int = 20,
                               supported_only: bool = False) -> list[dict[str, Any]]:
    """PURPOSE: Attach cached, validated semantic signatures without altering physical evidence.
    INPUT: Event Definitions, TimestampUnits, normalized DD, optional model/cache and batch bound.
    OUTPUT: Per-batch audits; every Event receives exactly one versioned signature.
    """
    timestamp_by_id = {item["ts_id"]: item for item in timestamps}
    dictionaries = dictionary_indexes(dd)['columns']
    semantic_dd = {key: value for key, value in dd.items()
                   if key not in {"ignored_answer_bearing_metadata", "input_contract_audit"}}
    schema_fingerprint = content_hash({"dd": semantic_dd, "events": [{
        "id": item["id"], "table": item.get("table"), "alpha": item.get("alpha"),
        "ts_id": item.get("ts_id")} for item in bindings]})
    by_table: dict[str, list[dict[str, Any]]] = defaultdict(list)
    contexts: dict[str, tuple[dict[str, Any], set[str]]] = {}
    skipped=[]
    from src.step1_understand.detect_and_normalize_timestamps import occurrence_time_policy
    for binding in sorted(bindings, key=lambda item: item["id"]):
        from src.common.event_clock import scoped_event_clock
        timestamp = scoped_event_clock(binding, timestamp_by_id.get(binding.get("ts_id"), {}))
        semantics=binding.get('activity_semantics',{})
        if supported_only and (semantics.get('status')!='supported' or
                semantics.get('occurrence_status')!='supported' or not occurrence_time_policy(timestamp)['eligible']):
            binding['semantic_signature']=_unknown_signature(binding,timestamp,method='other',model=model,
                                                           schema_fingerprint=schema_fingerprint)
            skipped.append(binding['id'])
            continue
        relationship = binding.get('carrier_clock_relationship', {})
        if clock_id := binding.get('documented_column_clock'):
            clock = dictionaries[binding['table'],timestamp['columns'][0]]
            phase = documented_phase(timestamp,clock['definition'])
            label = binding['activity_label']
            base = _unknown_signature(binding,timestamp,method='documented_column_clock',model=model,
                                      schema_fingerprint=schema_fingerprint)
            binding['semantic_signature'] = {**base,'action':label,'description':label,
                'interpretation_status':'supported','temporal_role':{'start':'start','complete':'completion'}.get(phase,'occurrence'),
                'evidence_refs':[clock_id]}
            continue
        if relationship.get('status') == 'supported':
            base = _unknown_signature(binding,timestamp,method='documented_carrier_clock',model=model,
                                      schema_fingerprint=schema_fingerprint)
            clock_id = relationship['clock_evidence_id']
            binding['semantic_signature'] = {**base,'action':binding['activity_label'],
                'description':binding['activity_label'],'interpretation_status':'supported',
                'temporal_role':{'start':'start','complete':'completion'}.get(relationship['phase'],'occurrence'),
                'evidence_refs':sorted({clock_id, *(c['evidence_id'] for c in semantics.get('citations',[]))})}
            continue
        contexts[binding["id"]] = _evidence_context(binding, timestamp, dd)
        by_table[str(binding.get("table"))].append(binding)
    audits = ([{"kind":"event_semantic_signature","task":"event_semantic_signature",
                 "actual_model_call":False,"skipped_ids":skipped,"usage":{},
                 "reason":"unsupported_activity_or_clock_cannot_be_promoted_by_signature"}] if skipped else [])
    for table, table_events in sorted(by_table.items()):
        for offset in range(0, len(table_events), max(1, batch_size)):
            batch = table_events[offset:offset + max(1, batch_size)]
            cards = [contexts[item["id"]][0] for item in batch]
            allowed = {item["id"]: contexts[item["id"]][1] for item in batch}
            evidence_ids = sorted(set().union(*allowed.values()))
            digest = hashlib.sha256(json.dumps(cards, ensure_ascii=False,
                                               sort_keys=True).encode()).hexdigest()
            key = f"{POLICY_VERSION}:{PROMPT_VERSION}:{model}:{schema_fingerprint}:{digest}"
            audit = {"kind": "event_semantic_signature", "table": table,
                     "prompt_version": PROMPT_VERSION, "model": model,
                     "cache_key": key, "cache_hit": False, "event_count": len(batch),
                     "usage": {}, "missing_ids": [], "invalid": {}}
            value = None
            try:
                if cache is not None and key in cache:
                    value, audit["cache_hit"] = cache[key], True
                elif llm is not None:
                    value, audit["usage"] = _call_batch(llm, model, cards, evidence_ids)
                    if cache is not None:
                        cache[key] = value
            except Exception as error:
                audit["error"] = f"{type(error).__name__}: {error}"
            returned = {str(item.get("event_id")): item
                        for item in (value or {}).get("signatures", [])
                        if isinstance(item, dict) and item.get("event_id")}
            retry_ids = [item["id"] for item in batch
                         if item["id"] not in returned or _validate_entry(
                             returned[item["id"]], item["id"], allowed[item["id"]])]
            if retry_ids and value is not None and llm is not None and not audit["cache_hit"]:
                retry_cards = [contexts[event_id][0] for event_id in retry_ids]
                retry_evidence = sorted(set().union(*(allowed[event_id]
                                                      for event_id in retry_ids)))
                try:
                    retry_value, retry_usage = _call_batch(
                        llm, model, retry_cards, retry_evidence)
                    for item in retry_value.get("signatures", []):
                        if isinstance(item, dict) and item.get("event_id") in retry_ids:
                            returned[str(item["event_id"])] = item
                    audit["retry"] = {"attempted_ids": retry_ids, "usage": retry_usage}
                    for key_name in ("input_tokens", "output_tokens", "latency_seconds"):
                        audit["usage"][key_name] = audit["usage"].get(key_name, 0) + \
                            retry_usage.get(key_name, 0)
                except Exception as error:
                    audit["retry"] = {"attempted_ids": retry_ids,
                                      "error": f"{type(error).__name__}: {error}"}
                if cache is not None:
                    cache[key] = {"signatures": list(returned.values())}
            for binding in batch:
                event_id = binding["id"]
                timestamp = timestamp_by_id.get(binding.get("ts_id"), {})
                entry = returned.get(event_id)
                errors = _validate_entry(entry or {}, event_id, allowed[event_id]) if entry else [
                    "missing_entry"]
                if errors:
                    audit["invalid"][event_id] = errors
                    binding["semantic_signature"] = _unknown_signature(
                        binding, timestamp, method="other", model=model,
                        schema_fingerprint=schema_fingerprint)
                    continue
                entry = _preserve_evidence_conflict(entry, timestamp)
                binding["semantic_signature"] = {
                    "schema_version": SIGNATURE_SCHEMA_VERSION,
                    **{key_name: entry.get(key_name) for key_name in (
                        "action", "transition", "temporal_role", "description",
                        "evidence_refs", "interpretation_status", "alternatives")},
                    "method": "cached" if audit["cache_hit"] else "batched_llm",
                    "model_version": model, "prompt_version": PROMPT_VERSION,
                    "schema_fingerprint": schema_fingerprint,
                    "original_label": binding.get("activity_label") or
                                      binding.get("alpha", {}).get("name"),
                }
            audit["missing_ids"] = sorted(set(item["id"] for item in batch) - set(returned))
            audit["unresolved_count"] = sum(
                item["semantic_signature"]["interpretation_status"] in {
                    "unknown", "ambiguous", "conflicting"} for item in batch)
            audits.append(audit)
    return audits
