"""Re-discover request-grounded extraction facts using the existing public EEG builder rules."""

from dataclasses import fields
from pathlib import Path
import re

from src.common.activity_identity import activity_identity
from src.common.data_dictionary import _documented_code_meanings
from src.common.database_io import read_physical_schema
from src.common.schema_metadata import database_fingerprint
from src.step1_understand.classify_definition_validation_axes import attach_validation_axes
from src.step1_understand.classify_table_event_sources import classify_tables
from src.step1_understand.detect_and_normalize_timestamps import detect_timestamps, name_tokens
from src.step1_understand.eeg_configuration import DbuConfig
from src.step1_understand.entity_representations import validate_entity_attribution
from src.step1_understand.interpret_event_definitions import _activity_name_from_timestamp, extract_activities
from src.step1_understand.profile_table_keys import profile_keys
from src.step1_understand.profile_table_values import profile_tables
from src.step1_understand.project_runtime_evidence_graph import project_event_definitions
from src.step1_understand.resolve_activity_meanings import attach_activity_semantics
from src.step1_understand.validate_event_attribution_paths import enumerate_attribution_paths
from src.step1_understand.validate_event_semantics import build_occurrence_identity_rules, finalize_extraction_contracts

GAPS = {'event_definition_missing', 'event_definition_unverified', 'case_attribution_missing'}


def _phrase_in(phrase, text):
    """PURPOSE: Detect literal documented business terms without fuzzy approval.
    INPUT: Documented label and exact request wording. OUTPUT: Whole term match."""
    tokens = ' '.join(name_tokens(str(phrase)))
    return bool(tokens and ' ' + tokens + ' ' in ' ' + ' '.join(name_tokens(text)) + ' ')


def _source_tables(graph, needs):
    """PURPOSE: Locate source tables with request-relevant public DD terms before reading DB rows.
    INPUT: Scoped graph and unresolved requirement spans. OUTPUT: Candidate table names.
    """
    spans = [r['span'] for r in needs]
    tables = set()
    for column in (graph.get('data_dictionary') or {}).get('columns', []):
        labels = [_activity_name_from_timestamp({'columns': [column['column']]}, column)]
        labels.extend(_documented_code_meanings(column).values())
        for meaning in (column.get('value_domain') or {}).values():
            labels.append(meaning.get('label') if isinstance(meaning, dict) else meaning)
        if any(_phrase_in(label, span) for span in spans for label in labels if label):
            tables.add(column['table'])
    for candidate in (graph.get('candidate_ledger') or {}).get('candidates', []):
        source = candidate['source']
        raw = source.get('value')
        if raw is not None and any(_phrase_in('code ' + str(raw), span) for span in spans):
            tables.add(source['table'])
    return tables


