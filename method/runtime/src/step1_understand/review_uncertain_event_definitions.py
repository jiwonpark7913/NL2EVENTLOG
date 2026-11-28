"""Grounded Event Definition patches with explicit targets and atomic table-local application."""

from __future__ import annotations
from src.common.prompt_loader import load_prompt
from src.common.runtime_input_contract import POLICY_VERSION
from pathlib import Path
from typing import Any
import hashlib
import json
from src.step1_understand.eeg_configuration import DbuConfig
from src.eeg.evidence_graph_models import Table
from src.step1_understand.collect_event_review_evidence import representative_rows
PROMPT_VERSION = "dbu-review-v10-column-patches"
PATCH_PROMPT = load_prompt('step1_understand', 'review_event_definition_patch')
EXCLUDED_CARRIER_REASONS = {"identifier_key_without_activity_code_evidence", "documented_not_activity"}
RETRY_PROMPT_VERSION = "dbu-review-retry-v1-validation-feedback"
RETRY_PROMPT = load_prompt('step1_understand', 'correct_event_definition_patch')
from src.common.llm_usage import chat_settings


def _request_patch(llm: Any, config: DbuConfig, schema: dict[str, Any],
                   messages: list[dict[str, str]]) -> tuple[Any, dict[str, int]]:
    """PURPOSE: Send one strict-schema review request. INPUT: Client, config, schema, chat messages.
    OUTPUT: (parsed JSON, token usage); raises on refusal or invalid JSON.
    """
    response = llm.chat.completions.create(model=config.model, **chat_settings(config.model),
        response_format={'type': 'json_schema', 'json_schema': {
            'name': 'database_understanding_repair', 'strict': True, 'schema': schema}},
        messages=messages)
    message = response.choices[0].message
    if getattr(message, 'refusal', None):
        raise ValueError('model_refusal')
    usage = getattr(response, 'usage', None)
    return json.loads(message.content), {'input_tokens': getattr(usage, 'prompt_tokens', 0) or 0,
                                         'output_tokens': getattr(usage, 'completion_tokens', 0) or 0}


def operation_diagnostics(value: Any, payload: dict[str, Any]) -> list[dict[str, Any]]:
    """PURPOSE: Explain which operations of a rejected patch fail on their own (feedback only).
    INPUT: Structurally valid patch JSON and its exact review context.
    OUTPUT: [{index, operation, target, errors}]. Passing alone never implies the whole patch applies.
    """
    from src.step1_understand.validate_event_review_patches import validate_patch
    result = []
    for index, operation in enumerate(value.get('operations', []) if isinstance(value, dict) else []):
        single = {**value, 'operations': [operation], 'time_role_revisions': []}
        result.append({'index': index, 'operation': operation.get('operation'),
                       'target': operation.get('target_definition_id'),
                       'errors': validate_patch(single, payload)})
    return result


def _local_evidence(table: Table, dd: dict[str, Any]) -> dict[str, str]:
    """PURPOSE: Collect citable public statements for one table only.
    INPUT: Physical table and normalized DD. OUTPUT: {statement ID: verbatim text}.
    Table/column definitions use their DD IDs; code-domain statements keep their semantic IDs.
    """
    names = {column.name for column in table.columns}
    evidence = {}
    for item in dd.get("tables", []):
        if item["table"] == table.name and item.get("definition"):
            evidence[item["id"]] = item["definition"]
    for item in dd.get("columns", []):
        if item["table"] == table.name and item["column"] in names and item.get("definition"):
            evidence[item["id"]] = item["definition"]
    for item in dd.get("semantic_statements", []):
        if item.get("table") == table.name and item.get("field") in {"value_domain", "code_meaning",
                                                                       "row_grain"}:
            evidence[item["id"]] = item["text"]
    return evidence


def _carrier_column_ids(table: Table, timestamps: list[dict[str, Any]]) -> list[str]:
    """PURPOSE: List columns a reviewer may name as carrier (non-key, non-temporal).
    INPUT: Table and its timestamp units. OUTPUT: Sorted physical column IDs.
    Rank signals are context only; none of them is a necessary condition (paper §4.1.2).
    """
    excluded = set(table.primary_key)
    for unit in timestamps:
        excluded.update(unit.get("columns", []))
    return sorted(column.id for column in table.columns if column.name not in excluded)


def _compact_unit(unit: dict[str, Any]) -> dict[str, Any]:
    """PURPOSE: Minimal timestamp context for review. INPUT: Unit. OUTPUT: Small mapping."""
    return {key: unit.get(key) for key in ("ts_id", "columns", "json_path", "semantic_role",
                                           "role_status", "detected_format", "null_ratio")}


