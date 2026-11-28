"""Compare the projected EEG with claims enumerated independently from public sources."""

from collections import Counter, defaultdict
from contextlib import closing
import re

from src.common.data_dictionary import dictionary_indexes
from src.common.database_io import connect_readonly, quote_identifier
from src.common.event_clock import scoped_event_clock
from src.step1_understand.candidate_ledger import candidate_key
from src.step1_understand.carrier_timestamp_binding import carrier_clock_relationship, documented_work_endpoints
from src.step1_understand.detect_and_normalize_timestamps import occurrence_time_policy, timestamp_semantic_role
from src.step1_understand.interpret_event_definitions import profile_carrier_family
from src.step1_understand.resolve_activity_meanings import code_table_evidence, deterministic_meanings

CARRIER_EVIDENCE = re.compile(r'\b(?:activity|event|transition|operation|action|milestone)\b', re.I)


def source_claims(database, tables, dictionary, units, key_profiles):
    """PURPOSE: Enumerate independently testable expectations from ordinary public inputs.
    INPUT: Read-only DB, schema, DD, recognized clock representations, and physical key profiles.
    OUTPUT: Source-side clock, code, combination, key and FK claims with explicit evidence references.
    """
    docs = dictionary_indexes(dictionary)
    schemas = {table.name: table for table in tables}
    by_table = defaultdict(list)
    for unit in units:
        by_table[unit['table']].append(unit)
    claims = []
    with closing(connect_readonly(database)) as connection:
        for table in tables:
            local_units = by_table[table.name]
            table_doc = docs['tables'].get(table.name, {})
            columns = {item.name: docs['columns'].get((table.name, item.name), {})
                       for item in table.columns}
            clocks = {unit['ts_id']: columns.get(unit['columns'][0], {}) for unit in local_units}
            work_endpoints = documented_work_endpoints(table_doc.get('definition', ''), (
                (unit, clocks[unit['ts_id']].get('definition', '')) for unit in local_units))
            for column, document in columns.items():
                if not document.get('id'):
                    continue
                text = document.get('definition', '')
                clock_role = timestamp_semantic_role(table.name, [column], document)
                if clock_role['confidence_basis'] == 'explicit_dictionary' and re.search(
                        r'\b(?:time|date|timestamp|clock)\b', text, re.I):
                    claims.append({'kind': 'clock', 'table': table.name, 'columns': [column],
                                   'role': clock_role['semantic_role'], 'evidence': document['id']})
                domain = document.get('value_domain') or document.get('code_meanings')
                if not CARRIER_EVIDENCE.search(text) or re.search(r'\b(?:not an? (?:event|activity)|static attribute)\b', text, re.I):
                    continue
                lookup = code_table_evidence(connection, table, column, schemas, dictionary)
                if not domain and not lookup:
                    continue
                observed, support = profile_carrier_family(connection, table, column, local_units, document, lookup)
                codebook_ids = [item['evidence']['id'] for entries in lookup.values() for item in entries]
                for value_type, value in support:
                    if value_type is bytes:
                        continue
                    meaning = deterministic_meanings(document, value, lookup, table_doc)
                    if meaning['status'] != 'supported':
                        continue
                    claims.append({'kind': 'documented_code', 'table': table.name, 'column': column,
                                   'value': value, 'evidence': document['id'], 'observed': (value_type, value) in observed})
                    for unit, stats in zip(local_units, support[(value_type, value)], strict=True):
                        clock = clocks[unit['ts_id']]
                        alpha = {'kind': 'value', 'column': column, 'value': value}
                        scoped = scoped_event_clock({'table': table.name, 'alpha': alpha},
                                                   unit, document, clock, resolution=meaning)
                        verdict = carrier_clock_relationship(scoped, clock, document, alpha, meaning, stats,
                                                             work_endpoints=work_endpoints)
                        # Documented history/context acts on a stricter occurrence scope.
                        if (verdict['status'] != 'supported' or not occurrence_time_policy(scoped)['eligible']
                                or table_doc.get('state_history') or table_doc.get('related_occurrence')):
                            continue
                        claims.append({'kind': 'carrier_event', 'table': table.name, 'column': column,
                                       'value': value, 'timestamp_unit_id': unit['ts_id'],
                                       'evidence': [document['id'], clock.get('id'), *codebook_ids[:1]]})
            claims.extend({'kind': 'reference', 'table': table.name, 'parent': fk['parent_table'],
                           'columns': [list(pair) for pair in fk['columns']]}
                          for fk in table.foreign_keys)
    claims.extend({'kind': 'key', 'table': row['table'], 'columns': list(row['columns'])}
                  for row in key_profiles if row.get('unique'))
    return claims


