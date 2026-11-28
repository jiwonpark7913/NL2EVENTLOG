"""Prove carrier partitions over independently validated EEG definitions."""

from collections import Counter, defaultdict
from contextlib import closing
from copy import deepcopy
import json
import sqlite3

from src.common.database_io import connect_readonly
from src.common.schema_metadata import build_process_view_candidates, database_fingerprint, event_source_condition, stable_id
from src.common.sql_identifiers import quote_identifier
from src.step2_retrieve_and_interpret.event_definition_granularity import definition_subsumption
from src.step3_execute.compile_event_log_sql import _condition

POLICY_VERSION = 'carrier-event-families-v3'
from src.step1_understand.eeg_configuration import INTEGRATED_POLICY
PATH_STATES = {'valid', 'rule_confirmed_no_occurrences'}


def _clock_semantics(definition):
    """PURPOSE: Identify a documented occurrence phase and clock.
    INPUT: One executable EEG definition. OUTPUT: Scalar clock evidence and phase, or None.
    """
    signature = definition.get('semantic_signature') or {}
    clocks = definition.get('timestamp_candidates', [])
    if (len(clocks) != 1 or clocks[0].get('kind') != 'direct'
            or signature.get('interpretation_status') != 'supported'
            or signature.get('transition') is not None):
        return None
    clock = clocks[0]
    role = signature.get('temporal_role')
    if not role or role in {'unknown', 'unresolved', 'other', 'validity', 'scheduled', 'recorded'}:
        return None
    column = clock.get('column')
    reference = f"C:{definition['source_table']}.{column}"
    if not column or not any(s == reference or s.startswith(reference + ':')
                             for s in signature.get('evidence_refs', [])):
        return None
    return column, role, clock.get('time_role'), clock.get('timezone'), clock.get('format')


def _carrier_partition(broad, children, alternatives):
    """PURPOSE: Admit documented specializations of one occurrence phase.
    INPUT: Broad definition, physically included members and reviewed alternative edges.
    OUTPUT: A single carrier column, or None for unsupported or conflicting encodings.
    """
    clock = _clock_semantics(broad)
    if not clock or broad.get('source_kind') != 'column_event':
        return None
    carrier = {e.get('activity_column') for e in children}
    if len(carrier) != 1 or None in carrier:
        return None
    column = next(iter(carrier))
    reference = f"C:{broad['source_table']}.{column}:"
    seen = set()
    for child in children:
        values = child.get('raw_values', [])
        semantics = child.get('activity_semantics') or {}
        citations = [c.get('evidence_id', '') for c in semantics.get('citations', [])]
        typed = {json.dumps(v, ensure_ascii=False) for v in values}
        documented = {ref.rsplit(':', 1)[-1] for ref in citations if ref.startswith(reference)}
        missing = [value for value in values if str(value) not in documented and not any(
            evidence.get('kind') == 'verified_code_table_row'
            and evidence.get('source_table') == broad['source_table']
            and evidence.get('carrier_column') == column
            and type(evidence.get('lookup_code')) is type(value) and evidence.get('lookup_code') == value
            and evidence.get('foreign_key', {}).get('parent_table') == evidence.get('lookup_table')
            and tuple(tuple(pair) for pair in evidence.get('foreign_key', {}).get('columns', []))
                == ((column, evidence.get('lookup_key')), )
            and isinstance(evidence.get('lookup_label'), str) and evidence['lookup_label'].strip()
            for evidence in semantics.get('evidence', []))]
        if (child.get('source_kind') != 'row_activity' or not values or None in values
                or seen & typed or _clock_semantics(child) != clock
                or semantics.get('status') != 'supported'
                or missing
                or frozenset((broad['id'], child['id'])) not in alternatives):
            return None
        seen.update(typed)
    return column


