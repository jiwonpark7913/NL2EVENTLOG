"""Public-input policy shared by native/legacy builders, runtime graphs and prompts."""

from __future__ import annotations
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
POLICY_VERSION = "public-runtime-input-v1"
BLOCKED_FIELDS = {
    "gold", "gold_ref", "gold_sql", "gold_query", "gold_queries", "gold_event_log",
    "gold_event_graph", "gold_extraction_specification", "gold_es", "gold_bindings",
    "gold_case_mapping", "reference_es", "reference_sql", "reference_event_log",
    "answer_key", "expected_event_log", "expected_events", "oracle_metadata",
    "object_activity_design", "event_encoding", "encoding_detail", "carrier_column",
    "event_activity", "timestamp_summary", "activity_timestamp_pairing",
    'gold_event_definitions', "gold_event_bindings", "gold_case_mappings",
    "event_bindings", "extraction_specification", "case_mapping", "case_mappings",
    "event_case_mapping", "activity_to_timestamp", "activity_timestamp_pairs", "source_mapping",
}
CODE_MAPS = {"value_domain", "code_domain", "code_meanings"}
REVIEW_FIELDS = {"business_rules", "polymorphic_references", "logical_relationships",
                 "source_origin", "source_references", "source_policy", "processes",
                 "business_process_overview"}
HINT_TEXT = re.compile(r"\b(gold|oracle|benchmark|task catalog|current ES|event[- ]to[- ]case|"
                       r"case mapping|default.{0,40}(?:lifecycle|timeline)|\bSELECT\b.{0,80}\bFROM\b)", re.I)
EXECUTION_AXES = ("activity", "occurrence", "time", "identity")


def extraction_status_from_checks(checks):
    """PURPOSE: Apply the single Step 1 executability rule to the four independent proof axes.
    INPUT: Mapping with activity, occurrence, time and identity states.
    OUTPUT: executable only when every required axis is supported, otherwise unresolved plus reasons.
    """
    normalized = {axis: str((checks or {}).get(axis, "unresolved")) for axis in EXECUTION_AXES}
    executable = all(normalized[axis] == "supported" for axis in EXECUTION_AXES)
    return {"checks": normalized, "status": "executable" if executable else "unresolved",
            "unresolved_reasons": [axis + "_not_validated" for axis in EXECUTION_AXES
                                   if normalized[axis] != "supported"]}


class RuntimeInputError(ValueError):
    """A runtime caller attempted to supply an evaluator-only asset or contaminated graph."""


def require_public_path(path):
    """PURPOSE: Refuse known private/evaluator paths at actual file-read boundaries.
    INPUT: Explicit input path. OUTPUT: Resolved path; raises without reading forbidden files.
    """
    path = Path(path).resolve()
    if ({p.casefold() for p in path.parts} & {"private", "gold_dfg", "gold_logs"} or
            path.name.casefold() in {"gold.jsonl", "identity_gold.json", "gold_es.json", "reference_es.json"}):
        raise RuntimeInputError("Evaluator-only file cannot be a runtime input: " + str(path))
    return path


def sanitize_dictionary(raw):
    """PURPOSE: Exclude explicit extraction answers while preserving ordinary business/schema semantics.
    INPUT: Public DD JSON mapping. OUTPUT: Independent safe mapping and reviewable field audit.
    """
    if not isinstance(raw, dict):
        raise RuntimeInputError("Data Dictionary root must be an object")
    findings = []
    def visit(value, path, table=None, column=None, code_map=False):
        """PURPOSE: Classify metadata with location, leaving code vocabulary keys untouched.
        INPUT: JSON subtree and scope. OUTPUT: Filtered subtree plus enclosing audit updates.
        """
        if isinstance(value, list):
            return [visit(v, f"{path}[{i}]", table, column) for i, v in enumerate(value)]
        if not isinstance(value, dict):
            return deepcopy(value)
        table = value.get("table", value.get("table_name", table))
        if ".columns[" in path or path.startswith("$.columns["):
            column = value.get("column", value.get("column_name", value.get("name", column)))
        result = {}
        for key, child in value.items():
            location = f"{path}.{key}"
            blocked = not code_map and (key.casefold() in BLOCKED_FIELDS or key.casefold().startswith("gold_"))
            meaningful = child not in (None, "", [], {})
            if blocked:
                if meaningful:
                    findings.append({"path": location, "table": table, "column": column, "field": key,
                        "classification": "forbidden_extraction_answer", "action": "removed",
                        "reason": "Explicit evaluation/extraction annotation is not ordinary DD semantics."})
                continue
            if not code_map and key in REVIEW_FIELDS and meaningful:
                findings.append({"path": location, "table": table, "column": column, "field": key,
                    "classification": "requires_context_review", "action": "retained_for_review",
                    "reason": "May be ordinary business semantics; name alone does not establish leakage."})
            if not code_map and key in {"definition", "description", "text", "row_grain", "row_meaning"} and isinstance(child, str) and HINT_TEXT.search(child):
                findings.append({"path": location, "table": table, "column": column, "field": key,
                    "classification": "suspected_answer_in_prose", "action": "retained_for_review",
                    "reason": "Potential task/extraction instruction; semantic human review required."})
            if key == "business_rules" and isinstance(child, list):
                for i, rule in enumerate(child):
                    if isinstance(rule, str) and HINT_TEXT.search(rule):
                        findings.append({"path": f"{location}[{i}]", "table": table, "column": column,
                            "field": key, "classification": "suspected_answer_in_prose", "action": "retained_for_review",
                            "reason": "May describe expected scope or extraction; not automatically classified as Gold."})
            result[key] = visit(child, location, table, column, code_map=key in CODE_MAPS)
        return result
    safe = visit(raw, "$")
    audit = {"policy_version": POLICY_VERSION,
        "input_sha256": hashlib.sha256(json.dumps(raw, sort_keys=True, ensure_ascii=False).encode()).hexdigest(),
        "sanitized_sha256": hashlib.sha256(json.dumps(safe, sort_keys=True, ensure_ascii=False).encode()).hexdigest(),
        "blocked_count": sum(f["action"] == "removed" for f in findings),
        "review_count": sum(f["action"] != "removed" for f in findings),
        "semantic_leakage_guarantee": "explicit_fields_filtered_prose_requires_review",
        "findings": findings}
    return safe, audit


def validate_runtime_graph(graph):
    """PURPOSE: Reject precomputed EGs carrying forbidden DD rather than laundering derived candidates.
    INPUT: Runtime graph. OUTPUT: None or RuntimeInputError requiring graph reconstruction.
    """
    dictionary = graph.get("data_dictionary") or {}
    _, audit = sanitize_dictionary(dictionary)
    if audit["blocked_count"]:
        raise RuntimeInputError("Cached graph contains forbidden DD annotations; rebuild from filtered public inputs")
    if graph.get("dbu_rewrite") and graph.get("runtime_input_policy") != POLICY_VERSION:
        raise RuntimeInputError("Native cached graph predates the input policy; rebuild the Evidence Graph")


def require_no_oracle_payload(value):
    """PURPOSE: Guard explicit oracle fields in runtime PI/model/ES payloads, including cached output.
    INPUT: JSON runtime payload. OUTPUT: None or RuntimeInputError; does not inspect ordinary label strings.
    """
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).casefold().startswith("gold_") or key in {"gold", "oracle_metadata", "answer_key"}:
                raise RuntimeInputError("Oracle field in runtime payload: " + str(key))
            if key not in CODE_MAPS:
                require_no_oracle_payload(child)
    elif isinstance(value, list):
        for child in value:
            require_no_oracle_payload(child)
