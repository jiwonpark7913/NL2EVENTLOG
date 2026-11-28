"""Evidence-backed identity-mapping assessment between Tables' representative Keys."""

from __future__ import annotations
from src.common.prompt_loader import load_prompt
from src.common.runtime_input_contract import POLICY_VERSION
from src.common.entity_identity import identity_review_judgment
from src.common.attribution_policy import declared_foreign_key_groups
from itertools import combinations
from pathlib import Path
from typing import Any
import hashlib
import json
import re
import sqlite3
from src.common.database_io import connect_readonly, quote_identifier
PROMPT_VERSION = "representative-key-identity-v4-entity-type"
RESPONSE_SCHEMA_NAME = "representative_key_identity_review"
AUDIT_TASK = "representative_key_identity"
_GENERIC = {
    "business", "data", "detail", "extension", "header", "info", "information",
    "master", "record", "table", "current", "status", "state", "attribute",
    "attributes", "id", "key", "no", "number", "the", "of", "object",
    "identifier", "instance", "optional", "same", "related",
}
_NON_IDENTITY = re.compile(
    r"\b(distinct|separate|independent lifecycle|different object|history record|"
    r"event log|transaction record|child object|parent object)\b", re.I)
_EXPLICIT_IDENTITY = re.compile(
    r"\b(same (?:business )?(?:entity|instance|object|order)|same object identity|"
    r"identif(?:y|ies) the same|vertical(?:ly)? partition(?:ed)?|extension of (?:the )?same|"
    r"additional (?:attributes|information) (?:for|of) (?:the )?same|"
    r"one[- ]to[- ]one extension)\b", re.I)
from src.common.llm_usage import DEFAULT_MODEL, chat_settings


def _tokens(value: str) -> set[str]:
    """PURPOSE: Extract conservative business tokens from physical or documented names.
    INPUT: One name or Data Dictionary definition.
    OUTPUT: Lowercase alphanumeric tokens with storage and identifier words removed.
    """
    expanded = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    return {token for token in re.findall(r"[a-z0-9]+", expanded.casefold())
            if token not in _GENERIC}


def _physical_key_types(connection: sqlite3.Connection,
                        item: dict[str, Any]) -> dict[str, str]:
    """PURPOSE: Read authoritative declared SQL types for every complete key column.
    INPUT: Read-only connection and one Physical Object.
    OUTPUT: Key-column to declared-type mapping from the live schema.
    """
    types = {str(row[1]): str(row[2] or "") for row in connection.execute(
        f"PRAGMA table_info({quote_identifier(item['table'])})")}
    return {column: types.get(column, "") for column in item["pk"]}


def _domain(connection: sqlite3.Connection, table: str,
            columns: list[str]) -> set[tuple[Any, ...]]:
    """PURPOSE: Read a complete non-null composite key domain without lossy normalization.
    INPUT: Read-only SQLite connection, table and ordered full key columns.
    OUTPUT: Exact key tuples; NULL-containing tuples are excluded.
    """
    projection = ", ".join(quote_identifier(column) for column in columns)
    non_null = " AND ".join(f"{quote_identifier(column)} IS NOT NULL" for column in columns)
    return set(connection.execute(
        f"SELECT DISTINCT {projection} FROM {quote_identifier(table)} WHERE {non_null}"))