def _source_occurrences(connection, definition):
    """PURPOSE: Count full source keys and clocks under the real extraction predicate.
    INPUT: Read-only DB and trusted EEG definition. OUTPUT: Source occurrence multiset.
    """
    key = definition['source_row_key']
    clock = definition['timestamp_columns'][0]
    columns = ', '.join(f's0.{quote_identifier(name)}' for name in [*key, clock])
    table = quote_identifier(definition['source_table'])
    predicate = _condition({'source_condition': event_source_condition(definition)})
    return Counter(connection.execute(f'SELECT {columns} FROM {table} s0 WHERE {predicate} '
                                      f'AND s0.{quote_identifier(clock)} IS NOT NULL'))


def _path_signature(path):
    """PURPOSE: Compare attribution semantics independently of path IDs and observed counts.
    INPUT: Validated path. OUTPUT: Target, key, role and ordered path signature.
    """
    route = [path.get(key) for key in ('to', 'target_table_key_id', 'joins', 'case_role',
                                      'role_scope', 'role_validation', 'attribution_policy')]
    mapping = path['case_map']
    return json.dumps([*route, mapping.get('source_event_key_columns'), mapping.get('case_key_fields')],
                      sort_keys=True, ensure_ascii=False)


def _path_occurrences(connection, path):
    """PURPOSE: Replay one trusted case map with the original bound values.
    INPUT: Read-only DB and validated path. OUTPUT: Source-key/case-key multiset.
    """
    mapping = path['case_map']
    return Counter(connection.execute(mapping['map_sql'], mapping.get('map_parameters', [])))


def _prove_attribution(connection, broad_paths, members, definitions, by_event):
    """PURPOSE: Preserve every original target and role with a lossless carrier union.
    INPUT: Broad paths, child IDs and validated path index. OUTPUT: Old→new path IDs and missing path IDs.
    """
    indexes = {eid: defaultdict(list) for eid in members}
    for eid, index in indexes.items():
        for path in by_event[eid]:
            index[_path_signature(path)].append(path)
    mapping, unresolved = {}, []
    for path in broad_paths:
        route = _path_signature(path)
        parts = [index[route] for index in indexes.values()]
        if not all(len(part) == 1 for part in parts):
            unresolved.append(path['id'])
            continue
        children = [part[0] for part in parts]
        if any(definitions[eid].get('entity_reviews', {}).get(path.get('to'), {})
               .get('attribution_paths', {}).get(child['id'], {}).get('status') == 'incompatible'
               for eid, child in zip(members, children)):
            unresolved.append(path['id'])
            continue
        combined = Counter()
        for child in children:
            combined.update(_path_occurrences(connection, child))
        if combined != _path_occurrences(connection, path):
            unresolved.append(path['id'])
        else:
            mapping[path['id']] = [child['id'] for child in children]
    return mapping, unresolved