def build_review_payload(table: Table, state: dict[str, Any], trace: dict[str, Any],
                         profiles: dict[str, Any], timestamps: list[dict[str, Any]],
                         dd: dict[str, Any], bindings: list[dict[str, Any]], *,
                         neighbors: list[dict[str, Any]] | None, review_reasons: list[str],
                         uncertainties: list[dict[str, Any]], db_path: Path | None) -> dict[str, Any]:
    """PURPOSE: Assemble the table-local review input (paper: definition, columns, value
    dictionaries, ≤8 rows, one-hop FK neighbours) plus the current interpretations and why each
    is uncertain.
    INPUT: Table evidence, current bindings of this table and explicit uncertainty records.
    OUTPUT: JSON-safe payload without digests or database-wide prose.
    """
    local_units = [unit for unit in timestamps if unit["ts_id"] in state["ts_ids"]]
    evidence = _local_evidence(table, dd)
    temporal = {name for unit in local_units for name in unit.get("columns", [])}
    columns = []
    for column in table.columns:
        profile = profiles[table.name]["columns"][column.name]
        columns.append({"id": column.id, "name": column.name, "type": column.declared_type,
                        "distinct_count": profile["distinct_count"],
                        **({"top_values": [item["value"] for item in profile["frequent_values"][:8]]}
                           if column.name not in temporal else {})})
    current = [{"id": b["id"], "kind": b["alpha"]["kind"], "column": b["alpha"].get("column"),
                "value": b["alpha"].get("value"), "timestamp_unit_id": b.get("ts_id"),
                "activity_name": b.get("activity_label", b["alpha"].get("name")),
                "status": b.get("interpretation_status", "unresolved")}
               for b in bindings if b["table"] == table.name]
    candidate_names = [column.name for column in table.columns
                       if column.id in set(_carrier_column_ids(table, local_units))]
    return {"table": {"id": table.id, "name": table.name},
            "statements": [{"id": key, "text": text} for key, text in sorted(evidence.items())],
            "columns": columns, "timestamps": [_compact_unit(unit) for unit in local_units],
            "current_interpretations": current, "uncertainties": uncertainties,
            "review_reasons": review_reasons, "direct_fk_neighbors": neighbors or [],
            "representative_rows": representative_rows(
                db_path, table, candidate_names, sorted(temporal)) if db_path else []}


def repair_table(table: Table, state: dict[str, Any], trace: dict[str, Any], profiles: dict[str, Any],
                 timestamps: list[dict[str, Any]], dd: dict[str, Any], config: DbuConfig,
                 llm: Any, cache: dict[str, Any] | None, *,
                 bindings: list[dict[str, Any]] | None = None,
                 neighbors: list[dict[str, Any]] | None = None,
                 review_reasons: list[str] | None = None,
                 uncertainties: list[dict[str, Any]] | None = None,
                 database_digest: str | None = None,
                 db_path: Path | None = None) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """PURPOSE: Review explicit edits using one structure/evidence validator for API and cache.
    INPUT: Table-local public evidence, existing definitions, SDK/cache and optional read-only DB.
    OUTPUT: Validated patch/context and audit, or None with categorized errors; no graph mutation.
    """
    from copy import deepcopy
    from src.step1_understand.validate_event_review_patches import response_schema, validate_patch, definition_conflicts
    payload = build_review_payload(table, state, trace, profiles, timestamps, dd, bindings or [],
        neighbors=neighbors, review_reasons=review_reasons or [],
        uncertainties=uncertainties or [], db_path=db_path)
    local_times = [deepcopy(t) for t in timestamps if t['ts_id'] in state['ts_ids']]
    payload['timestamps'] = local_times
    payload['existing_definitions'] = [deepcopy(b) for b in bindings or [] if b['table'] == table.name]
    payload['existing_conflicts'] = definition_conflicts(payload['existing_definitions'],
        {b['id'] for b in payload['existing_definitions']})
    records = {r['id']: r for r in [*dd.get('columns', []), *dd.get('tables', []),
                                  *dd.get('semantic_statements', [])]}
    payload['evidence'] = [{'id': e['id'], 'text': e['text'],
                            'table': records.get(e['id'], {}).get('table'),
                            'column': records.get(e['id'], {}).get('column')}
                           for e in payload.pop('statements')]
    payload['carrier_values'] = {}
    payload['non_carrier_context'] = []
    for item in trace.get('activity_evaluations', []):
        if item['accepted']:
            continue
        payload['non_carrier_context'].append({
            'column_id': item['column_id'], 'role': item.get('admission', item['evidence_status']),
            'excluded_from_carriers_because': item['rejection_reasons'],
            'observed_values': [r['value'] for r in profiles[table.name]['columns'][item['column']]['frequent_values'][:5]],
        })
    carrier_clocks = {r['ts_id'] for r in trace.get('carrier_timestamp_matrix', [])
                      if r['status'] in {'supported', 'unresolved', 'non_occurrence'}}
    payload['protected_definition_ids'] = [b['id'] for b in payload['existing_definitions']
        if b['alpha']['kind'] == 'value' or (b['ts_id'] in carrier_clocks
        and b['interpretation_status'] == 'supported')]
    payload['protected_timestamp_ids'] = sorted(carrier_clocks)
    schema = response_schema()
    digest = hashlib.sha256(json.dumps([payload, schema, PATCH_PROMPT], ensure_ascii=False,
                                       sort_keys=True, default=str).encode()).hexdigest()
    key = f'{POLICY_VERSION}:{PROMPT_VERSION}:{config.model}:{database_digest}:{config.digest()}:{digest}'
    audit = {'table': table.name, 'input_hash': digest, 'cache_key': key,
             'prompt_version': PROMPT_VERSION, 'model': config.model, 'cache_hit': False,
             'validated': False, 'errors': [], 'usage': {}, 'input': payload}
    try:
        if cache is not None and key in cache:
            value = deepcopy(cache[key])
            audit['cache_hit'] = True
        else:
            if llm is None:
                return None, {**audit, 'errors': ['llm_unavailable']}
            messages = [{'role': 'system', 'content': PATCH_PROMPT},
                        {'role': 'user', 'content': json.dumps(payload, ensure_ascii=False,
                                                             sort_keys=True, default=str)}]
            value, audit['usage'] = _request_patch(llm, config, schema, messages)
        errors = validate_patch(value, payload)
        audit['attempts'] = [{'attempt': 0, 'output': deepcopy(value), 'errors': errors}]
        retries = 0 if audit['cache_hit'] else config.review_validation_retries
        while errors and retries > 0 and llm is not None:
            # Bounded recovery: the model sees why the patch was rejected; acceptance criteria are unchanged.
            retries -= 1
            feedback = {'validation_errors': errors, 'per_operation_diagnostics': operation_diagnostics(value, payload)}
            messages = [*messages, {'role': 'assistant', 'content': json.dumps(value, ensure_ascii=False, sort_keys=True)},
                        {'role': 'user', 'content': RETRY_PROMPT + '\n<validation_feedback>\n' +
                         json.dumps(feedback, ensure_ascii=False, sort_keys=True) + '\n</validation_feedback>'}]
            try:
                value, usage = _request_patch(llm, config, schema, messages)
            except Exception as error:  # a failed retry keeps the original rejection and definitions
                audit['attempts'].append({'attempt': len(audit['attempts']), 'prompt_version': RETRY_PROMPT_VERSION,
                                          'errors': [type(error).__name__ + ': ' + str(error)], 'feedback': feedback})
                break
            errors = validate_patch(value, payload)
            audit['attempts'].append({'attempt': len(audit['attempts']), 'prompt_version': RETRY_PROMPT_VERSION,
                                      'feedback': feedback, 'output': deepcopy(value), 'errors': errors, 'usage': usage})
        audit.update(output=value, validated=not errors, errors=list(errors),  # own list: application errors are appended later
                     recovered_by_retry=not errors and len(audit['attempts']) > 1)
        if errors:
            return None, audit
        if cache is not None and not audit['recovered_by_retry']:
            cache[key] = deepcopy(value)  # a retried answer belongs to a different request; never cache it as this one
        return {'patch': value, 'context': payload, 'audit': audit}, audit
    except Exception as error:
        audit['errors'] = [type(error).__name__ + ': ' + str(error)]
        return None, audit