def _identity_conflicts(connection, left, right):
    """PURPOSE: Detect counterexamples to equal keys denoting one instance.
    INPUT: Read-only DB and two ordered keys; compares shared declared single-column UNIQUE identifiers.
    OUTPUT: Auditable full-scan conflict counts and checked discriminators, preserving key components.
    Mutable ordinary attributes and temporal columns are not assumed invariant identifiers.
    """
    def discriminators(item):
        """PURPOSE: Collect alternate declared identifiers. INPUT: Object. OUTPUT: Column set."""
        result = set()
        for index in connection.execute(f"PRAGMA index_list({quote_identifier(item['table'])})"):
            if not index[2] or index[4]:
                continue
            columns = [row[2] for row in connection.execute(
                f"PRAGMA index_info({quote_identifier(index[1])})")]
            if len(columns) == 1 and columns[0] and columns[0] not in item['pk']:
                result.add(columns[0])
        return result
    checked = sorted(discriminators(left) & discriminators(right))
    join = ' AND '.join(f'l.{quote_identifier(a)} = r.{quote_identifier(b)}'
                        for a, b in zip(left['pk'], right['pk']))
    conflicts = []
    for column in checked:
        quoted = quote_identifier(column)
        count = connection.execute(
            f"SELECT COUNT(*) FROM {quote_identifier(left['table'])} l "
            f"JOIN {quote_identifier(right['table'])} r ON {join} "
            f"WHERE l.{quoted} IS NOT NULL AND r.{quoted} IS NOT NULL AND l.{quoted} IS NOT r.{quoted}").fetchone()[0]
        if count:
            conflicts.append({'column': column, 'count': count})
    return {'checked_identifiers': checked, 'conflicts': conflicts,
            'sampling': False, 'scope': 'all_matching_complete_key_tuples',
            'limitation': 'Unobserved identifiers and ordinary mutable attributes do not prove instance identity.'}


def _declared_shared_pk(connection: sqlite3.Connection, left: dict[str, Any],
                        right: dict[str, Any]) -> bool:
    """PURPOSE: Detect an optional shared-PK FK in either direction.
    INPUT: Read-only DB and two PK-backed Physical Object records.
    OUTPUT: True only when one complete PK maps to the other complete PK.
    """
    def one_way(child: dict[str, Any], parent: dict[str, Any]) -> bool:
        """PURPOSE: Check one child-to-parent shared-PK direction.
        INPUT: Child and parent Physical Object records.
        OUTPUT: True for one declared FK covering both complete ordered PKs; an FK that omits its
                target columns is read as the parent's PK, exactly as in attribution validation.
        """
        return any(group["parent_table"] == parent["table"] and
                   [source for source, _ in group["columns"]] == child["pk"] and
                   [target for _, target in group["columns"]] == parent["pk"]
                   for group in declared_foreign_key_groups(connection, child["table"]))
    return one_way(left, right) or one_way(right, left)


def _type_affinity(value: str) -> str:
    """PURPOSE: Compare SQLite declarations by affinity without coercing key values.
    INPUT: Declared SQL type text.
    OUTPUT: INTEGER, TEXT, BLOB, REAL or NUMERIC affinity.
    """
    upper = value.upper()
    if "INT" in upper:
        return "INTEGER"
    if any(token in upper for token in ("CHAR", "CLOB", "TEXT")):
        return "TEXT"
    if "BLOB" in upper or not upper:
        return "BLOB"
    if any(token in upper for token in ("REAL", "FLOA", "DOUB")):
        return "REAL"
    return "NUMERIC"


