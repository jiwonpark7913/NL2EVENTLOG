"""Strict, table-local Event Definition patches and grounded citation validation."""

from __future__ import annotations
from copy import deepcopy
from itertools import combinations
from typing import Any
import re
from jsonschema import Draft202012Validator
from src.step1_understand.interpret_event_definitions import _activity_provenance, _null_evidence
from src.common.event_clock import NON_OCCURRENCE_ROLES, documented_message_receipt_clock, documented_represented_clock
from src.common.graph_identifiers import event_definition_id
from src.step1_understand.detect_and_normalize_timestamps import occurrence_time_policy
from src.common.database_io import connect_readonly


def response_schema() -> dict[str, Any]:
    """PURPOSE: Define one OpenAI strict-output-compatible patch schema for every response source.
    INPUT: None; scoped physical IDs and evidence are checked locally against the supplied payload.
    OUTPUT: Root object with nested anyOf, all fields required and no additional properties.
    """
    citation = {'type': 'object', 'additionalProperties': False,
                'properties': {'evidence_id': {'type': 'string'}, 'quote': {'type': 'string'}},
                'required': ['evidence_id', 'quote']}
    citations = {'type': 'array', 'items': citation}
    definitions = []
    for kind in ('carrier_value', 'time_column'):
        fields = {'kind': {'type': 'string', 'enum': [kind]},
                  'carrier_column_id': {'type': 'string'} if kind == 'carrier_value' else {'type': 'null'},
                  'value': {'type': 'string'} if kind == 'carrier_value' else {'type': 'null'},
                  'activity_name': {'type': 'string'},
                  'timestamp_unit_id': {'type': 'string'},
                  'event_kind': {'type': 'string', 'enum': ['business', 'planned', 'technical']},
                  'activity_citations': citations, 'time_citations': citations}
        definitions.append({'type': 'object', 'additionalProperties': False,
                            'properties': fields, 'required': list(fields)})
    operations = []
    for operation in ('add', 'update', 'delete'):
        fields = {'operation': {'type': 'string', 'enum': [operation]}}
        if operation != 'add':
            fields['target_definition_id'] = {'type': 'string'}
        if operation != 'delete':
            fields['definition'] = {'anyOf': definitions}
        else:
            fields['citations'] = citations
        operations.append({'type': 'object', 'additionalProperties': False,
                           'properties': fields, 'required': list(fields)})
    revision_fields = {'timestamp_unit_id': {'type': 'string'},
                       'role': {'type': 'string', 'enum': ['business_occurrence', 'effective_time',
                           'recorded_time', 'scheduled_time', 'estimated_time', 'non_event_time',
                           'ingestion_time', 'unknown']},
                       'citations': citations}
    revision = {'type': 'object', 'additionalProperties': False, 'properties': revision_fields,
                'required': list(revision_fields)}
    return {'type': 'object', 'additionalProperties': False,
            'properties': {'time_role_revisions': {'type': 'array', 'items': revision}, 'confidence': {'type': 'string', 'enum': ['high', 'low']},
                           'operations': {'type': 'array', 'items': {'anyOf': operations}}},
            'required': ['confidence', 'operations', 'time_role_revisions']}


def citation_errors(citations, evidence, *, allowed_ids=None) -> list[str]:
    """PURPOSE: Require exact nonempty quotes from evidence actually supplied to this review.
    INPUT: Structurally validated citations, ID/text map, optional relevant-source ID allowlist.
    OUTPUT: Stable evidence error codes; never accepts a quote from an unprovided source.
    """
    errors = []
    if not citations:
        errors.append('evidence:missing_citation')
    for citation in citations:
        identifier, quote = citation['evidence_id'], citation['quote']
        if identifier not in evidence:
            errors.append('evidence:unknown_evidence_id')
        elif not quote.strip() or quote not in evidence[identifier]:
            errors.append('evidence:quote_not_verbatim')
        if allowed_ids is not None and identifier not in allowed_ids:
            errors.append('evidence:citation_outside_definition_scope')
    return errors