def recover_source_graph(graph, process_information, *, max_sources=3):
    """PURPOSE: Re-enumerate documented EDs in bounded source scope and prove their attribution.
    INPUT: Immutable request graph, unresolved PI with grounded spans, and source table budget.
    OUTPUT: Request-only overlay and evidence audit. No LLM, writes to the source, or generated SQL.
    """
    needs = [r for r in process_information.get('activity_requirement_results', [])
             if r['status'] != 'verified' and set(r.get('reason_codes', ())) & GAPS]
    target_id = process_information.get('case_notion_et_id')
    target = next((e for e in graph.get('entity_types', []) if e['id'] == target_id), None)
    if not needs or not target or (target.get('population') or {}).get('status') != 'valid':
        return graph, {'status': 'not_applicable'}
    if any(r.get('coverage') == 'all' or re.search(r'\b(?:first|last|except|only|before|after)\b', r['span'], re.I)
           for r in needs):
        return graph, {'status': 'scope_requires_semantic_resolution'}
    database = Path(graph['database'])
    if database_fingerprint(database) != graph['database_fingerprint']:
        return graph, {'status': 'source_snapshot_changed'}
    tables = _source_tables(graph, needs)
    if not tables or len(tables) > max_sources:
        return graph, {'status': 'source_budget_exhausted' if tables else 'source_evidence_unresolved',
                       'candidate_source_count': len(tables)}
    dd = graph['data_dictionary']
    schema, _ = read_physical_schema(database, dd, table_names=tables)
    config = DbuConfig(**{f.name: graph['build_configuration'][f.name] for f in fields(DbuConfig)
                        if f.name in (graph.get('build_configuration') or {})})
    profiles = profile_tables(database, schema, config.sample_size)
    timestamps, _ = detect_timestamps(database, schema, profiles, dd, config)
    states = classify_tables(schema, timestamps, dd)
    bindings, _ = extract_activities(database, schema, profiles, dd, timestamps, states, config)
    attach_activity_semantics(database, bindings, schema, timestamps, dd, llm=None,
                              model=config.model, review_budget=0)
    locked = {e['id']: e for e in graph.get('event_definitions', [])}
    # A request span must name the occurrence (including its phase, when the ED has one).
    additions = [item for item in bindings if any(
        _phrase_in(item['alpha']['name'], r['span']) for r in needs)]
    # Do not override a different, still-active rule by merely reusing its identifier.
    verified_path_ids = {p['event_definition_id'] for p in graph.get('attribution_paths', [])
                         if p.get('to') == target_id and p.get('validation_status') == 'valid'}
    additions = [item for item in additions if item['id'] not in locked or
                 locked[item['id']].get('extraction_status') != 'executable' or
                 (item['id'] not in verified_path_ids and not locked[item['id']].get('documented_source_conditions')
                  and locked[item['id']].get('alpha', {}).get('kind') == item['alpha']['kind']
                  and locked[item['id']].get('alpha', {}).get('column') == item['alpha']['column']
                  and type(locked[item['id']].get('alpha', {}).get('value')) is type(item['alpha']['value'])
                  and locked[item['id']].get('alpha', {}).get('value') == item['alpha']['value'])]
    if not additions:
        return graph, {'status': 'no_supported_source_definition', 'source_tables': sorted(tables)}
    physical_keys = [{'id': k['id'], 'table': k['anchor_table'], 'pk': k['key_columns']}
                     for k in graph.get('table_key_records', []) if k.get('key_columns')]
    case = dict(target, case_key={'fields': list(target['key_columns'])})
    keys = profile_keys(database, schema)
    native = dict(timestamps=timestamps, bindings=additions, tables=list(states.values()),
                  objects=physical_keys, concepts=[case],
                  occurrence_identity_rules=build_occurrence_identity_rules(additions, physical_keys))
    finalize_extraction_contracts(native, keys)
    additions = [a for a in additions if a['extraction_status'] == 'executable']
    native['bindings'] = additions
    attach_validation_axes(native, keys, database)
    paths = enumerate_attribution_paths(database, additions, physical_keys, [case],
        graph.get('relationships', []), [], max_hops=config.max_hops, dictionary=dd)
    paths = validate_entity_attribution(database, paths, [case])
    usable = {p['event_definition_id'] for p in paths if p['validation_status'] in {'valid', 'rule_confirmed_no_occurrences'}}
    new_events = [e for e in project_event_definitions(native) if e['id'] in usable]
    if not new_events:
        return graph, {'status': 'source_definition_or_attribution_unverified', 'source_tables': sorted(tables)}
    old_timestamps = (graph.get('dbu_rewrite') or {}).get('timestamps', [])
    merged_timestamps = {t['ts_id']: t for t in [*old_timestamps, *timestamps]}
    for position, event in enumerate(new_events):
        existing = locked.get(event['id'])
        if existing and existing.get('extraction_status') == 'executable':
            event = dict(existing)
            new_events[position] = event
        event['activity_identity'] = activity_identity(event)
        event['canonical_activity_id'] = event['activity_identity']
        event['recovery_origin'] = 'request_scoped_public_source'
    if database_fingerprint(database) != graph['database_fingerprint']:
        return graph, {'status': 'source_snapshot_changed'}
    new_ids = {e['id'] for e in new_events}
    overlay = dict(graph, event_definitions=[e for e in locked.values() if e['id'] not in new_ids] + new_events,
        attribution_paths=[p for p in graph.get('attribution_paths', []) if p['event_definition_id'] not in new_ids]
                          + [p for p in paths if p['event_definition_id'] in new_ids],
        occurrence_identity_rules=[r for r in graph.get('occurrence_identity_rules', []) if r.get('event_definition_id') not in new_ids]
                                  + [r for r in native['occurrence_identity_rules'] if r.get('event_definition_id') in new_ids],
        dbu_rewrite={**(graph.get('dbu_rewrite') or {}), 'timestamps': list(merged_timestamps.values())})
    return overlay, {'status': 'source_rules_verified', 'source_tables': sorted(tables), 'definition_ids': sorted(new_ids)}
