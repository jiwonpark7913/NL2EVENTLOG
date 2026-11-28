"""Resolve activity meanings from public evidence without changing physical selectors."""

from __future__ import annotations
from src.common.prompt_loader import load_prompt
from src.common.runtime_input_contract import POLICY_VERSION
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import time
from typing import Any
from jsonschema import Draft202012Validator
from src.common.data_dictionary import dictionary_indexes
from src.common.database_io import quote_identifier as qi
from src.common.database_io import connect_readonly
from src.common.event_clock import scoped_event_clock
VERSION = "activity-semantics-v7-preconstruction-carrier"
STATUSES = {"supported", "ambiguous", "unresolved", "conflicting"}
UNRESOLVED_ACTIVITY_LABEL = "Unresolved activity"
from src.common.llm_usage import DEFAULT_MODEL, chat_settings


def is_placeholder_label(value: Any) -> bool:
    """PURPOSE: Recognize the internal unresolved-activity marker (or an empty name).
    INPUT: Candidate label. OUTPUT: True when the text carries no activity meaning.
    """
    return _normalized(str(value or "")) in {"", _normalized(UNRESOLVED_ACTIVITY_LABEL)}


def _normalized(text: str) -> str:
    """PURPOSE: Compare explicitly stated labels without semantic synonym guesses.
    INPUT: Label text. OUTPUT: Case/whitespace normalized text; raw DB values remain untouched.
    """
    return " ".join(text.split()).casefold()


def _label(value: Any) -> str:
    """PURPOSE: Read supported structured or scalar code definitions.
    INPUT: DD meaning. OUTPUT: Human label, empty for unsupported structures.
    """
    if isinstance(value, dict):
        value = value.get("label", value.get("meaning", value.get("definition", "")))
    return value.strip() if isinstance(value, str) else ""


def atomic_activity_label(value):
    """PURPOSE: Prevent documentation sentences and ambiguous value lists from becoming activities.
    INPUT: Candidate meaning text. OUTPUT: True for concise atomic labels, False for explanatory prose.
    """
    text=_label(value)
    if is_placeholder_label(text):
        return False  # a short internal marker is not a documented activity name
    return bool(text and len(text)<=120 and len(text.split())<=12 and not re.search(
        r'[;\n]|\b(?:selects? the activity|this (?:column|field)|values? (?:are|include)|indicates whether)\b|\sor\s',text,re.I))


ACTIVITY_LABEL_TIME_WORDS = {"time", "timestamp", "date", "datetime"}


def activity_label_issue(value, *, identifier_values=()):
    """PURPOSE: Shared activity-name contract for rule, column-model and review-patch approval paths.
    INPUT: Proposed name and optional observed identifier values that must not become activities.
    OUTPUT: None for an acceptable activity expression (sentence form is allowed), otherwise one of
    placeholder | identifier_value | time_attribute | documentation_or_value_list.
    """
    text = _label(value) if not isinstance(value, str) else value.strip()
    if is_placeholder_label(text):
        return "placeholder"
    norm = _normalized(text)
    if norm in {_normalized(str(v)) for v in identifier_values if str(v).strip()}:
        return "identifier_value"
    tokens = re.findall(r"[a-z0-9]+", norm)
    # A phrase whose head is a clock ("Order creation timestamp", "Date of order") describes a time attribute.
    if tokens and (tokens[-1] in ACTIVITY_LABEL_TIME_WORDS or
                   len(tokens) > 2 and tokens[0] in ACTIVITY_LABEL_TIME_WORDS and tokens[1] == "of"):
        return "time_attribute"
    if not atomic_activity_label(text):
        return "documentation_or_value_list"
    return None


def enumerated_value_label(text,raw_value):
    """PURPOSE: Ground an observed textual value in an explicit DD alternative list.
    INPUT: Scoped carrier description and exact DB value. OUTPUT: That value's label or empty; no general-domain guesses.
    """
    head=re.split(r'[;\n.]',text,maxsplit=1)[0].strip()
    choices=[x.strip(' \"\'') for x in re.split(r'\s+or\s+|\s*[,|]\s*',head,flags=re.I)]
    raw=str(raw_value)
    return raw if len(choices)>1 and all(atomic_activity_label(x) for x in choices) and any(
        _normalized(raw)==_normalized(x) for x in choices) else ''


def _explicit_prose(text: str, raw_value: Any) -> list[str]:
    """PURPOSE: Recover concise, explicit code mappings without guessing from ordinary prose.
    INPUT: Column-local DD text and exact code. OUTPUT: Verbatim meanings for code=meaning forms.
    """
    code = re.escape(str(raw_value))
    pattern = (r"(?<![\w])['\"]?" + code + r"['\"]?\s*(?:=|:|(?i:\bmeans\b|\bdenotes\b|\bstands for\b))"
               r"\s*['\"]?([^,;\n.\"']+)")
    meanings = []
    for match in re.finditer(pattern, text):
        value = match.group(1).strip()
        if (value and len(value.split()) <= 8 and not re.match(r"(?:that|when|if|the code)\b", value, re.I)
                and not re.search(r"\b(?:means|denotes)\b|[=:]", value)):
            meanings.append(value)
    return meanings