def _pair_metadata(left: dict[str, Any], right: dict[str, Any], dd: dict[str, Any]
                   ) -> dict[str, Any]:
    """PURPOSE: Collect public semantic and type evidence for one candidate pair.
    INPUT: Two Physical Objects and normalized Data Dictionary.
    OUTPUT: Definitions, evidence IDs, tokens, key names and type affinities.
    """
    table_dd = {item["table"]: item for item in dd.get("tables", [])}
    column_dd = {(item["table"], item["column"]): item for item in dd.get("columns", [])}

    def one(item: dict[str, Any]) -> dict[str, Any]:
        """PURPOSE: Build one side of a pair-local identity payload.
        INPUT: Physical Object record.
        OUTPUT: Table and complete-PK documentation with existing evidence IDs.
        """
        table = table_dd.get(item["table"], {})
        columns = [column_dd.get((item["table"], column), {}) for column in item["pk"]]
        return {
            "table_key_id": item["id"], "table": item["table"], "pk_columns": list(item["pk"]),
            "key_kind": item.get("key_kind", "primary_key"),
            "unique_non_null_by_representative_key_selection": True,
            "table_definition": table.get("definition", ""),
            "row_grain": table.get("row_grain", ""),
            "table_evidence_id": table.get("id"),
            "pk": [{"column": column, "type": record.get("type", ""),
                    "affinity": _type_affinity(str(record.get("type", ""))),
                    "definition": record.get("definition", ""),
                    "evidence_id": record.get("id")}
                   for column, record in zip(item["pk"], columns)],
        }

    left_meta, right_meta = one(left), one(right)
    left_text = " ".join([left["table"], left_meta["table_definition"],
                           *(item["definition"] for item in left_meta["pk"])])
    right_text = " ".join([right["table"], right_meta["table_definition"],
                            *(item["definition"] for item in right_meta["pk"])])
    evidence_ids = sorted({str(value) for side in (left_meta, right_meta)
                           for value in [side.get("table_evidence_id"),
                                         *(item.get("evidence_id") for item in side["pk"])]
                           if value})
    return {"left": left_meta, "right": right_meta,
            "left_text": left_text, "right_text": right_text,
            "shared_tokens": sorted(_tokens(left_text) & _tokens(right_text)),
            "same_key_names": [value.casefold() for value in left["pk"]] ==
                              [value.casefold() for value in right["pk"]],
            "type_compatible": [item["affinity"] for item in left_meta["pk"]] ==
                               [item["affinity"] for item in right_meta["pk"]],
            "evidence_ids": evidence_ids}


def _response_schema(evidence_ids: list[str]) -> dict[str, Any]:
    """PURPOSE: Constrain the semantic identity judge to auditable decisions.
    INPUT: Pair-local Data Dictionary evidence IDs.
    OUTPUT: Strict OpenAI JSON schema with no physical identifiers invented by the model.
    """
    allowed = evidence_ids or ["NO_EVIDENCE"]
    return {"type": "object", "additionalProperties": False, "properties": {
        "row_grain_compatible": {"type": "string", "enum": ["YES", "NO", "UNKNOWN"]},
        "same_entity_type": {"type": "string", "enum": ["YES", "NO", "UNKNOWN"]},
        "identity_correspondence": {"type": "string", "enum": ["YES", "NO", "UNKNOWN"]},
        "explicit_identity_mapping": {"type": "string",
                                      "enum": ["PRESENT", "ABSENT", "UNKNOWN"]},
        "semantic_decision": {"type": "string",
                              "enum": ["SUPPORT", "CONTRADICT", "INSUFFICIENT"]},
        "evidence_refs": {"type": "array", "items": {"type": "string", "enum": allowed}},
        "reason": {"type": "string"}},
        "required": ["row_grain_compatible", "same_entity_type", "identity_correspondence", "explicit_identity_mapping",
                     "semantic_decision", "evidence_refs", "reason"]}