def activity_tokens(text):
    """PURPOSE: Compare activity-specific words when a reviewer chooses among competing clocks.
    INPUT: Human activity name or exact clock quote. OUTPUT: Conservative inflection-normalized words.
    Generic clock/record wording cannot justify a competing timestamp.
    """
    generic = {'actual', 'utc', 'time', 'date', 'timestamp', 'occurrence', 'event', 'activity',
               'when', 'the', 'was', 'were', 'for', 'this', 'that', 'row', 'record', 'recorded', 'of', 'at'}
    phases = {'completion': 'complete', 'completed': 'complete', 'complete': 'complete',
              'finish': 'complete', 'finished': 'complete', 'finishing': 'complete',
              'start': 'start', 'started': 'start', 'starting': 'start',
              'begin': 'start', 'began': 'start', 'beginning': 'start'}
    return {phases.get(w, re.sub(r'(?:ing|ed|s)$', '', w)) for w in re.findall(r'[a-z]+', text.casefold())
            if len(w) > 2 and w not in generic}


def revised_time_units(revisions, context):
    """PURPOSE: Stage cited time-role corrections without mutating live units or bypassing clock evidence.
    INPUT: Structurally valid revisions and exact supplied review context.
    OUTPUT: Copied unit map and categorized errors; contradictory/scoped-invalid revisions never apply.
    """
    from src.step1_understand.detect_and_normalize_timestamps import timestamp_semantic_role
    units = {t['ts_id']: deepcopy(t) for t in context['timestamps']}
    evidence = {e['id']: e for e in context['evidence']}
    errors, seen = [], set()
    for revision in revisions:
        identifier = revision['timestamp_unit_id']
        unit = units.get(identifier)
        if unit is None:
            errors.append('reference:unknown_timestamp_unit')
            continue
        if identifier in seen:
            errors.append('conflict:duplicate_time_role_revision')
        seen.add(identifier)
        if (unit.get('role_status')=='supported' and unit.get('semantic_role') in NON_OCCURRENCE_ROLES
                and revision['role'] != unit['semantic_role']):
            errors.append('semantic:cannot_change_documented_non_occurrence_time')
            continue
        allowed = {key for key, e in evidence.items() if e.get('table') == context['table']['name'] and
                   e.get('column') in unit.get('columns', [])}
        failures = citation_errors(revision['citations'], {key: e['text'] for key, e in evidence.items()},
                                   allowed_ids=allowed)
        errors.extend(failures)
        if failures:
            continue
        text = ' '.join(c['quote'] for c in revision['citations'])
        inferred = timestamp_semantic_role(context['table']['name'], unit['columns'], {'definition': text})
        # The model can ground ordinary occurrence prose, but cannot turn explicit plans/ETL into occurrences.
        if revision['role'] == 'business_occurrence' and (inferred['semantic_role'] in
                NON_OCCURRENCE_ROLES or
                inferred['semantic_role'] == 'unknown' and not re.search(r'\bwhen\b', text, re.I)):
            errors.append('semantic:unsupported_time_role_revision')
        elif revision['role'] not in {'business_occurrence', 'unknown'} and inferred['semantic_role'] != revision['role']:
            errors.append('semantic:unsupported_time_role_revision')
        unit.update(semantic_role=revision['role'],
                    role_status='unknown' if revision['role'] == 'unknown' else 'supported',
                    role_evidence=[{'source': 'dictionary_description', 'id': c['evidence_id'],
                                    'detail': c['quote']} for c in revision['citations']],
                    confidence_basis='cited_review')
    return units, errors