def code_table_evidence(connection, table, carrier, tables, dd):
    """PURPOSE: Reuse declared code references and retain competing meanings as evidence.
    INPUT: Read-only connection, source schema/column, schema map and normalized DD.
    OUTPUT: Code-keyed meanings with FK and actual lookup-row provenance; no source joins are changed.
    """
    columns = dictionary_indexes(dd)["columns"]
    result = {}
    for fk in table.foreign_keys:
        pairs = fk.get("columns", [])
        if len(pairs) != 1 or pairs[0][0] != carrier:
            continue
        parent = tables.get(fk["parent_table"])
        if parent is None:
            continue
        key = pairs[0][1]
        for column in parent.columns:
            if column.name == key:
                continue
            description = columns.get((parent.name, column.name), {})
            words = set(re.findall(r"[a-z]+", (column.name + " " + description.get("definition", "")).casefold()))
            if not words & {"meaning", "label", "name", "description"}:
                continue
            if "TEXT" not in column.declared_type.upper() and not column.unique:
                continue
            rows = connection.execute(f"SELECT {qi(key)}, {qi(column.name)} FROM {qi(parent.name)} "
                                      f"WHERE {qi(key)} IS NOT NULL AND {qi(column.name)} IS NOT NULL").fetchall()
            for code, meaning in rows:
                if not isinstance(meaning, str) or not meaning.strip():
                    continue
                identifier = "CT:" + hashlib.sha256(json.dumps(
                    [table.name, carrier, parent.name, key, column.name, code, meaning],
                    ensure_ascii=False, default=str).encode()).hexdigest()[:20]
                result.setdefault(str(code), []).append({"meaning": meaning.strip(),
                    "source": "declared_code_table_label", "evidence": {"id": identifier,
                    "text": f"{parent.name}.{key}={code!r}; {column.name}={meaning!r}",
                    "kind": "verified_code_table_row", "source_table": table.name,
                    "carrier_column": carrier, "lookup_table": parent.name,
                    "lookup_key": key, "lookup_label_column": column.name,
                    "lookup_code": code, "lookup_label": meaning,
                    "foreign_key": deepcopy(fk)}})
    return result


def deterministic_meanings(column_dd, raw_value, lookup=None, table_dd=None):
    """PURPOSE: Combine scoped DD domains, code_meanings, prose and lookup without priority hiding conflicts.
    INPUT: One normalized column, exact observed value and code-table evidence map.
    OUTPUT: Candidate meanings, status and citable local evidence.
    """
    code, candidates, context = str(raw_value), [], []
    column_id = column_dd.get("id", "")
    def add(meaning, source, identifier, text):
        """PURPOSE: Attach one explicit claim. INPUT: Meaning/source/citation. OUTPUT: Updated local lists."""
        if meaning and atomic_activity_label(meaning):
            candidates.append({"meaning": meaning, "source": source,
                               "evidence": {"id": identifier, "text": text, "kind": "dictionary"}})
    domains = column_dd.get("domain_definitions", [])
    for domain in domains:
        if str(domain["code"]) == code:
            add(_label(domain), "data_dictionary_value_domain",
                f"{column_id}:domain:{domain['origin']}:{code}", domain["label"])
    if not domains and code in column_dd.get("value_domain", {}):
        value = column_dd["value_domain"][code]
        add(_label(value), "data_dictionary_value_domain", f"{column_id}:value:{code}",
            value.get("definition", _label(value)) if isinstance(value, dict) else str(value))
    if code in column_dd.get("code_meanings", {}):
        value = column_dd["code_meanings"][code]
        add(_label(value), "data_dictionary_code_meanings", f"{column_id}:code:{code}", str(value))
    for field in ("definition", "description", "readable_name"):
        text = str(column_dd.get(field, "")).strip()
        if text:
            evidence = {"id": f"{column_id}:{field}", "text": text, "kind": "dictionary"}
            context.append(evidence)
            enumerated=enumerated_value_label(text,raw_value)
            if enumerated:add(enumerated,'data_dictionary_enumerated_value',evidence['id'],text)
            for meaning in _explicit_prose(text, raw_value):
                add(meaning, "data_dictionary_explicit_prose", evidence["id"], text)
    for field in ("definition", "description", "row_grain"):
        text = str((table_dd or {}).get(field, "")).strip()
        if text:
            evidence = {"id": f"{table_dd['id']}:{field}", "text": text, "kind": "dictionary"}
            context.append(evidence)
            for meaning in _explicit_prose(text, raw_value):
                add(meaning, "data_dictionary_explicit_prose", evidence["id"], text)
    candidates.extend(deepcopy((lookup or {}).get(code, [])))
    meanings = sorted({_normalized(c["meaning"]) for c in candidates})
    evidence = {c["evidence"]["id"]: c["evidence"] for c in candidates}
    evidence.update({c["id"]: c for c in context})
    return {"status": "supported" if len(meanings) == 1 else "conflicting" if meanings else "unresolved",
            "code_meaning": candidates[0]["meaning"] if len(meanings) == 1 else None,
            "candidates": candidates, "evidence": list(evidence.values())}