def _semantic_judgment(payload: dict[str, Any], evidence_ids: list[str], llm: Any | None,
                       model: str, cache: dict[str, Any] | None
                       ) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """PURPOSE: Judge business meaning and a concrete equal-key identity correspondence.
    INPUT: Pair evidence, allowed evidence IDs, optional model client and response cache.
    OUTPUT: Validated structured judgment or None plus a complete reproducibility audit.
    """
    digest = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    key = f"{POLICY_VERSION}:{PROMPT_VERSION}:{model}:{digest}"
    audit = {"task": AUDIT_TASK, "pair": payload["pair"], "input_hash": digest,
             "cache_key": key, "prompt_version": PROMPT_VERSION, "model": model,
             "cache_hit": False, "validated": False, "errors": [], "usage": {}}
    if llm is None and not (cache and key in cache):
        audit["errors"] = ["llm_unavailable"]
        return None, audit
    try:
        if cache is not None and key in cache:
            cached = dict(cache[key])
            if "value" in cached and isinstance(cached.get("value"), dict):
                value = dict(cached["value"])
                audit["usage"] = dict(cached.get("_meta", {}).get("usage", {}))
                audit["response_metadata"] = dict(
                    cached.get("_meta", {}).get("response_metadata", {}))
            else:
                value = cached
            audit["cache_hit"] = True
        else:
            response = llm.chat.completions.create(
                model=model, **chat_settings(model),
                response_format={"type": "json_schema", "json_schema": {
                    "name": RESPONSE_SCHEMA_NAME, "strict": True,
                    "schema": _response_schema(evidence_ids)}},
                messages=[{"role": "system", "content": (
                    load_prompt('step1_understand', 'judge_entity_identity_correspondence'))},
                    {"role": "user", "content": json.dumps(payload, ensure_ascii=False,
                                                             sort_keys=True)}])
            value = json.loads(response.choices[0].message.content)
            usage = getattr(response, "usage", None)
            audit["usage"] = {"input_tokens": getattr(usage, "prompt_tokens", 0) or 0,
                              "output_tokens": getattr(usage, "completion_tokens", 0) or 0}
            audit["response_metadata"] = {
                "response_id": getattr(response, "id", None),
                "created": getattr(response, "created", None),
                "system_fingerprint": getattr(response, "system_fingerprint", None)}
            if cache is not None:
                cache[key] = {"value": value, "_meta": {
                    "usage": dict(audit["usage"]),
                    "response_metadata": dict(audit["response_metadata"])}}
        value = identity_review_judgment(value)
        value.setdefault("row_grain_compatible", "UNKNOWN")
        allowed_values = {
            "row_grain_compatible": {"YES", "NO", "UNKNOWN"},
            "same_entity_type": {"YES", "NO", "UNKNOWN"},
            "identity_correspondence": {"YES", "NO", "UNKNOWN"},
            "explicit_identity_mapping": {"PRESENT", "ABSENT", "UNKNOWN"},
            "semantic_decision": {"SUPPORT", "CONTRADICT", "INSUFFICIENT"}}
        invalid_fields = [name for name, allowed in allowed_values.items()
                          if value.get(name) not in allowed]
        if invalid_fields or not isinstance(value.get("evidence_refs"), list) or not isinstance(
                value.get("reason"), str):
            audit["errors"] = ["invalid_structured_output:" + name
                               for name in invalid_fields] or ["invalid_structured_output:type"]
            audit["output"] = value
            return None, audit
        allowed_refs = set(evidence_ids or ["NO_EVIDENCE"])
        invalid = [item for item in value.get("evidence_refs", []) if item not in allowed_refs]
        if invalid:
            audit["errors"] = ["unknown_evidence_id:" + str(item) for item in invalid]
            audit["output"] = value
            return None, audit
        audit.update({"validated": True, "output": value})
        return value, audit
    except Exception as error:
        audit["errors"] = [type(error).__name__ + ": " + str(error)]
        return None, audit


def _deterministic_semantics(metadata: dict[str, Any]) -> dict[str, str]:
    """PURPOSE: Provide a safe fallback when no semantic model decision is available.
    INPUT: Pair-local documented text and conflict markers.
    OUTPUT: Conservative semantic fields; only authoritative identity wording yields support.
    """
    combined = metadata["left_text"] + " " + metadata["right_text"]
    if re.search(r'\b(?:independent|separate|distinct)\b[^.]{0,64}\b(?:namespace|identifier system|ID system)\b', combined, re.I):
        return {'same_entity_type': 'UNKNOWN', 'identity_correspondence': 'NO',
                'explicit_identity_mapping': 'ABSENT', 'semantic_decision': 'CONTRADICT',
                'reason': 'Independent identifier namespace does not imply a different business type.'}
    if _NON_IDENTITY.search(combined):
        return {"same_entity_type": "NO", "identity_correspondence": "NO",
                "explicit_identity_mapping": "ABSENT", "semantic_decision": "CONTRADICT",
                "reason": "Data Dictionary describes an independent object or history record."}
    if _EXPLICIT_IDENTITY.search(combined):
        return {"same_entity_type": "YES", "identity_correspondence": "YES",
                "explicit_identity_mapping": "ABSENT", "semantic_decision": "SUPPORT",
                "reason": "Data Dictionary explicitly describes the same business instance."}
    return {"same_entity_type": "UNKNOWN", "identity_correspondence": "UNKNOWN",
            "explicit_identity_mapping": "UNKNOWN", "semantic_decision": "INSUFFICIENT",
            "reason": "No authoritative instance-identity statement was supplied."}