def _message_clock_roles(context):
    """PURPOSE: Identify public clocks carrying event times and independent receipt times.
    INPUT: Table-local review evidence and TimestampUnits. OUTPUT: Two sets of TimestampUnit IDs.
    A named independent event_activity can coexist with a represented time on the same column.
    """
    represented, receipts = set(), set()
    for unit in context['timestamps']:
        if unit.get('json_path') or len(unit.get('columns', [])) != 1:
            continue
        definitions = [item['text'] for item in context['evidence']
                       if item.get('table') == context['table']['name']
                       and item.get('column') == unit['columns'][0]]
        if any(documented_represented_clock(text) for text in definitions):
            if not unit.get('documented_event_activity') and not occurrence_time_policy(unit)['eligible']:
                represented.add(unit['ts_id'])
        if (occurrence_time_policy(unit)['eligible']
                and any(documented_message_receipt_clock(text) for text in definitions)):
            receipts.add(unit['ts_id'])
    return represented, receipts if represented else set()


def validate_patch(value, context) -> list[str]:
    """PURPOSE: Apply identical structure, reference and citation checks to API/cache/local patches.
    INPUT: Untrusted JSON and the exact table-local review context supplied to the model.
    OUTPUT: Categorized error codes; invalid structure stops semantic validation safely.
    """
    errors = ['structure:' + '/'.join(map(str, e.absolute_path)) + ':' + e.validator
              for e in Draft202012Validator(response_schema()).iter_errors(value)]
    if errors:
        return sorted(set(errors))
    existing = {b['id']: b for b in context['existing_definitions']}
    times, time_errors = revised_time_units(value['time_role_revisions'], context)
    errors.extend(time_errors)
    evidence = {e['id']: e['text'] for e in context['evidence']}
    scopes = {e['id']: e for e in context['evidence']}
    represented_times, receipt_times = _message_clock_roles(context)
    for revision in value['time_role_revisions']:
        if revision['timestamp_unit_id'] in receipt_times and revision['role'] != 'business_occurrence':
            errors.append('semantic:documented_receipt_occurrence_required')
    targets = set()
    for operation in value['operations']:
        target = operation.get('target_definition_id')
        if target is not None:
            if target not in existing:
                errors.append('reference:unknown_target_definition')
            if target in targets:
                errors.append('conflict:duplicate_patch_target')
            targets.add(target)
        original = existing.get(target, {})
        if original.get('ts_id') in receipt_times and original.get('alpha', {}).get('kind') == 'column':
            replacement = operation.get('definition', {})
            if (replacement.get('kind') != 'time_column'
                    or replacement.get('timestamp_unit_id') != original['ts_id']):
                errors.append('semantic:documented_receipt_occurrence_required')
        if operation['operation'] == 'delete':
            original_columns = set(next((t.get('columns', []) for t in times.values()
                                         if t['ts_id'] == original.get('ts_id')), []))
            if original.get('alpha', {}).get('column'):
                original_columns.add(original['alpha']['column'])
            errors.extend(citation_errors(operation['citations'], evidence,
                allowed_ids={key for key, e in scopes.items() if e.get('table') == context['table']['name']
                             and (not e.get('column') or e['column'] in original_columns)}))
            continue
        definition = operation['definition']
        unit = times.get(definition['timestamp_unit_id'])
        if unit is None:
            errors.append('reference:unknown_timestamp_unit')
        if definition['kind'] == 'time_column' and definition['timestamp_unit_id'] in represented_times:
            errors.append('semantic:represented_clock_requires_activity_selector')
        from src.step1_understand.resolve_activity_meanings import activity_label_issue
        issue = activity_label_issue(definition['activity_name'], identifier_values=[
            v for item in context.get('non_carrier_context', []) for v in item.get('observed_values', [])])
        if issue == 'documentation_or_value_list':
            errors.append('semantic:non_atomic_activity_name')
        elif issue:
            errors.append('semantic:activity_name_' + issue)
        column = definition['carrier_column_id']
        if definition['kind'] == 'carrier_value':
            if column not in context['carrier_values']:
                errors.append('reference:unknown_carrier_column')
            elif definition['value'] not in context['carrier_values'][column]:
                errors.append('reference:unobserved_carrier_value')
        activity_ids = {key for key, e in scopes.items() if e.get('table') == context['table']['name'] and
                        (not e.get('column') or e['column'] in (
                            ([c['name'] for c in context.get('columns', []) if c['id'] == column] or
                             ([column.split('.', 1)[1]] if '.' in column else []))
                            if column else (unit or {}).get('columns', [])))}
        time_ids = {key for key, e in scopes.items() if e.get('table') == context['table']['name'] and
                    e.get('column') in (unit or {}).get('columns', [])}
        errors.extend(citation_errors(definition['activity_citations'], evidence, allowed_ids=activity_ids))
        errors.extend(citation_errors(definition['time_citations'], evidence, allowed_ids=time_ids))
        if definition['kind'] == 'carrier_value':
            raw_pattern = r'(?<!\w)' + re.escape(definition['value']) + r'(?!\w)'
            if not any(re.search(raw_pattern, c['quote']) or
                       c['evidence_id'].endswith(':' + definition['value'])
                       for c in definition['activity_citations']):
                errors.append('evidence:activity_citation_does_not_link_value')
        eligible_times = [t for t in times.values() if t.get('semantic_role') not in
                          NON_OCCURRENCE_ROLES]
        if unit and len(eligible_times) > 1:
            label_tokens = activity_tokens(definition['activity_name'])
            if column:
                label_tokens |= activity_tokens(column.split('.', 1)[-1])
            clock_tokens = activity_tokens(' '.join(c['quote'] for c in definition['time_citations']))
            other_tokens = [activity_tokens(' '.join(e['text'] for e in scopes.values()
                if e.get('table') == context['table']['name'] and e.get('column') in t.get('columns', [])))
                for t in eligible_times if t['ts_id'] != unit['ts_id']]
            common = set().union(*other_tokens)
            if not label_tokens.intersection(clock_tokens - common):
                errors.append('semantic:unsupported_competing_timestamp_choice')
        if unit:
            role = unit.get('semantic_role')
            kind = definition['event_kind']
            if kind == 'business' and not occurrence_time_policy(unit)['eligible']:
                errors.append('semantic:unsupported_occurrence_time')
            if kind == 'planned' and (role not in {'scheduled_time','estimated_time'} or unit.get('role_status') != 'supported'):
                errors.append('semantic:unsupported_planned_time')
            if kind == 'technical' and (role not in {'ingestion_time', 'recorded_time'} or
                                        unit.get('role_status') != 'supported'):
                errors.append('semantic:unsupported_technical_time')
    return sorted(set(errors))