ACTION_NOUNS = {"creation": "created", "payment": "paid", "confirmation": "confirmed", "placement": "placed",
                "admission": "admitted", "discharge": "discharged", "departure": "departed", "arrival": "arrived",
                "dispatch": "dispatched", "approval": "approved", "rejection": "rejected",
                "completion": "completed", "receipt": "received", "submission": "submitted",
                "administration": "administered", "omission": "omitted"}


def documented_activity_label(label, column_dd) -> bool:
    """PURPOSE: Rule-approve a column activity label only with explicit equality evidence in its own DD text.
    INPUT: Label being approved (often a column-name hypothesis) and the time column's DD record.
    OUTPUT: True for a documented event_activity, a label quoted by the DD, or a DD action word of the
    label's own word family (claim_filed_at / "filed"). A different word (created_at / "placed the order")
    is not equality evidence and stays unresolved for the LLM; the time role is never activity evidence.
    """
    from src.step1_understand.detect_and_normalize_timestamps import name_tokens, past_action_verbs
    if column_dd.get("event_activity"):
        return True
    text = " ".join(str(column_dd.get(k, "")) for k in ("definition", "description")).casefold()
    label = str(label or "").strip().casefold()
    if not label or not text:
        return False
    # The DD names the label as the activity in the slots _activity_name_from_timestamp reads; a mere
    # mention ("placed the order" for label "Order") is an object, not equality evidence.
    named = re.escape(label)
    if re.search(rf"\b(?:time|occurrence) (?:of|for) {named}\b|\bactual (?:utc )?{named} (?:occurrence )?time\b|"
                 rf"\b{named} occurrence time\b", text):
        return True
    actions = {ACTION_NOUNS.get(word, word) for word in
               past_action_verbs(text) | (set(re.findall(r"[a-z]+", text)) & ACTION_NOUNS.keys())}
    return bool(actions & {ACTION_NOUNS.get(token, token) for token in name_tokens(label)})


def occurrence_evidence(binding, timestamp, table_dd, column_dd, *, review_supported=False,
                        additional_evidence=()):
    """PURPOSE: Keep code meaning independent of eventness and timestamp validity.
    INPUT: Existing physical binding, immutable timestamp and source DD records.
    OUTPUT: Occurrence status/type/reason; snapshot wording cannot become an event through relabeling.
    """
    table_text = " ".join(str(table_dd.get(k, "")) for k in ("definition", "description", "row_grain"))
    table_text += " " + " ".join(str(item.get("text", "")) for item in additional_evidence)
    column_text = " ".join(str(column_dd.get(k, "")) for k in ("definition", "description"))
    if any(term.get("kind") in {"state_transition", "related_value"}
           for term in binding.get("documented_source_conditions", [])):
        from src.step1_understand.detect_and_normalize_timestamps import occurrence_time_policy
        if occurrence_time_policy(timestamp)["eligible"]:
            return {"status": "supported", "semantic_type": "occurrence",
                    "reason": "verified_documented_relational_occurrence"}
    if re.search(r"\bsnapshot\b|\bcurrent(?:\s+\w+){0,4}\s+(?:state|status)\b|"
                 r"\b(static attribute|not an event)\b", table_text + " " + column_text, re.I):
        return {"status": "unresolved", "semantic_type": "state", "reason": "snapshot_is_not_occurrence_evidence"}
    from src.step1_understand.detect_and_normalize_timestamps import occurrence_time_policy
    role_supported = occurrence_time_policy(timestamp)["eligible"]
    paired = binding.get("timestamp_pairing", {}).get("status") in {"supported", "supported_by_review"}
    history = bool(re.search(r"\b(event|activity|occurrence|transition)\b.*\b(history|record|log|stream)\b|"
                            r"\b(history|append.only)\b|one row per (?:event|activity|occurrence)|"
                            r"one (?:business )?(?:task )?occurrence per row", table_text, re.I))
    value_occurrence = bool(re.search(r"\b(event|activity|transition|occurrence)\b", column_text, re.I))
    # A value carrier may name the action while the table DD states the row's action-record grain. Keep this
    # same-word-family proof separate from a generic record/table label: it cannot turn an arbitrary code into
    # an event, and it still requires a supported occurrence clock and value-to-clock pairing below.
    value_documented = documented_activity_label(
        binding.get("alpha", {}).get("value") or binding.get("activity_label"),
        {"definition": table_text})
    prior = binding.get("interpretation_status") == "supported"
    if binding.get("alpha", {}).get("kind") != "value":
        activity_documented = documented_activity_label(
            binding.get("activity_label") or binding.get("alpha", {}).get("name"), column_dd)
        supported = role_supported and (activity_documented or prior or review_supported)
    else:
        documented_pair = binding.get('carrier_clock_relationship', {}).get('status') == 'supported'
        supported = role_supported and (paired or prior) and (
            documented_pair or history or value_occurrence or value_documented
            or review_supported or timestamp.get('row_value_scope'))
    return {"status": "supported" if supported else "unresolved",
            "semantic_type": "occurrence" if supported else "state" if "status" in column_text.casefold() else "unknown",
            "reason": "existing_binding_and_occurrence_time" if supported else "occurrence_evidence_insufficient"}


