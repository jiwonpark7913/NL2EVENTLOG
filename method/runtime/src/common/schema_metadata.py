"""Reusable DB evidence graph; semantic assertions live in sourced annotations."""

from __future__ import annotations
from src.common.attribution_policy import MAX_ATTRIBUTION_HOPS, bounded_hops
import copy
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path
from src.common.sql_identifiers import quote_identifier


def normalize(value):
    """PURPOSE: Normalize lexical matching without discarding non-English text.
    INPUT: Unicode label or question text.
    OUTPUT: Casefolded, whitespace-separated tokens; no side effects.
    """
    return ' '.join(x for x in re.split(r'[\W_]+', value.casefold()) if x)


def stable_id(prefix, value):
    """PURPOSE: Identify an immutable evidence/candidate description deterministically.
    INPUT: Namespace prefix and JSON-serializable value.
    OUTPUT: Short SHA-256-based ID; dictionary key order is ignored.
    """
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True)
    return prefix + '_' + hashlib.sha256(raw.encode()).hexdigest()[:16]


def database_fingerprint(path):
    """PURPOSE: Invalidate cached evidence when a database or WAL changes.
    INPUT: Existing SQLite file path.
    OUTPUT: Path/stat/header fingerprint; read-only, not a cryptographic full-file snapshot.
    """
    path = Path(path).resolve()
    digest = hashlib.sha256()
    for file in (path, Path(str(path) + '-wal')):
        if file.exists():
            stat = file.stat()
            digest.update(f'{file}:{stat.st_size}:{stat.st_mtime_ns}'.encode())
            with file.open('rb') as stream:
                digest.update(stream.read(65536))
    return digest.hexdigest()


def timestamp_columns(binding):
    """PURPOSE: Give timestamp components a stable semantic order across consumers.
    INPUT: Timestamp binding, including direct, epoch or date/clock shapes.
    OUTPUT: Ordered physical columns independent of JSON dictionary insertion order.
    """
    if binding.get('components'):
        return [component['column'] for component in binding['components']]
    return [binding[key] for key in ('column', 'date_column', 'clock_column', 'seconds_column') if key in binding]


def event_source_condition(binding):
    """PURPOSE: Share event-defining predicates across retrieval, knowledge, and ES.
    INPUT: Row/column candidate plus optional explicitly documented source conditions.
    OUTPUT: Structured predicate only; no SQL and no user-query filters.
    """
    base = ({'kind': 'in', 'column': binding['activity_column'], 'values': binding['raw_values']}
            if binding['source_kind'] == 'row_activity'
            else {'kind': 'not_null', 'column': binding['timestamp_columns'][0]})
    conditions = binding.get('documented_source_conditions', [])
    return {'kind': 'and', 'conditions': [base, *conditions]} if conditions else base


def _anchor_directed_paths(relationships, source, anchor, max_hops, max_paths):
    """PURPOSE: Find bounded source-to-anchor structural paths for offline view cards.
    INPUT: Relationship records, source/anchor tables and explicit search limits.
    OUTPUT: Declared child-to-parent paths first; inferred paths remain visibly flagged.
    """
    max_hops = bounded_hops(max_hops)
    if source == anchor:
        return [[]], False
    adjacency = defaultdict(list)
    for edge in relationships:
        if edge.get('declared') is True:
            adjacency[edge['left_table']].append((edge['right_table'], edge, False))
    queue = [(source, [], {source})]
    found, truncated = [], False
    while queue and len(found) < max_paths:
        table, path, seen = queue.pop(0)
        for target, edge, reverse in sorted(adjacency.get(table, []), key=lambda item: item[1]['id']):
            if target in seen:
                continue
            step = {'relationship_id': edge['id'], 'from_table': table, 'to_table': target,
                    'declared': bool(edge.get('declared')), 'direction':
                    'inferred_reverse' if reverse else
                    'child_to_parent' if edge.get('declared') else 'inferred_forward'}
            extended = [*path, step]
            if target == anchor:
                found.append(extended)
                if len(found) >= max_paths:
                    truncated |= bool(queue)
                    break
            else:
                queue.append((target, extended, seen | {target}))
    found.sort(key=lambda path: (any(not step['declared'] for step in path), len(path),
                                 [step['relationship_id'] for step in path]))
    return found, truncated