def patch_binding(connection, table, definition, unit, indexes, *, previous=None):
    """PURPOSE: Materialize a grounded definition with physical time provenance and no stale proofs.
    INPUT: Read-only connection, schema, validated definition/unit/DD indexes and replaced binding.
    OUTPUT: Fresh binding for downstream meaning/time/occurrence/attribution revalidation.
    """
    carrier = definition['kind'] == 'carrier_value'
    column = next((c.name for c in table.columns if c.id == definition['carrier_column_id']), None) if carrier else None
    raw_value = None
    if carrier:
        from src.common.database_io import quote_identifier as qi
        matches = [row[0] for row in connection.execute(
            f'SELECT DISTINCT {qi(column)} FROM {qi(table.name)} WHERE {qi(column)} IS NOT NULL')
            if str(row[0]) == definition['value']]
        if len(matches) != 1:
            raise ValueError('ambiguous_or_unobserved_carrier_value')
        raw_value = matches[0]
    alpha = {'kind': 'value' if carrier else 'column', 'column': column,
             'value': raw_value, 'name': definition['activity_name']}
    citations = [*definition['activity_citations'], *definition['time_citations']]
    return {'id': event_definition_id(table.name, alpha, unit['ts_id']), 'table': table.name,
            'alpha': alpha, 'ts_id': unit['ts_id'], 'paths': [], 'provenance': 'llm_repair',
            'encoding_interpretation': 'row' if carrier else 'column',
            'interpretation_status': 'unresolved', 'event_kind': definition['event_kind'],
            'review_definition': deepcopy(definition),
            'replaces_definition_id': previous['id'] if previous else None,
            **_activity_provenance(table.name, alpha, unit, 'grounded_definition_review'),
            **_null_evidence(connection, table.name, unit, indexes,
                             carrier_column=column, carrier_value=raw_value),
            **({'timestamp_pairing': {'selected': unit['ts_id'], 'status': 'supported_by_review',
                                      'evidence': deepcopy(definition['time_citations'])}} if carrier else {}),
            'evidence': [{'kind': 'dd', 'ref': c['evidence_id'], 'quote': c['quote']} for c in citations]}