def _llm_resolution(payload, llm, model, cache):
    """PURPOSE: Resolve only an evidence-bearing unresolved meaning using strict grounded output.
    INPUT: One binding's scoped evidence, SDK client/model/cache.
    OUTPUT: Validated meaning/status and telemetry; never edits or returns physical extraction fields.
    """
    schema = {"type": "object", "additionalProperties": False, "properties": {
        "status": {"type": "string", "enum": sorted(STATUSES)},
        "code_meaning": {"anyOf": [{"type": "string"}, {"type": "null"}]},
        "citations": {"type": "array", "items": {"type": "object", "additionalProperties": False,
            "properties": {"evidence_id": {"type": "string"}, "quote": {"type": "string"}},
            "required": ["evidence_id", "quote"]}},
        "reason": {"type": "string"}}, "required": ["status", "code_meaning", "citations", "reason"]}
    digest = hashlib.sha256(json.dumps([VERSION, model, payload, schema], sort_keys=True,
                                      ensure_ascii=False, default=str).encode()).hexdigest()
    key = POLICY_VERSION + ":" + VERSION + ":" + digest
    audit = {"kind": "activity_semantics", 'event_definition_id': payload['event_definition_id'], "model": model,
             "prompt_version": VERSION, "cache_key": key, "cache_hit": False, "usage": {}, "errors": []}
    started = time.perf_counter()
    value = None
    try:
        if cache is not None and key in cache:
            value, audit["cache_hit"] = deepcopy(cache[key]), True
        else:
            response = llm.chat.completions.create(model=model, **chat_settings(model),
                response_format={"type": "json_schema", "json_schema": {
                    "name": "activity_semantics", "strict": True, "schema": schema}},
                messages=[{"role": "system", "content": (
                    load_prompt('step1_understand', 'interpret_observed_activity_value'))},
                    {"role": "user", "content": "<runtime_data>\n" + json.dumps(payload,
                        ensure_ascii=False, sort_keys=True, default=str) + "\n</runtime_data>"}])
            usage = getattr(response, "usage", None)
            audit["usage"] = {"input_tokens": getattr(usage, "prompt_tokens", 0) or 0,
                              "output_tokens": getattr(usage, "completion_tokens", 0) or 0}
            message = response.choices[0].message
            if getattr(message, "refusal", None):
                raise ValueError("model_refusal")
            value = json.loads(message.content)
        Draft202012Validator(schema).validate(value)
        evidence = {e["id"]: e["text"] for e in payload["evidence"]}
        citations = value["citations"]
        if any(c["evidence_id"] not in evidence or not c["quote"].strip() or
               c["quote"] not in evidence[c["evidence_id"]] for c in citations):
            raise ValueError("invalid_dictionary_citation")
        if value['status']=='supported' and not atomic_activity_label(value.get('code_meaning')):
            raise ValueError('activity_label_is_documentation_or_ambiguous_list')
        if value["status"] == "supported" and (not citations or not value["code_meaning"] or
                                                 not value["code_meaning"].strip()):
            raise ValueError("supported_meaning_requires_evidence")
        raw_pattern = r"(?<!\w)" + re.escape(str(payload["raw_value"])) + r"(?!\w)"
        if value["status"] == "supported" and not any(
                re.search(raw_pattern, c["quote"]) and len(c["quote"].strip()) > len(str(payload["raw_value"])) + 4
                for c in citations):
            raise ValueError("meaning_citation_does_not_link_observed_code")
        if cache is not None:
            cache[key] = deepcopy(value)
        audit["validated"] = True
        return value, audit
    except Exception as error:
        audit.update(validated=False, errors=[type(error).__name__ + ": " + str(error)])
        return None, audit
    finally:
        audit["elapsed_seconds"] = time.perf_counter() - started


COLUMN_OCCURRENCE = {"supported", "unresolved", "rejected"}
COLUMN_TIME_ROLES = {"business_occurrence", "effective_time", "recorded_time", "ingestion_time",
                     "scheduled_time", "unknown"}
COLUMN_PROMPT = load_prompt('step1_understand', 'interpret_timestamp_occurrence')


