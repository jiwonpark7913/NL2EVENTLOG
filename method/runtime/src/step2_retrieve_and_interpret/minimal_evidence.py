"""Expose the existing EEG entity, time and attribution evidence to the interpreter."""

from collections import defaultdict

from src.common.attribution_policy import attribution_adjacency, documented_reference_roles
from src.step3_execute.verify_execution_dependencies import VALID_PATH


def make_evidence(graph):
    """PURPOSE: Present A/B arms one bounded projection of EEG facts.
    INPUT: Indexed PI graph. OUTPUT: Model cards and graph-backed scope records. No extraction knowledge is added.
    """
    case_facts = {e['id']: e for e in graph['entity_types'] if (e.get('population') or {}).get('status') == 'valid'}
    definitions = {e['id']: e for e in graph['event_definitions'] if e.get('extraction_status') == 'executable'}
    roles = documented_reference_roles(attribution_adjacency(graph.get('relationships', [])),
                                       graph.get('data_dictionary') or {})
    offered_paths = defaultdict(list)
    for path in graph['attribution_paths']:
        case, event = path['to'], path['event_definition_id']
        if case not in case_facts or event not in definitions or path.get('validation_status') not in VALID_PATH:
            continue
        proven = (path.get('role_validation') or {}).get('reference') or {}
        edges = path.get('edge_ids', [])
        path_roles = {roles[edge]['role']: roles[edge]['quote'] for edge in edges if edge in roles}
        if proven.get('role'):
            path_roles[proven['role']] = proven.get('quote')
        offered_paths[event].append({'id': path['id'], 'case_et_id': case,
                                     'role': next(iter(path_roles)) if len(path_roles) == 1 else None,
                                     'role_evidence': path_roles, 'lineage': edges})
    cases, scopes = [], {}
    for case, entity in sorted(case_facts.items()):
        maps = entity['population']['maps']
        options = {}
        if len(maps) == 1:
            options = {key: {'kind': 'reference_role', 'role': role['role'], 'step': role['step'],
                             'dictionary_id': role['dictionary_id'], 'evidence': role['quote']}
                       for key, role in roles.items() if role['step']['left_table'] == maps[0]['table']}
        scopes[case] = options
        cases.append({'id': case, 'name': entity.get('name'), 'meaning': entity.get('business_meaning'),
                      'definition': entity.get('business_definition'), 'aliases': entity.get('lexical_aliases', []),
                      'populations': [{'table': m['table'], 'keys': m['key_columns']} for m in maps],
                      'scopes': [{'id': key, 'role': role['role'], 'evidence': role['evidence']}
                                 for key, role in sorted(options.items())]})
    priority = set(graph.get('index_scope', {}).get('prioritization_event_ids', []))
    cards = []
    for event in sorted(offered_paths, key=lambda identifier: (identifier not in priority, identifier)):
        definition = definitions[event]
        semantics = definition.get('activity_semantics') or {}
        cards.append({'id': event, 'activity': definition.get('activity_label') or definition.get('activity'),
                      'meaning': semantics.get('event_label'), 'code_meaning': semantics.get('code_meaning'),
                      'evidence': [item['quote'] for item in semantics.get('citations', []) if item.get('quote')][:2],
                      'source_table': definition.get('source_table'), 'clock_id': definition.get('ts_id'),
                      'clock': definition.get('occurrence_time_source'), 'values': definition.get('raw_values', []),
                      'paths': sorted(offered_paths[event], key=lambda p: (p['case_et_id'], p['id']))})
    return {'cases': cases, 'events': cards}, scopes


def case_evidence(evidence, case):
    """PURPOSE: Focus event selection on the chosen Case. INPUT: Immutable full cards and selected Case ID.
    OUTPUT: Same event facts restricted to paths addressed to that Case.
    """
    cards = []
    for event in evidence['events']:
        paths = [path for path in event['paths'] if path['case_et_id'] == case]
        if paths:
            cards.append({**event, 'paths': paths})
    return cards