def _candidate_families(graph, connection):
    """PURPOSE: Measure proof, residue and attribution for broad/child definitions.
    INPUT: Final runtime projection and read-only DB. OUTPUT: Non-executable families and proof audit.
    """
    definitions = {e['id']: e for e in graph['event_definitions'] if e['extraction_status'] == 'executable'}
    candidates = definition_subsumption(definitions, definitions)
    alternatives = {frozenset(r['binding_pair']) for r in graph.get('event_definition_pair_relationships', [])
                    if r.get('relationship') == 'alternative' and r.get('status') == 'supported'}
    paths = defaultdict(list)
    for path in graph.get('attribution_paths', []):
        if path.get('validation_status') in PATH_STATES and path.get('case_map', {}).get('map_sql'):
            paths[path['event_definition_id']].append(path)

    families, diagnostics = [], []
    for broad_id, ids in sorted(candidates.items()):
        broad = definitions[broad_id]
        members = sorted(ids)
        children = [definitions[eid] for eid in members]
        carrier = _carrier_partition(broad, children, alternatives)
        row = {'broad_event_definition_id': broad_id, 'member_event_definition_ids': members,
               'source_table': broad['source_table'], 'carrier_column': carrier,
               'timestamp_column': broad['timestamp_columns'][0]}
        if not carrier:
            diagnostics.append({**row, 'status': 'unproven_semantic_partition'})
            continue
        original = _source_occurrences(connection, broad)
        union = Counter()
        member_counts = {}
        for child in children:
            values = _source_occurrences(connection, child)
            union.update(values)
            member_counts[child['id']] = sum(values.values())
        repeated = sum(n - 1 for n in union.values() if n > 1)
        missing, extra = original - union, union - original
        path_mapping, path_gaps = _prove_attribution(connection, paths[broad_id], members, definitions, paths)
        status = ('proven' if original and all(member_counts.values()) and not (missing or extra or repeated or path_gaps)
                  else 'incomplete_occurrence_or_attribution_union')
        diagnostic = {**row, 'status': status, 'broad_occurrences': sum(original.values()),
                      'member_occurrences': member_counts, 'union_occurrences': len(union),
                      'overlap_occurrences': repeated, 'missing_occurrences': sum(missing.values()),
                      'extra_occurrences': sum(extra.values()), 'uncovered_path_ids': path_gaps,
                      'replacement_path_ids': path_mapping}
        if missing:
            key_columns = broad['source_row_key']
            select = ', '.join(quote_identifier(col) for col in [*key_columns, row['timestamp_column'], carrier])
            table = quote_identifier(broad['source_table'])
            residue = Counter()
            for record in connection.execute(f'SELECT {select} FROM {table}'):
                if tuple(record[:-1]) in missing:
                    residue['null_carrier' if record[-1] is None else 'uncovered_carrier'] += 1
            diagnostic['residue_reasons'] = dict(residue)
        diagnostics.append(diagnostic)
        if status == 'proven':
            clock, phase, time_role, _, _ = _clock_semantics(broad)
            family_id = stable_id('event_family', [broad_id, members])
            families.append({'id': family_id, 'label': broad.get('activity_label') or broad['activity'],
                             'scope': 'carrier_specializations_of_one_recorded_phase',
                             'broad_event_definition_id': broad_id, 'member_event_definition_ids': members,
                             'phase': phase, 'time_role': time_role, 'timestamp_column': clock,
                             'source_table': broad['source_table'], 'carrier_column': carrier,
                             'evidence_ids': sorted(set(broad['semantic_signature'].get('evidence_refs', []))),
                             'proof': 'documented_phase_disjoint_full_source_keys_and_role_path_unions'})
    return families, diagnostics


def _prove_family_lifecycle_pairs(graph, families):
    """PURPOSE: Resolve legacy unknown pairs for distinct, documented clocks of one source case.
    INPUT: Active EDs, independent clock signatures and proven carrier families.
    OUTPUT: Phase relations on the same source identity, including the supporting DD evidence.
    """
    members = {eid for family in families for eid in family['member_event_definition_ids']}
    definitions = {d['id']: d for d in graph['event_definitions'] if d['extraction_status'] == 'executable'}
    resolved = []
    for pair in graph.get('event_definition_pair_relationships', []):
        ids = pair['binding_pair']
        if pair.get('relationship') != 'unknown' or len(ids) != 2 or not members.intersection(ids):
            continue
        left, right = (definitions.get(eid) for eid in ids)
        if not left or not right or left['source_table'] != right['source_table']:
            continue
        if left.get('source_row_key') != right.get('source_row_key'):
            continue
        clocks = [_clock_semantics(d) for d in (left, right)]
        if not all(clocks) or {clock[1] for clock in clocks} != {'start', 'completion'}:
            continue
        if clocks[0][0] == clocks[1][0]:
            continue
        supporting = sorted({ref for d in (left, right) for ref in d['semantic_signature']['evidence_refs']})
        pair.update(relationship='lifecycle_pair', status='supported',
                    evidence=['documented_separate_source_clocks', *supporting],
                    confidence_basis='documented_separate_source_clocks')
        resolved.append(pair['id'])
    return resolved