def column_review_eligible(timestamp):
    """PURPOSE: Decide whether a clock may receive model interpretation of its activity.
    INPUT: TimestampUnit. OUTPUT: True for documented occurrence clocks and for clocks whose role is still
    uncertain; False for clocks a rule has settled as ingestion/planned/recorded or a non-transition effective time.
    """
    from src.step1_understand.detect_and_normalize_timestamps import occurrence_time_policy
    if occurrence_time_policy(timestamp)["eligible"]:
        return True
    role, status = timestamp.get("semantic_role", "unknown"), timestamp.get("role_status", "unknown")
    return status != "supported" or role == "unknown"


def apply_cited_occurrence_role(timestamp, decision, event_definition_id):
    """PURPOSE: Promote an uncertain clock to business_occurrence from a validated, own-column-cited interpretation.
    INPUT: Mutable TimestampUnit, validated column decision and binding ID.
    OUTPUT: True when revised. Settled roles are never changed; the original role stays in role_revisions.
    """
    from src.step1_understand.detect_and_normalize_timestamps import occurrence_time_policy
    if occurrence_time_policy(timestamp)["eligible"] or not column_review_eligible(timestamp):
        return False
    if not (decision["status"] == "supported" and decision["occurrence"] == "supported"
            and decision["time_role"] == "business_occurrence"):
        return False
    timestamp.setdefault("role_revisions", []).append({
        "by": "column_activity_semantics", 'event_definition_id': event_definition_id,
        "from": {"semantic_role": timestamp.get("semantic_role"), "role_status": timestamp.get("role_status")},
        "to": {"semantic_role": "business_occurrence", "role_status": "supported"},
        "citations": deepcopy(decision["citations"])})
    timestamp["semantic_role"], timestamp["role_status"] = "business_occurrence", "supported"
    timestamp.setdefault("role_evidence", []).extend(
        {"source": "cited_column_interpretation", "detail": c["quote"], "evidence_id": c["evidence_id"]}
        for c in decision["citations"])
    return True


def _column_review_payload(binding, timestamp, table, dd):
    """PURPOSE: Scope one column definition's public evidence for model interpretation.
    INPUT: Column-kind binding, its TimestampUnit, physical Table and normalized DD.
    OUTPUT: JSON payload with table-scoped DD statements and structural key/FK/time-role facts only.
    """
    from src.step1_understand.detect_and_normalize_timestamps import occurrence_time_policy
    return {'event_definition_id': binding["id"], "table": binding["table"],
            "timestamp_unit": {k: timestamp.get(k) for k in
                               ("ts_id", "columns", "json_path", "semantic_role", "role_status", "detected_format")},
            "occurrence_time_policy": occurrence_time_policy(timestamp)["status"],
            "structure": {"primary_key": list(table.primary_key) if table else [],
                          "unique_keys": [list(k) for k in table.unique_keys] if table else [],
                          "foreign_keys": deepcopy(table.foreign_keys) if table else []},
            "evidence": [{"id": s["id"], "text": s["text"]} for s in
                         _activity_evidence(dd, binding)]}


def _activity_evidence(dd, binding):
    """PURPOSE: Preserve table-local evidence and relevant global rules for one physical candidate.
    INPUT: Normalized public DD and immutable binding selectors. OUTPUT: Bounded scoped statements;
    global rules enter only when they explicitly mention the table, carrier, value or activity label.
    """
    alpha = binding.get("alpha", {})
    terms = {str(binding.get("table", "")), str(alpha.get("column", "")),
             str(alpha.get("value", "")), str(binding.get("activity_label", "")),
             str(alpha.get("name", ""))}
    terms = {term.casefold().strip() for term in terms if len(term.strip()) >= 3}
    selected = []
    for statement in dd.get("semantic_statements", []):
        if statement.get("table") == binding.get("table"):
            selected.append(statement)
            continue
        if statement.get("table"):
            continue
        text = str(statement.get("text", "")).casefold()
        if any(re.search(r"(?<![a-z0-9_])" + re.escape(term) + r"(?![a-z0-9_])", text)
               for term in terms):
            selected.append(statement)
    return selected[:80]