def assess_key_identity_mappings(
        db_path: Path, table_keys: list[dict[str, Any]], dd: dict[str, Any], *,
        overlap_threshold: float = 0.30, llm: Any | None = None,
        model: str = DEFAULT_MODEL, cache: dict[str, Any] | None = None,
        requested_pairs: set[frozenset[str]] | None = None,
        semantic_overrides: dict[frozenset[str], dict[str, Any]] | None = None,
        key_profiles: list[dict[str, Any]] | None = None,
        unresolved_only: bool = False
        ) -> list[dict[str, Any]]:
    """PURPOSE: Generate, semantically judge and validate identity-mapping candidates between representative Keys.
    INPUT: Read-only DB, PK-backed Table + Key records, normalized DD, retrieval signal, optional
           LLM/cache and validated global-review pair requests/semantic decisions.
    OUTPUT: One audited MERGE, SEPARATE or UNRESOLVED relation per unique candidate pair.

    Candidate retrieval and merge validation are intentionally separate. A shared-PK FK is useful
    evidence but is not required. Partial extensions are allowed with a verified key correspondence; value overlap alone never authorizes a merge.
    """
    connection = connect_readonly(db_path)
    domains: dict[str, set[tuple[Any, ...]]] = {}
    valid_keys = {}
    result: list[dict[str, Any]] = []
    try:
        for left, right in combinations(sorted(table_keys, key=lambda item: item["id"]), 2):
            if not left.get("pk") or len(left["pk"]) != len(right.get("pk", [])):
                continue
            metadata = _pair_metadata(left, right, dd)
            for side_name, physical in (("left", left), ("right", right)):
                schema_types = _physical_key_types(connection, physical)
                for key in metadata[side_name]["pk"]:
                    key["schema_type"] = schema_types.get(key["column"], "")
                    key["affinity"] = _type_affinity(key["schema_type"] or key["type"])
            metadata["type_compatible"] = (
                [item["affinity"] for item in metadata["left"]["pk"]] ==
                [item["affinity"] for item in metadata["right"]["pk"]])
            for item in (left, right):
                if item["id"] not in domains:
                    domains[item["id"]] = _domain(connection, item["table"], item["pk"])
                    valid_keys[item['id']] = (len(domains[item['id']]) == connection.execute(
                            f"SELECT COUNT(*) FROM {quote_identifier(item['table'])}").fetchone()[0])
            left_domain, right_domain = domains[left["id"]], domains[right["id"]]
            intersection = left_domain & right_domain
            nonempty = bool(left_domain and right_domain)
            coverage_left = len(intersection) / len(left_domain) if left_domain else None
            coverage_right = len(intersection) / len(right_domain) if right_domain else None
            overlap_min = (len(intersection) / min(len(left_domain), len(right_domain))
                           if nonempty else None)
            shared_pk = _declared_shared_pk(connection, left, right)
            combined = metadata["left_text"] + " " + metadata["right_text"]
            pair_addressed = any(
                _EXPLICIT_IDENTITY.search(sentence) and re.search(
                    r"(?<![\w])" + re.escape(metadata[other]['table']) + r"(?![\w])", sentence, re.I)
                for side, other in (("left", "right"), ("right", "left"))
                for sentence in re.split(r"[.!?]", metadata[side]['table_definition']))
            documented_key_match = (metadata['same_key_names'] and all(
                _tokens(a['definition']) & _tokens(b['definition'])
                for a, b in zip(metadata['left']['pk'], metadata['right']['pk'])))
            explicit = (bool(_EXPLICIT_IDENTITY.search(combined)) and
                        bool(metadata["shared_tokens"]) and
                        (shared_pk or pair_addressed or documented_key_match))
            triggers = []
            if metadata["same_key_names"] or metadata["shared_tokens"]:
                triggers.append("pk_semantics_compatible")
            if overlap_min is not None and overlap_min >= overlap_threshold:
                triggers.append("key_containment_retrieval_threshold")
            if explicit:
                triggers.append("dd_explicit_same_instance")
            if shared_pk:
                triggers.append("declared_shared_pk_fk")
            pair_key = frozenset((left["id"], right["id"]))
            requested = pair_key in (requested_pairs or set())
            if not triggers and not requested:
                continue
            if requested and not triggers:
                triggers.append("global_review_proposal")
            collision_check = _identity_conflicts(connection, left, right)
            statistics = {"collision_check": collision_check, "left_distinct_count": len(left_domain),
                          "right_distinct_count": len(right_domain),
                          "intersection_count": len(intersection),
                          "overlap_min": overlap_min, "coverage_left": coverage_left,
                          "coverage_right": coverage_right,
                          "left_key_valid": valid_keys[left['id']],
                          "right_key_valid": valid_keys[right['id']],
                          "sampling": False, "observation_scope": "complete_non_null_pk_domains"}
            payload = {"pair": [left["id"], right["id"]], "left": metadata["left"],
                       "right": metadata["right"], "key_statistics": statistics,
                       "declared_shared_pk_fk": shared_pk, "candidate_triggers": triggers,
                       "provided_identity_mapping": None,
                       "key_generation": {"left": "unknown", "right": "unknown"},
                       "task": {"same_entity_type": "same Entity Type (business entity kind)",
                                "identity_correspondence": "equal tuples mean the same instance"}}
            if pair_key in (semantic_overrides or {}):
                judgment = identity_review_judgment(semantic_overrides[pair_key])
                audit = {"task": AUDIT_TASK, "pair": payload["pair"],
                         "source": "validated_global_review", "validated": True,
                         "cache_hit": True, "usage": {}, "errors": []}
            elif unresolved_only and (_deterministic_semantics(metadata)["semantic_decision"] == "CONTRADICT" or explicit):
                judgment = None
                audit = {"task":AUDIT_TASK, "pair":payload["pair"],
                         "source":"authoritative_dictionary", "actual_model_call":False,
                         "validated":True,"cache_hit":False,"usage":{},"errors":[]}
            else:
                judgment, audit = _semantic_judgment(
                    payload, metadata["evidence_ids"], llm, model, cache)
            semantic = judgment or _deterministic_semantics(metadata)
            if judgment is None and not explicit and semantic.get("semantic_decision") == "SUPPORT":
                semantic = {"same_entity_type": "UNKNOWN", "identity_correspondence": "UNKNOWN",
                            "explicit_identity_mapping": "UNKNOWN",
                            "semantic_decision": "INSUFFICIENT",
                            "reason": "Identity wording did not name a concept shared by both sides."}
            mapping_claimed = semantic.get("explicit_identity_mapping") == "PRESENT"
            executable_mapping = bool(payload["provided_identity_mapping"])
            correspondence_supported = semantic.get("identity_correspondence") == "YES"
            same_type = semantic.get("same_entity_type") == "YES"
            contradictory = (semantic.get("semantic_decision") == "CONTRADICT" or
                             semantic.get("same_entity_type") == "NO" or
                             semantic.get("identity_correspondence") == "NO")
            structural_valid = (metadata["type_compatible"] and len(left["pk"]) == len(right["pk"])
                                and valid_keys[left['id']] and valid_keys[right['id']])
            documented_key_semantics = all(
                bool(_tokens(a['definition'])) and _tokens(a['definition']) == _tokens(b['definition'])
                for a, b in zip(metadata['left']['pk'], metadata['right']['pk']))
            cited_correspondence_review = bool(judgment and judgment.get('evidence_refs') and
                correspondence_supported and same_type and documented_key_semantics)
            authoritative = explicit or cited_correspondence_review or semantic.get('correspondence_evidence_validated') is True
            # Evidence about THIS pair; `explicit` alone can come from either side's wording about a third Table.
            pair_specific_evidence = [name for name, present in (
                ("declared_shared_pk_fk", shared_pk), ("dd_names_counterpart_table", pair_addressed),
                ("cited_semantic_review", cited_correspondence_review),
                ("validated_global_review", semantic.get('correspondence_evidence_validated') is True)) if present]
            granularity_supported = (semantic.get('row_grain_compatible') != 'NO' and
                (explicit or cited_correspondence_review or semantic.get('row_grain_compatible') == 'YES'))
            # An equality map is the only executable mapping currently supported. Every key
            # on at least one side must be observed on the other; sparse extensions are valid.
            equality_verified = bool(intersection) and (left_domain <= right_domain or right_domain <= left_domain)
            reinforcing_keys = equality_verified and (authoritative or shared_pk)
            structural_valid = structural_valid and not collision_check['conflicts']
            statistics['collision_check'] = collision_check
            statistics['equality_mapping_verified'] = equality_verified
            statistics['unmatched_left_count'] = len(left_domain - right_domain)
            statistics['unmatched_right_count'] = len(right_domain - left_domain)
            if contradictory:
                decision, status, reason = "SEPARATE", "rejected", "semantic_contradiction"
            elif same_type and (correspondence_supported or executable_mapping) and structural_valid and granularity_supported and reinforcing_keys:
                decision, status, reason = "MERGE", "valid", "validated_shared_identity"
            else:
                decision, status, reason = "UNRESOLVED", "unresolved", "insufficient_identity_evidence"
            result.append({
                "id": f"OR:identity:{left['table']}:{right['table']}",
                "kind": "identity", "left": left["id"], "right": right["id"],
                "left_table": left["table"], "right_table": right["table"],
                "key_mapping": [[source, target] for source, target in zip(left["pk"], right["pk"])],
                "candidate_triggers": triggers, "pair_specific_evidence": pair_specific_evidence,
                "validation_status": status,
                "final_decision": decision, "reason_code": reason,
                "same_entity_type": semantic.get("same_entity_type", "UNKNOWN"),
                "identity_correspondence": semantic.get("identity_correspondence", "UNKNOWN"),
                "explicit_identity_mapping": semantic.get("explicit_identity_mapping", "UNKNOWN"),
                "semantic_judgment": semantic, "semantic_judge_audit": audit,
                "decision_reason": semantic.get("reason", ""),
                "validator": {"pk_arity_equal": True,
                              "type_compatible": metadata["type_compatible"],
                              "granularity_compatible": "supported" if granularity_supported else "unresolved",
                              "safe_normalization": "exact_tuple_equality",
                              "mapping_claimed_by_model": mapping_claimed,
                              "mapping_executable": equality_verified and structural_valid,
                              "key_correspondence_evidence": "documented" if authoritative else "unresolved",
                              "group_conflict": False},
                "identity_policy": "semantic_type_plus_observed_subset_mapping_v2",
                "statistics": statistics,
                "evidence": [
                    {"kind": "dd", "refs": metadata["evidence_ids"], "quote": combined.strip()},
                    {"kind": "stat", **statistics},
                    {"kind": "semantic", "name": "shared_tokens",
                     "value": metadata["shared_tokens"]},
                    {"kind": "schema", "name": "declared_shared_pk", "value": shared_pk},
                    {"kind": "rule", "id": 'R5.entity_type_identity', "outcome": decision}],
            })
        return result
    finally:
        connection.close()
