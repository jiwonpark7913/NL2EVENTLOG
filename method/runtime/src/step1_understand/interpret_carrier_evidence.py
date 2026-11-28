"""Ground carrier identification and value/clock interpretation in public metadata."""

from copy import deepcopy
from json import dumps, loads
import re
from time import perf_counter

from jsonschema import Draft202012Validator

from src.common.llm_usage import chat_settings
from src.common.prompt_loader import load_prompt
from src.common.schema_metadata import stable_id
from src.step1_understand.carrier_timestamp_binding import documented_phase, endpoint_label
from src.step1_understand.resolve_activity_meanings import activity_label_issue

VERSION = "carrier-identification-v2"
BATCH_SIZE = 20


def _record(fields):
    """PURPOSE: Define a closed JSON record. INPUT: Field schemas. OUTPUT: Required record schema."""
    return {"type": "object", "properties": fields, "required": list(fields),
            "additionalProperties": False}


_STRING = {"type": "string"}
_CITATION = _record({"evidence_id": _STRING, "quote": _STRING})
_TASKS = {
    "event_encoding_identification": ["carrier", "attribute", "unresolved"],
    "carrier_value_semantics": ["supported", "unresolved"],
    "carrier_value_timestamp_relationship": ["actual", "unrelated", "unresolved"],
}


def _literal(value, text):
    """PURPOSE: Match a complete observed value or identifier. INPUT: Value, prose. OUTPUT: Exact-token match."""
    return bool(re.search(r"(?<!\w)" + re.escape(str(value)) + r"(?!\w)", text))


def _review(task, candidates, evidence, context, llm, model, cache, audits):
    """PURPOSE: Ask for cited semantic decisions for existing IDs, without proposing selectors or SQL.
    INPUT: Task, bounded candidates, public source text and client/cache.
    OUTPUT: Decisions with valid local IDs and exact quotes; audit of rejected claims and failed calls.
    """
    if llm is None or not candidates:
        return {}
    instructions = load_prompt("step1_understand", "interpret_carrier_evidence").split("\n## ")
    task_instruction = next(section.split("\n", 1)[1] for section in instructions[1:]
                            if section.split("\n", 1)[0] == task)
    instruction = instructions[0] + "\n" + task_instruction
    ids = {str(index): candidate for index, candidate in enumerate(candidates, 1)}
    payload = {"task": task, "context": context, "candidates": [
        {**candidate, "id": identifier} for identifier, candidate in ids.items()], "evidence": evidence}
    choice = _record({"id": {"type": "string", "enum": list(ids)},
                      "decision": {"type": "string", "enum": _TASKS[task]}, "label": _STRING,
                      "citations": {"type": "array", "items": _CITATION}})
    schema = _record({"decisions": {"type": "array", "items": choice}})
    key = stable_id(VERSION, [model, instruction, dumps(payload, default=str), schema])
    audit = {"kind": task, "table": context["table"], "model": model, "prompt_version": VERSION,
             "cache_key": key, "cache_hit": False, "usage": {}, "errors": [],
             "requested_candidate_ids": [candidate["id"] for candidate in candidates],
             "carrier_column": context.get("carrier_column")}
    audits.append(audit)
    started = perf_counter()
    try:
        if cache is not None and key in cache:
            value, audit["cache_hit"] = deepcopy(cache[key]), True
        else:
            response = llm.chat.completions.create(model=model, **chat_settings(model), messages=[
                {"role": "system", "content": instruction},
                {"role": "user", "content": "<runtime_data>\n" + dumps(payload, ensure_ascii=False, default=str)
                 + "\n</runtime_data>"}], response_format={"type": "json_schema", "json_schema": {
                     "name": "carrier_evidence", "strict": True, "schema": schema}})
            usage = getattr(response, "usage", None)
            audit["usage"] = {"input_tokens": getattr(usage, "prompt_tokens", 0) or 0,
                              "output_tokens": getattr(usage, "completion_tokens", 0) or 0}
            message = response.choices[0].message
            if getattr(message, "refusal", None):
                raise ValueError("model_refusal")
            value = loads(message.content)
        Draft202012Validator(schema).validate(value)
        submitted = value["decisions"]
        counts = {item["id"]: 0 for item in submitted}
        for item in submitted:
            counts[item["id"]] += 1
        audit["missing_candidate_ids"] = [candidate["id"] for identifier, candidate in ids.items()
                                          if identifier not in counts]
        decisions = {}
        for item in submitted:
            candidate = ids.get(item["id"])
            if candidate is None or counts[item["id"]] != 1:
                audit["errors"].append({"id": item["id"], "reason": "unknown_or_duplicate_candidate"})
                continue
            cites = item["citations"]
            if not cites or any(c["evidence_id"] not in candidate["evidence_ids"] or not c["quote"].strip()
                                or c["quote"] not in evidence[c["evidence_id"]] for c in cites):
                audit["errors"].append({"id": item["id"], "reason": "unverified_candidate_citation"})
                continue
            decisions[candidate["id"]] = item
        if cache is not None and not audit["missing_candidate_ids"] and not audit["errors"]:
            cache[key] = deepcopy(value)
        audit["validated_decisions"] = list(decisions)
        return decisions
    except Exception as error:
        audit["errors"].append(type(error).__name__)
        audit["missing_candidate_ids"] = audit["requested_candidate_ids"]
        return {}
    finally:
        audit["elapsed_seconds"] = perf_counter() - started