def validate_materialized_time(connection, binding, unit):
    """PURPOSE: Execute the actual normalization expression on the repaired definition's source rows.
    INPUT: Read-only connection, materialized definition and actual TimestampUnit.
    OUTPUT: Counts and errors; non-NULL source values that normalize to NULL reject the patch.
    """
    from src.step1_understand.validate_event_attribution_paths import _binding_predicate
    from src.common.database_io import quote_identifier
    from src.step1_understand.detect_and_normalize_timestamps import normalization_sql
    predicate, parameters = _binding_predicate(binding)
    expression = normalization_sql(unit)
    try:
        total, parsed = connection.execute(
            f'SELECT COUNT(*), COALESCE(SUM(({expression}) IS NOT NULL), 0) '
            f'FROM {quote_identifier(binding["table"])} s0 WHERE {predicate}', parameters).fetchone()
    except Exception as error:
        return {'status': 'fail', 'error': type(error).__name__}, ['time:normalization_sql_failed']
    receipt = {'status': 'pass' if total and parsed == total else 'unknown' if not total else 'fail',
               'source_rows': total, 'normalized_rows': parsed, 'invalid_rows': total - parsed}
    return receipt, ['time:normalization_failed'] if total > parsed else []


def definition_conflicts(bindings, touched_ids) -> list[dict[str, Any]]:
    """PURPOSE: Detect duplicate occurrences and unresolved mutually exclusive interpretations.
    INPUT: Proposed final table definitions and IDs changed by this patch.
    OUTPUT: Pairwise conflict records; untouched pre-existing ambiguities do not reject unrelated edits.
    """
    conflicts = []
    for left, right in combinations(bindings, 2):
        if not ({left['id'], right['id']} & touched_ids):
            continue
        a, b = left['alpha'], right['alpha']
        av, bv = a['kind'] == 'value', b['kind'] == 'value'
        # Different values of one carrier select disjoint occurrences.
        if av and bv and a['column'] == b['column'] and (type(a['value']), a['value']) != (type(b['value']), b['value']):
            continue
        same_selector = (not av and not bv) or (av and bv and a['column'] == b['column'] and
                                                a['value'] == b['value'])
        same_time = left['ts_id'] == right['ts_id']
        same_label = re.sub(r'\W+', '', a['name']).casefold() == re.sub(r'\W+', '', b['name']).casefold()
        if same_time:
            reason = 'overlapping_occurrence_alternatives'
        elif same_selector and (av or same_label):
            reason = 'unsupported_competing_timestamps'
        else:
            continue
        conflicts.append({'definition_ids': sorted([left['id'], right['id']]), 'reason': reason})
    return conflicts