def _retire_broad_definitions(graph, broad_ids):
    """PURPOSE: Remove replaced executable EDs and their active references.
    INPUT: Independent runtime graph and proven broad IDs. OUTPUT: Updated active projection.
    """
    removed_relations = {r['id'] for r in graph.get('event_definition_pair_relationships', [])
                         if broad_ids & set(r['binding_pair'])}
    for key in ('event_definitions', 'bindings', 'activity_bindings'):
        if key not in graph:
            continue
        graph[key] = [d for d in graph[key] if d['id'] not in broad_ids]
        for definition in graph[key]:
            if 'conflict_relation_ids' in definition:
                definition['conflict_relation_ids'] = [rid for rid in definition['conflict_relation_ids']
                                                        if rid not in removed_relations]
            for review in definition.get('entity_reviews', {}).values():
                if review.get('duplicate_of') in broad_ids:
                    review.pop('duplicate_of')
                    review.pop('verified_occurrences', None)
    for key in ('attribution_paths', 'event_entity_links', 'event_entity_associations', 'occurrence_identity_rules'):
        graph[key] = [r for r in graph.get(key, []) if
                      (r.get('event_definition_id') or r.get('binding_id')) not in broad_ids]
    graph['event_definition_pair_relationships'] = [r for r in graph.get('event_definition_pair_relationships', [])
                                                    if r['id'] not in removed_relations]
    graph.pop('revision_summary', None)
    if 'view_candidates' in graph:
        graph['view_candidates'] = build_process_view_candidates(
            graph, max_hops=graph.get('build_configuration', {}).get('max_hops'))


def apply_carrier_policy(graph, database):
    """PURPOSE: Prove carrier partitions and build the single active runtime projection.
    INPUT: Validated pre-policy graph and matching read-only SQLite database.
    OUTPUT: Independent graph with supported families, retired definitions and migration evidence.
    """
    if graph.get('carrier_event_policy'):
        raise ValueError('Carrier policy requires a validated pre-policy EEG')
    if (expected := graph.get('database_fingerprint')) and expected != database_fingerprint(database):
        raise ValueError('Carrier policy DB fingerprint does not match the EEG')
    result = deepcopy(graph)
    with closing(connect_readonly(database)) as connection:
        connection.execute('PRAGMA query_only=ON')
        connection.execute('BEGIN')
        families, diagnostics = _candidate_families(result, connection)
    lifecycle_pairs = _prove_family_lifecycle_pairs(result, families)
    prior = [e['id'] for e in result['event_definitions']]
    replaced = {family['broad_event_definition_id']: family for family in families}
    result['canonical_activity_policy'] = 'eeg-canonical-label-v1'
    result['retired_event_definitions'] = [
        {**d, 'previous_extraction_status':d['extraction_status'], 'extraction_status':'retired',
         'retirement_proof_id':replaced[d['id']]['id']}
        for d in result['event_definitions'] if d['id'] in replaced]
    if replaced:
        _retire_broad_definitions(result, set(replaced))
    result['carrier_event_policy'] = {'version': POLICY_VERSION, 'mode': INTEGRATED_POLICY}
    result['event_families'] = families
    result['build_configuration'] = {**result.get('build_configuration', {}),
                                     'carrier_event_policy': INTEGRATED_POLICY}
    result['carrier_lifecycle_pair_proofs'] = lifecycle_pairs
    result['carrier_partition_audit'] = diagnostics
    result['event_definition_migration'] = {
        eid: {'status': 'replaced_by_family', 'family_id': replaced[eid]['id'],
              'replacement_ids': replaced[eid]['member_event_definition_ids']} if eid in replaced else
             {'status': 'retained', 'replacement_ids': [eid]} for eid in prior}
    result.pop('eeg_cache', None)
    return result