def identify_carriers(table, evaluations, profiles, columns, table_doc, clocks, *, llm, model, cache, audits):
    """PURPOSE: Admit a column as an occurrence discriminator before reading its complete domain.
    INPUT: Bounded profiles, rule evaluations and public table/clock/column definitions.
    OUTPUT: Updates admission and citations for confirmed carriers; ambiguous columns stay unadmitted.
    """
    table_ref = table_doc.get("id", table.id)
    table_text = table_doc.get("definition", "")
    evidence = {table_ref: table_text} if table_text else {}
    candidates = []
    for item in evaluations:
        if item["accepted"] or not item["plausible_carrier"]:
            continue
        column = columns.get((table.name, item["column"]), {})
        text = column.get("definition", "")
        if not text or set(item["rejection_reasons"]) & {"documented_not_activity",
                "identifier_key_without_activity_code_evidence"}:
            continue
        evidence[item["column_id"]] = text
        candidates.append({"id": item["column_id"], "column": item["column"],
                           "distinct_count": item["distinct_count"],
                           "sample": [r["value"] for r in profiles[item["column"]]["frequent_values"][:5]],
                           "evidence_ids": [item["column_id"], *([table_ref] if table_text else [])]})
    decisions = _review("event_encoding_identification", candidates, evidence, {
        "table": table.name, "timestamp_descriptions": clocks}, llm, model, cache, audits)
    for item in evaluations:
        choice = decisions.get(item["column_id"])
        if not choice:
            continue
        cited_column = any(c["evidence_id"] == item["column_id"] for c in choice["citations"])
        if choice["decision"] == "carrier" and cited_column:
            item.update(accepted=True, evidence_status="supported", admission="cited_model",
                        admission_citations=choice["citations"])
        elif choice["decision"] == "attribute":
            item.update(evidence_status="rejected", admission="cited_non_carrier",
                        admission_citations=choice["citations"])


def interpret_values(table, column_doc, resolutions, *, llm, model, cache, audits):
    """PURPOSE: Resolve missing value meanings in batches before constructing any ED.
    INPUT: Admitted carrier, observed typed values paired with deterministic resolutions.
    OUTPUT: Updates only unresolved, exactly cited values; preserves all conflicts and unknowns.
    """
    evidence, candidates, by_id = {}, [], {}
    for index, (raw, resolution) in enumerate(resolutions):
        if resolution["status"] != "unresolved":
            continue
        scoped = {e["id"]: e["text"] for e in resolution["evidence"]
                  if _literal(raw, e["text"]) and len(e["text"].strip()) > len(str(raw)) + 4}
        if scoped:
            value_id = str(index)
            by_id[value_id] = (raw, resolution)
            evidence.update(scoped)
            candidates.append({"id": value_id, "raw_value": raw, "evidence_ids": list(scoped)})
    for offset in range(0, len(candidates), BATCH_SIZE):
        group = candidates[offset:offset + BATCH_SIZE]
        scoped = {ref: evidence[ref] for item in group for ref in item["evidence_ids"]}
        decisions = _review("carrier_value_semantics", group, scoped, {
            "table": table, "carrier_column": column_doc["column"]}, llm, model, cache, audits)
        for identifier, decision in decisions.items():
            raw, resolution = by_id[identifier]
            label = decision["label"].strip()
            citations = [c for c in decision["citations"] if _literal(raw, c["quote"])
                         and _literal(label.casefold(), c["quote"].casefold())]
            if decision["decision"] != "supported" or activity_label_issue(label, identifier_values=[raw]) or not citations:
                continue
            reference = f"{column_doc['id']}:interpreted:{raw}"
            resolution.update(status="supported", code_meaning=label, method="evidence_grounded_llm",
                              citations=citations)
            resolution["evidence"].extend({"kind": "llm_citation", "id": reference, "text": c["quote"],
                                           "source_evidence_id": c["evidence_id"]} for c in citations)


def interpret_relationships(table, column, pending, *, llm, model, cache, audits):
    """PURPOSE: Interpret unresolved value/clock links with separate clock and value evidence.
    INPUT: Physical candidate pairs with supported values and clocks and their public evidence.
    OUTPUT: Verified per-pair meanings or exclusions; independently known clock roles stay fixed.
    """
    for offset in range(0, len(pending), BATCH_SIZE):
        group = pending[offset:offset + BATCH_SIZE]
        evidence = {}
        candidates = []
        for identifier, row in group:
            value_evidence = {e["id"]: e["text"] for e in row["resolution"]["evidence"]
                              if e["id"].endswith(":" + str(row["value"])) or _literal(row["value"], e["text"])}
            clock_ref = row["clock"]["id"]
            evidence.update(value_evidence)
            evidence[clock_ref] = row["clock"]["definition"]
            candidates.append({"id": identifier, "raw_value": row["value"], "value_meaning": row["resolution"]["code_meaning"],
                               "timestamp_columns": row["unit"]["columns"], "clock_role": row["unit"]["semantic_role"],
                               "clock_evidence_id": clock_ref, "evidence_ids": [clock_ref, *value_evidence]})
        results = _review("carrier_value_timestamp_relationship", candidates, evidence, {
            "table": table, "carrier_column": column}, llm, model, cache, audits)
        for identifier, row in group:
            decision = results.get(identifier)
            if not decision:
                continue
            clock_cited = {c["evidence_id"] == row["clock"]["id"] for c in decision["citations"]}
            if clock_cited != {True, False}:
                continue
            relationship = row["relationship"]
            if decision["decision"] == "unrelated":
                relationship.update(status="excluded", reason="cited_clock_not_for_value")
            if decision["decision"] == "actual":
                phase = documented_phase(row["unit"], row["clock"]["definition"])
                relationship.update(status="supported", reason="cited_value_timestamp_relationship",
                                    phase=phase, label=endpoint_label(row["resolution"]["code_meaning"], phase),
                                    citations=decision["citations"])