def _llm_column_resolution(payload, llm, model, cache):
    """PURPOSE: Resolve a column definition's activity and occurrence from cited DD/structure evidence.
    INPUT: _column_review_payload output, SDK client/model/cache.
    OUTPUT: (validated decision or None, audit). Never edits physical selectors or clocks; a time-role
    promotion is applied separately by apply_cited_occurrence_role.
    """
    schema = {"type": "object", "additionalProperties": False, "properties": {
        "status": {"type": "string", "enum": sorted(STATUSES)},
        "activity_name": {"anyOf": [{"type": "string"}, {"type": "null"}]},
        "occurrence": {"type": "string", "enum": sorted(COLUMN_OCCURRENCE)},
        "time_role": {"type": "string", "enum": sorted(COLUMN_TIME_ROLES)},
        "citations": {"type": "array", "items": {"type": "object", "additionalProperties": False,
            "properties": {"evidence_id": {"type": "string"}, "quote": {"type": "string"}},
            "required": ["evidence_id", "quote"]}},
        "reason": {"type": "string"}},
        "required": ["status", "activity_name", "occurrence", "time_role", "citations", "reason"]}
    row = payload.get('activity_value')
    instruction = load_prompt('step1_understand', 'interpret_coded_occurrence') if row else COLUMN_PROMPT
    digest = hashlib.sha256(json.dumps([VERSION, model, instruction, payload, schema], sort_keys=True,
                                       ensure_ascii=False, default=str).encode()).hexdigest()
    key = POLICY_VERSION + ":" + VERSION + ":column:" + digest
    audit = {"kind": "activity_semantics_column", 'event_definition_id': payload['event_definition_id'], "model": model,
             "prompt_version": VERSION, "cache_key": key, "cache_hit": False, "usage": {}, "errors": []}
    started = time.perf_counter()
    try:
        if cache is not None and key in cache:
            value, audit["cache_hit"] = deepcopy(cache[key]), True
        else:
            response = llm.chat.completions.create(model=model, **chat_settings(model),
                response_format={"type": "json_schema", "json_schema": {
                    "name": "row_activity_occurrence" if row else "column_activity_semantics", "strict": True, "schema": schema}},
                messages=[{"role": "system", "content": instruction},
                          {"role": "user", "content": "<runtime_data>\n" + json.dumps(payload,
                              ensure_ascii=False, sort_keys=True, default=str) + "\n</runtime_data>"}])
            usage = getattr(response, "usage", None)
            audit["usage"] = {"input_tokens": getattr(usage, "prompt_tokens", 0) or 0,
                              "output_tokens": getattr(usage, "completion_tokens", 0) or 0}
            message = response.choices[0].message
            if getattr(message, "refusal", None):
                raise ValueError("model_refusal")
            value = json.loads(message.content)
        audit["output"] = deepcopy(value)
        Draft202012Validator(schema).validate(value)
        evidence = {e["id"]: e["text"] for e in payload["evidence"]}
        citations = value["citations"]
        if any(c["evidence_id"] not in evidence or not c["quote"].strip() or
               c["quote"] not in evidence[c["evidence_id"]] for c in citations):
            raise ValueError("invalid_dictionary_citation")
        if value["status"] == "supported":
            issue = activity_label_issue(value.get("activity_name"))
            if issue:
                raise ValueError("activity_label_" + issue)
            own = {f"C:{payload['table']}.{c}" for c in payload["timestamp_unit"].get("columns") or []}
            if not any(c["evidence_id"] in own or c["evidence_id"].rsplit(":", 1)[0] in own for c in citations):
                raise ValueError("citation_does_not_cover_timestamp_column")
            if row:
                carrier_id = f"C:{payload['table']}.{row['column']}"
                if not any(c['evidence_id'] == carrier_id or c['evidence_id'].startswith(carrier_id + ':')
                           for c in citations):
                    raise ValueError('citation_does_not_cover_activity_carrier')
        if cache is not None:
            cache[key] = deepcopy(value)
        audit["validated"] = True
        return value, audit
    except Exception as error:
        audit.update(validated=False, errors=[type(error).__name__ + ": " + str(error)])
        return None, audit
    finally:
        audit["elapsed_seconds"] = time.perf_counter() - started