def apply_patch(db_path, table, bindings, patch, context, timestamps, dd):
    """PURPOSE: Apply explicit definition operations atomically while preserving every unspecified ID.
    INPUT: Read-only DB, table, global bindings, patch/context, actual time inventory and normalized DD.
    OUTPUT: (proposed global bindings, errors, change audit); any error leaves the caller's graph untouched.
    """
    from contextlib import closing
    from pathlib import Path
    import sqlite3
    from src.common.data_dictionary import dictionary_indexes
    from src.step1_understand.collect_event_review_evidence import validate_rebuilt_bindings

    errors = validate_patch(patch, context)
    audit = {'added': [], 'updated': [], 'deleted': [], 'conflicts': []}
    if errors or not patch['operations'] and not patch['time_role_revisions']:
        return bindings, errors, audit
    local = {b['id']: deepcopy(b) for b in bindings if b['table'] == table.name}
    times, _ = revised_time_units(patch['time_role_revisions'], context)
    originals = dict(local)
    revised_ids = {r['timestamp_unit_id'] for r in patch['time_role_revisions']}
    touched = {b['id'] for b in local.values() if b['ts_id'] in revised_ids}
    # Remove only explicitly targeted originals before generating additions; order is immaterial.
    for operation in patch['operations']:
        if operation['operation'] != 'add':
            local.pop(operation['target_definition_id'])
    with closing(connect_readonly(db_path)) as connection:
        for operation in patch['operations']:
            target = operation.get('target_definition_id')
            if operation['operation'] == 'delete':
                audit['deleted'].append(target)
                continue
            definition = operation['definition']
            try:
                item = patch_binding(connection, table, definition, times[definition['timestamp_unit_id']],
                                     dictionary_indexes(dd), previous=originals.get(target))
            except ValueError as error:
                errors.append('reference:' + str(error))
                continue
            receipt, time_errors = validate_materialized_time(connection, item, times[item['ts_id']])
            item['review_time_validation'] = receipt
            errors.extend(time_errors)
            if item['id'] in local:
                errors.append('conflict:existing_definition_requires_explicit_update')
                continue
            local[item['id']] = item
            touched.add(item['id'])
            audit['updated' if target else 'added'].append({'before': target, 'after': item['id']})
        for item in local.values():
            if item['id'] in touched and 'review_time_validation' not in item:
                receipt, time_errors = validate_materialized_time(connection, item, times[item['ts_id']])
                item['review_time_validation'] = receipt
                errors.extend(time_errors)
    generated = [b for b in local.values() if b['id'] in touched]
    if generated:
        errors.extend(validate_rebuilt_bindings(db_path, table, generated, list(times.values())))
    audit['conflicts'] = definition_conflicts(list(local.values()), touched)
    errors.extend('conflict:' + c['reason'] for c in audit['conflicts'])
    if errors:
        return bindings, sorted(set(errors)), audit
    for revision in patch['time_role_revisions']:
        for unit in timestamps:
            if unit['ts_id'] == revision['timestamp_unit_id']:
                unit.update(times[unit['ts_id']])
    audit['time_role_revisions'] = deepcopy(patch['time_role_revisions'])
    return [b for b in bindings if b['table'] != table.name] + sorted(local.values(), key=lambda b: b['id']), [], audit


def reviewed_meaning(binding, timestamp, dd):
    """PURPOSE: Revalidate grounded review semantics against current DD and the actual selected clock.
    INPUT: Materialized binding, current TimestampUnit and normalized public DD.
    OUTPUT: Valid review definition or None; cached support/physical proofs are never reused.
    """
    definition = binding.get('review_definition')
    if definition is None:
        return None
    records = {e['id']: e for e in [*dd.get('tables', []), *dd.get('columns', []),
                                   *dd.get('semantic_statements', [])]}
    evidence = dict(dd.get('evidence_text', {}))
    evidence.update({e['id']: e['text'] for e in dd.get('semantic_statements', [])})
    context = {'table': {'name': binding['table']}, 'existing_definitions': [], 'timestamps': [timestamp],
               'carrier_values': {definition['carrier_column_id']: [str(binding['alpha']['value'])]}
                   if definition['kind'] == 'carrier_value' else {},
               'evidence': [{'id': key, 'text': text, 'table': records.get(key, {}).get('table'),
                             'column': records.get(key, {}).get('column')} for key, text in evidence.items()]}
    if timestamp.get('ts_id') != definition['timestamp_unit_id']:
        return None
    if validate_patch({'confidence': 'high', 'time_role_revisions': [], 'operations': [{'operation': 'add', 'definition': definition}]}, context):
        return None
    return definition