def build_process_view_candidates(graph, max_hops=MAX_ATTRIBUTION_HOPS, budgets=None):
    """PURPOSE: Precompute bounded anchor-centred Process View evidence cards.
    INPUT: A v6 graph, hop limit and optional anchor/path/branch budgets.
    OUTPUT: Offline hypotheses whose activities are evidence, never fixed view members.
    """
    max_hops = bounded_hops(max_hops)
    limits = {'max_anchors': 128, 'max_paths_per_source': 3, 'max_branches_per_anchor': 512}
    limits.update(budgets or {})
    cards = []
    table_key_records = graph.get('table_key_records', [])[:limits['max_anchors']]
    for object_type in table_key_records:
        branches, exhausted = [], False
        for binding in graph.get('event_definitions', []):
            if object_type.get('case_projection'):
                if binding['source_table'] not in object_type.get('projection_sources', []):
                    continue
                paths, truncated = [[]], False
            else:
                paths, truncated = _anchor_directed_paths(
                    graph.get('relationships', []), binding['source_table'],
                    object_type['anchor_table'], max_hops, limits['max_paths_per_source'])
            exhausted |= truncated
            for path in paths:
                timestamp_ids = [candidate['id'] for candidate in binding.get('timestamp_candidates', [])]
                branches.append({
                    'id': stable_id('view_branch', [object_type['id'], binding['id'], path]),
                    'entity_type_id': object_type['id'],
                    'path_shape': {'relationship_ids': [step['relationship_id'] for step in path],
                                   'hop_count': len(path),
                                   'declared_anchor_directed': all(step['direction'] == 'child_to_parent'
                                                                   for step in path),
                                   'contains_inferred_edge': any(not step['declared'] for step in path),
                                   'steps': path},
                    'activity_hypotheses': [{
                        'event_definition_id': binding['id'],
                        'canonical_activity_id': binding['canonical_activity_id'],
                        'activity_label': binding['activity_label'],
                        'source_kind': binding['source_kind'],
                        'timestamp_candidate_ids': timestamp_ids,
                        'evidence_ids': [stable_id('evidence', [binding['id'], item])
                                         for item in timestamp_ids or ['timestamp_missing']],
                    }],
                })
                if len(branches) >= limits['max_branches_per_anchor']:
                    exhausted = True
                    break
            if len(branches) >= limits['max_branches_per_anchor']:
                break
        path_nodes = {step['from_table'] for branch in branches for step in branch['path_shape']['steps']}
        path_nodes.update(step['to_table'] for branch in branches for step in branch['path_shape']['steps'])
        nodes = sorted({object_type['anchor_table'], *path_nodes})
        edge_ids = sorted({step['relationship_id'] for branch in branches
                           for step in branch['path_shape']['steps']})
        hypothesis_count = sum(len(branch['activity_hypotheses']) for branch in branches)
        timestamp_count = sum(bool(item['timestamp_candidate_ids']) for branch in branches
                              for item in branch['activity_hypotheses'])
        payload = {'anchor_entity_type_id': object_type['id'],
                   'branch_ids': [branch['id'] for branch in branches], 'max_hops': max_hops}
        cards.append({
            'id': stable_id('process_view_candidate', payload),
            'anchor_entity_type_id': object_type['id'],
            'case_projection': copy.deepcopy(object_type.get('case_projection')),
            'projection_sources': list(object_type.get('projection_sources', [])),
            'concept_name': object_type.get('concept_name'),
            'subgraph': {'nodes': nodes, 'relationship_ids': edge_ids},
            'branches': branches,
            'quality_estimates': {
                'case_support': {
                    'identity_candidate_count': len(object_type.get('identity_candidates', [])),
                    'has_primary_key': object_type.get('prior', {}).get('has_primary_key', False)},
                'activity_support': {
                    'hypothesis_count': hypothesis_count,
                    'distinct_activity_count': len({
                        item['canonical_activity_id'] for branch in branches
                        for item in branch['activity_hypotheses']}),
                    'timestamp_supported_ratio': (
                        timestamp_count / hypothesis_count if hypothesis_count else 0.0)},
                'path_support': {
                    'declared_anchor_directed_ratio': (
                        sum(branch['path_shape']['declared_anchor_directed'] for branch in branches) /
                        len(branches) if branches else 0.0),
                    'inferred_branch_count': sum(
                        branch['path_shape']['contains_inferred_edge'] for branch in branches)},
                'activity_hypothesis_count': hypothesis_count,
                'timestamp_supported_ratio': timestamp_count / hypothesis_count if hypothesis_count else 0.0,
                'declared_path_ratio': (sum(branch['path_shape']['declared_anchor_directed'] for branch in branches) /
                                        len(branches) if branches else 0.0),
                'budget_exhausted': exhausted,
            },
            'budgets': {**limits, 'max_hops': max_hops},
            'contract': 'activity_hypotheses_not_view_membership',
        })
    return sorted(cards, key=lambda card: card['id'])