def source_coverage(claims, native, runtime):
    """PURPOSE: Match source-side claims to discovery, meaning review and final executable projection.
    INPUT: Independent claims, native evidence, final runtime EEG, including projection ledger.
    OUTPUT: Reviewable gap receipts and denominators by evidence type.
    """
    ledger = (runtime.get('candidate_ledger') or {}).get('candidates', [])
    candidates = {row['id']: row for row in ledger}
    projected_defs = {row['id']: row for row in runtime.get('event_definitions', [])}
    projected_paths = {row['id']: row for row in runtime.get('attribution_paths', [])}
    representations = {(m['table'], tuple(m['key_columns']))
        for et in runtime.get('entity_types', []) for m in (et.get('population') or {}).get('maps', [])
        if m.get('identity_scope_id') or m.get('namespace_id')}
    deferred = {row['table'] for row in native.get('source_coverage_rechecks', [])
                if row['status'] == 'recheck_budget_exhausted'}
    unit_types = {unit['ts_id']: unit for unit in native.get('timestamps', [])}
    columns = {(u['table'], col): u for u in unit_types.values() for col in u.get('columns', [])}
    keys = {(row['table'], tuple(row.get('pk', []))) for row in native.get('objects', [])}
    reference_shapes = {(ref.get('child_table'), ref.get('parent_table'),
                         tuple(tuple(pair) for pair in ref.get('columns', [])))
                        for ref in native.get('references', [])}
    carrier_codes = {(row['source']['table'], row['source'].get('column'),
                      type(row['source']['value']), row['source']['value'])
                     for row in ledger if row['kind'] == 'carrier_event' and 'value' in row['source']}
    gaps, counts = [], defaultdict(Counter)
    for claim in claims:
        category, table = claim['kind'], claim['table']
        counts[category]['source_claims'] += 1
        if category == 'clock':
            found = (table, claim['columns'][0]) in columns
            status = 'accounted' if found else 'clock_discovery_gap'
        elif category == 'key':
            found = (table, tuple(claim['columns'])) in keys
            status = 'accounted' if found else 'key_not_used_as_representative'
            if found and (table, tuple(claim['columns'])) not in representations:
                found, status = False, 'key_without_verified_entity_representation'
        elif category == 'reference':
            found = (table, claim['parent'], tuple(tuple(pair) for pair in claim['columns'])) in reference_shapes
            status = 'accounted' if found else 'reference_discovery_gap'
        elif category == 'documented_code':
            found = (table, claim['column'], type(claim['value']), claim['value']) in carrier_codes
            status = 'accounted' if found else 'code_not_reviewed'
        else:
            source = {key: claim[key] for key in ('table', 'column', 'value', 'timestamp_unit_id')}
            row = candidates.get(candidate_key('carrier_event', source))
            if not row:
                status = 'eligible_pair_review_deferred' if table in deferred else 'eligible_pair_not_enumerated'
            elif row.get('projected_ids'):
                definitions = [projected_defs.get(i, {}) for i in row['projected_ids']]
                status = 'accounted' if any(ed.get('extraction_status') == 'executable' for ed in definitions) else 'approved_definition_not_executable'
            else:
                status = 'eligible_pair_not_projected' if row['decision'] == 'approved' else 'eligible_pair_unresolved'
            found = status == 'accounted'
        counts[category]['accounted' if found else 'gaps'] += 1
        if not found:
            gaps.append({**claim, 'status': status})
    valid = {'valid', 'rule_confirmed_no_occurrences'}
    for path in native.get('attribution_paths', []):
        if path.get('validation_status') not in valid or path.get('event_definition_id') not in projected_defs:
            continue
        counts['validated_attribution']['source_claims'] += 1
        found = projected_paths.get(path['id'], {}).get('validation_status') in valid
        counts['validated_attribution']['accounted' if found else 'gaps'] += 1
        if not found:
            gaps.append({'kind': 'validated_attribution', 'id': path['id'],
                         'event_definition_id': path['event_definition_id'],
                         'status': 'verified_path_not_projected'})
    return {'version': 'source-coverage-v2-integrated', 'counts': dict(counts), 'gaps': gaps,
            'scope': ['explicit DD clocks/code domains, recognized compatible clock pairs, declared keys/FKs',
                      'validated path availability for projected definitions; no inferred semantic completeness']}


def reconsider_missing_pairs(database, tables, profiles, dictionary, units, classifications, config,
                             claims, bindings, traces, *, table_budget=3):
    """PURPOSE: Recheck bounded source-backed discovery gaps before event attribution.
    INPUT: Independently proved pair claims, native input and existing candidates.
    OUTPUT: Verified deterministic additions, amended traces and recheck/deferred receipts.
    """
    observed = {(row['table'], row['carrier'], type(row['value']), row['value'], row['ts_id'])
                for trace in traces.values() for row in trace.get('carrier_timestamp_matrix', [])}
    targets = defaultdict(set)
    for claim in claims:
        if claim['kind'] != 'carrier_event':
            continue
        table, column, value, clock = (claim[k] for k in ('table', 'column', 'value', 'timestamp_unit_id'))
        key = (table, column, type(value), value, clock)
        if key not in observed:
            rejected = any(row['column'] == column and row.get('admission') == 'cited_non_carrier'
                           for row in traces.get(table, {}).get('activity_evaluations', []))
            if not rejected:
                targets[table].add(key)
    if not targets:
        return bindings, traces, []

    from copy import deepcopy
    from src.step1_understand.interpret_event_definitions import extract_activities

    receipts = []
    active = {binding['id'] for binding in bindings}
    for position, table in enumerate(sorted(targets)):
        if position >= table_budget:
            receipts.append({'table': table, 'status': 'recheck_budget_exhausted', 'candidates': len(targets[table])})
            continue
        forced = {item[1] for item in targets[table]}
        proposals, output = extract_activities(
            database, tables, profiles, dictionary, units, {table: deepcopy(classifications[table])},
            config, source_proved_carriers={table: forced})
        proposed = {item['id']: item for item in proposals if item['interpretation_status'] == 'supported'}
        reviewed = []
        for row in output[table].get('carrier_timestamp_matrix', []):
            identity = (table, row['carrier'], type(row['value']), row['value'], row['ts_id'])
            if identity in targets[table]:
                traces[table].setdefault('carrier_timestamp_matrix', []).append(row)
                identifier = row['candidate_id']
                if identifier in proposed and identifier not in active:
                    bindings.append(proposed[identifier])
                    active.add(identifier)
                    reviewed.append(identifier)
        receipts.append({'table': table, 'status': 'rechecked', 'candidates': len(targets[table]),
                         'added_definition_ids': reviewed})
    return bindings, traces, receipts