def attach_activity_semantics(db_path: Path, bindings, tables, timestamps, dd, *,
                              llm=None, model=DEFAULT_MODEL, cache=None, review_budget=50):
    """PURPOSE: Attach grounded meanings and uncertainty while preserving every physical binding/ID.
    INPUT: Discovered/reviewed bindings, actual schema/observations, DD and optional model.
    OUTPUT: In-place semantic metadata/labels and call audits; no key, raw value, timestamp or path edits.
    """
    indexes, audits = dictionary_indexes(dd), []
    by_table, by_time = {t.name: t for t in tables}, {t["ts_id"]: t for t in timestamps}
    lookup_cache, decision_cache = {}, {}
    table_carriers = {}
    for binding in bindings:
        if binding["alpha"]["kind"] == "value":
            table_carriers.setdefault(binding["table"], set()).add(binding["alpha"]["column"])
    connection = connect_readonly(db_path)
    try:
        for binding in bindings:
            alpha, table_name = binding["alpha"], binding["table"]
            column_dd = indexes["columns"].get((table_name, alpha.get("column")), {})
            table_dd = indexes["tables"].get(table_name, {})
            timestamp = by_time.get(binding.get("ts_id"), {})
            if alpha['kind'] == 'value':
                timestamp = scoped_event_clock(binding, timestamp, column_dd,
                    indexes['columns'].get((table_name, (timestamp.get('columns') or [None])[0]), {}))
            scoped_activity_evidence = _activity_evidence(dd, binding)
            column_occurrence_supported = False  # set only by a validated column interpretation below
            column_occurrence_rejected = False   # a cited model rejection is never overridden by keyword rules
            prior_label = binding.get("activity_label", alpha["name"])
            if is_placeholder_label(prior_label):
                # An earlier pass's marker is not a label: only the pre-marker hypothesis may be re-judged.
                prior_label = binding.get("activity_name_hypothesis") or ""
            from src.step1_understand.validate_event_review_patches import reviewed_meaning
            reviewed = reviewed_meaning(binding, timestamp, dd)
            if alpha["kind"] == "value":
                cache_key = (table_name, alpha["column"])
                if cache_key not in lookup_cache:
                    lookup_cache[cache_key] = code_table_evidence(connection, by_table[table_name],
                        alpha["column"], by_table, dd)
                table_context = table_dd if (len(table_carriers[table_name]) == 1 or
                    alpha["column"] in table_dd.get("definition", "")) else None
                preconstruction = binding.get("carrier_value_semantics")
                result = (deepcopy(preconstruction) if preconstruction else
                          deterministic_meanings(column_dd, alpha["value"], lookup_cache[cache_key], table_context))
                known_ids = {item["id"] for item in result["evidence"]}
                result["evidence"].extend({"id": item["id"], "text": item["text"], "kind": "dictionary"}
                                          for item in scoped_activity_evidence if item["id"] not in known_ids)
                method = "deterministic_evidence"
                raw_pattern = r"(?<!\w)" + re.escape(str(alpha["value"])) + r"(?!\w)"
                grounded_context = any(re.search(raw_pattern, e["text"]) for e in result["evidence"])
                if result["status"] == "unresolved" and grounded_context and llm is not None:
                    scoped_key = (*cache_key, type(alpha["value"]).__name__, str(alpha["value"]))
                    if scoped_key not in decision_cache and len(decision_cache) < review_budget:
                        payload = {'event_definition_id': binding["id"], "table": table_name,
                            "column": alpha["column"], "raw_value": alpha["value"],
                            "evidence": result["evidence"], "table_definition": table_dd.get("definition", "")}
                        decision, audit = _llm_resolution(payload, llm, model, cache)
                        audits.append(audit)
                        decision_cache[scoped_key] = decision
                    decision = decision_cache.get(scoped_key)
                    if scoped_key not in decision_cache:
                        result['review_status'] = 'review_budget_exhausted'
                    if decision:
                        result.update(status=decision["status"],
                                      code_meaning=decision["code_meaning"] if decision["status"] == "supported" else None,
                                      citations=decision["citations"])
                        method = "evidence_grounded_llm"
            else:
                # Existing column/table naming is semantic, never an edit to the physical timestamp.
                source_column = indexes["columns"].get((table_name, (timestamp.get("columns") or [None])[0]), {})
                occurrence = occurrence_evidence(binding, timestamp, table_dd, source_column,
                                                 review_supported=reviewed is not None,
                                                 additional_evidence=scoped_activity_evidence)
                named = activity_label_issue(prior_label) is None
                result = {"status": "supported" if occurrence["status"] == "supported" and named else "unresolved",
                          "code_meaning": str(prior_label) if occurrence["status"] == "supported" and named else None,
                          "candidates": [], "evidence": [{"id": source_column.get("id", table_dd.get("id", "")),
                          "text": source_column.get("definition", table_dd.get("definition", "")), "kind": "dictionary"}]}
                method = "existing_column_or_table_evidence"
                if (result["status"] != "supported" and llm is not None and reviewed is None
                        and column_review_eligible(timestamp)):
                    scoped_key = ("column", binding["id"])
                    if scoped_key not in decision_cache and len(decision_cache) < review_budget:
                        decision, audit = _llm_column_resolution(
                            _column_review_payload(binding, timestamp, by_table.get(table_name), dd), llm, model, cache)
                        audits.append(audit)
                        decision_cache[scoped_key] = decision
                    if scoped_key not in decision_cache:
                        result["review_status"] = "review_budget_exhausted"
                    decision = decision_cache.get(scoped_key)
                    column_occurrence_rejected = bool(decision) and decision["occurrence"] == "rejected"
                    if decision and decision["status"] == "supported":
                        if apply_cited_occurrence_role(timestamp, decision, binding["id"]):
                            result["time_role_revised"] = True
                        column_occurrence_supported = decision["occurrence"] == "supported"
                        result.update(status="supported", code_meaning=decision["activity_name"],
                                      citations=decision["citations"])
                        result["evidence"] = [*result["evidence"], *[
                            {"id": c["evidence_id"], "text": c["quote"], "kind": "llm_citation"} for c in decision["citations"]]]
                        method = "evidence_grounded_llm_column"
                    elif decision:
                        result["status"] = decision["status"]
            if (alpha['kind'] == 'value' and result['status'] == 'supported' and llm is not None
                    and column_review_eligible(timestamp)):
                current_occurrence = occurrence_evidence(binding, timestamp, table_dd, column_dd,
                    review_supported=reviewed is not None, additional_evidence=scoped_activity_evidence)
                if current_occurrence['status'] != 'supported':
                    scoped_key = ('row_occurrence', binding['id'])
                    if scoped_key not in decision_cache and len(decision_cache) < review_budget:
                        payload = _column_review_payload(binding, timestamp, by_table.get(table_name), dd)
                        payload['activity_value'] = {'column': alpha['column'], 'value': alpha['value'],
                                                     'meaning': result['code_meaning']}
                        decision, audit = _llm_column_resolution(payload, llm, model, cache)
                        audits.append(audit)
                        decision_cache[scoped_key] = decision
                    decision = decision_cache.get(scoped_key)
                    if (decision and decision['status'] == 'supported' and decision['occurrence'] == 'supported'
                            and decision['time_role'] == 'business_occurrence'
                            and timestamp.get('role_status') == 'supported'
                            and timestamp.get('semantic_role') == 'business_occurrence'):
                        result.update(code_meaning=decision['activity_name'], citations=decision['citations'])
                        binding.setdefault('timestamp_pairing', {}).update(
                            status='supported_by_review', selected=binding['ts_id'], citations=decision['citations'])
                        column_occurrence_supported = True
                        method = 'evidence_grounded_llm_row'
            if reviewed is not None and result['status'] not in {'conflicting', 'ambiguous'}:
                result.update(status='supported', code_meaning=reviewed['activity_name'],
                              citations=reviewed['activity_citations'])
                result['candidates'] = []
                method = 'revalidated_definition_review'
            relationship = binding.get('carrier_clock_relationship', {})
            if relationship.get('status') == 'supported' and result['status'] == 'supported':
                result['code_meaning'] = relationship['label']
                evidence_prefix = column_dd.get('id', '') + ':'
                raw_suffix = ':' + str(alpha['value'])
                value_citations = [
                    {'evidence_id':e['id'],'quote':e['text']} for e in result['evidence']
                    if (e['id'].startswith(evidence_prefix) and e['id'].endswith(raw_suffix))
                    or e['kind'] == 'verified_code_table_row']
                timing = indexes["columns"].get((table_name, timestamp['columns'][0]), {})
                result['citations'] = [*value_citations, *result.get('citations', []),
                    *relationship.get('citations', []), {'evidence_id':timing['id'],'quote':timing['definition']}]
                method = 'documented_carrier_clock'
            occurrence_column = (column_dd if alpha["kind"] == "value" else
                indexes["columns"].get((table_name, (timestamp.get("columns") or [None])[0]), {}))
            occurrence = occurrence_evidence(binding, timestamp, table_dd, occurrence_column,
                                             review_supported=reviewed is not None or column_occurrence_supported,
                                             additional_evidence=scoped_activity_evidence)
            if column_occurrence_rejected and reviewed is None:
                occurrence = {"status": "unresolved", "semantic_type": "unknown",
                              "reason": "column_interpretation_rejected_occurrence"}
            meaning = result["code_meaning"]
            event_label = meaning if result["status"] == "supported" and occurrence["status"] == "supported" else None
            binding["activity_semantics"] = {"version": VERSION,
                "status": result["status"], "code_meaning": meaning, "event_label": event_label,
                "semantic_type": occurrence["semantic_type"], "occurrence_status": occurrence["status"],
                "occurrence_reason": occurrence["reason"], "method": method,
                "review_status": result.get("review_status", "not_required_or_completed"),
                "evidence_ids": sorted({e["id"] for e in result["evidence"] if e["id"]}),
                "evidence": result["evidence"], "alternatives": result["candidates"],
                "citations": result.get("citations", []), "original_label": prior_label or None}
            if result['status']=='supported' and not atomic_activity_label(meaning):
                result.update(status='unresolved',code_meaning=None)
                meaning=None;event_label=None
                binding['activity_semantics'].update(status='unresolved',code_meaning=None,event_label=None)
            if meaning and result["status"] == "supported":
                binding["activity_label"] = meaning
                alpha["name"] = meaning
                binding["activity_label_source"] = (result["candidates"][0]["source"]
                    if result["candidates"] else method)
            if result["status"] in {"conflicting", "ambiguous"}:
                binding["activity_label"] = str(alpha.get("value", prior_label))
                alpha["name"] = binding["activity_label"]
                binding["activity_label_source"] = "unresolved_conflicting_evidence"
            if not atomic_activity_label(binding.get('activity_label')):
                if not is_placeholder_label(binding.get('activity_label')):
                    binding['activity_name_hypothesis']=binding.get('activity_label')
                safe=str(alpha.get('value') or UNRESOLVED_ACTIVITY_LABEL)
                safe=safe if atomic_activity_label(safe) else UNRESOLVED_ACTIVITY_LABEL
                binding['activity_label']=safe;alpha['name']=safe
                binding['activity_label_source']='unresolved_documentation_label'
            binding["interpretation_status"] = ("supported" if event_label else
                "conflicting" if result["status"] == "conflicting" else "unresolved")
        return audits
    finally:
        connection.close()