def apply_review_decision(bindings: list[dict[str, Any]], table: Table, state: dict[str, Any],
                          decision: dict[str, Any], timestamps: list[dict[str, Any]],
                          dd: dict[str, Any], db_path: Path) -> tuple[list[dict[str, Any]], str]:
    """PURPOSE: Apply explicit operations atomically and preserve every unaddressed definition.
    INPUT: Global bindings, validated patch/context, actual units/DD and read-only database path.
    OUTPUT: New bindings and review status; audit receives changes/conflicts or application errors.
    """
    from src.step1_understand.validate_event_review_patches import apply_patch
    patch = decision['patch']
    if patch['confidence'] != 'high':
        return bindings, 'unresolved_low_confidence'
    context = decision['context']
    protected = set(context.get('protected_definition_ids', []))
    protected_times = set(context.get('protected_timestamp_ids', []))
    changes_allowed = [op for op in patch['operations']
                       if op.get('target_definition_id') not in protected
                       and op.get('definition', {}).get('kind') != 'carrier_value'
                       and op.get('definition', {}).get('timestamp_unit_id') not in protected_times]
    revisions_allowed = [r for r in patch['time_role_revisions']
                         if r['timestamp_unit_id'] not in protected_times]
    ignored = [op for op in patch['operations'] if op not in changes_allowed]
    ignored_times = [r for r in patch['time_role_revisions'] if r not in revisions_allowed]
    patch = {**patch, 'operations': changes_allowed, 'time_role_revisions': revisions_allowed}
    proposed, errors, changes = apply_patch(db_path, table, bindings, patch, context, timestamps, dd)
    changes['ignored_protected_operations'] = ignored
    changes['ignored_protected_time_role_revisions'] = ignored_times
    changes['applied'] = not errors
    decision['audit']['application'] = changes
    if errors:
        decision['audit']['errors'].extend(errors)
        return bindings, 'unresolved_invalid_binding_bundle'
    return proposed, 'applied' if patch['operations'] or patch['time_role_revisions'] else 'confirmed_unchanged'
