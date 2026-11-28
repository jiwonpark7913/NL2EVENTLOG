"""Prove the selected occurrence assignments after the compiler's Case population filter."""

from collections import defaultdict
from contextlib import closing
import json
import sqlite3

from src.common.attribution_policy import path_issues
from src.common.database_io import connect_readonly
from src.common.entity_population import population_cte
from src.common.schema_metadata import database_fingerprint, stable_id
from src.step2_retrieve_and_interpret.resolve_history_attribution import path_pairs, path_role, union_policy
from src.step3_execute.verify_execution_dependencies import VALID_PATH


def _population_keys(connection, target, scope):
    """PURPOSE: Read exactly the compiler's typed Case identifiers.
    INPUT: Existing read transaction, bound ET and structural scope. OUTPUT: Internal typed key set.
    """
    cte = population_cte({'population': target['population']}, scope)
    keys = set()
    for encoded, in connection.execute(f'WITH {cte} SELECT case_id FROM entity_cases'):
        entity, namespace, parts = json.loads(encoded)
        if entity != target['id']:
            raise ValueError('scope_entity_mismatch')
        keys.add((namespace, tuple(tuple(part) for part in parts)))
    return keys


def _prove_event(graph, target, definition, paths, connection, population, scope):
    """PURPOSE: Check path-local proofs and classify their scope-qualified union.
    INPUT: Selected ED, validated path records, one DB transaction and typed Case set.
    OUTPUT: Counts, special unresolved reason or a snapshot/scope-bound certificate.
    """
    ids = sorted(path['id'] for path in paths)
    by_map = {m['representation_id']: m for m in target['population']['maps']}
    assignments = defaultdict(lambda: defaultdict(set))
    counts = {}
    union_pairs = set()
    for path in paths:
        pairs = path_pairs(connection, path, by_map)
        kept = {(source, case) for source, case in pairs if case in population}
        counts[path['id']] = len(kept)
        union_pairs.update(kept)
        role = (path_role(path).get('role') or '').casefold()
        for source, case in kept:
            assignments[source][case].add(role)
    multiple = [cases for cases in assignments.values() if len(cases) > 1]
    receipt = {'path_ids': ids, 'source_occurrences': len(assignments), 'distinct_pairs': len(union_pairs),
               'repeated_pairs': sum(counts.values()) - len(union_pairs),
               'multiple_case_occurrences': len(multiple), 'scoped_pairs_by_path': counts}
    if multiple:
        authority = set()
        for cases in multiple:
            roles = set().union(*cases.values())
            documented = (union_policy(graph, definition, target, roles)
                          if '' not in roles and sum(map(len, cases.values())) == len(roles) else None)
            if documented is None:
                return {**receipt, 'status': 'cross_path_case_conflict'}
            authority.add(documented)
        return {**receipt, 'status': 'documented_multiple_cases', 'evidence_ids': sorted(authority)}
    if all(count == len(union_pairs) for count in counts.values()):
        return {**receipt, 'status': 'pass', 'equivalent_paths': ids}
    # The contract is functional over scoped assignments, including shared identical pairs.
    proof = stable_id('scoped_path_union', [graph['database_fingerprint'], target['id'], definition['id'],
                                            scope or {'kind': 'all_cases'}, ids, counts,
                                            sorted(union_pairs, key=repr)])
    return {**receipt, 'status': 'pass', 'union_id': proof}


def verify_scoped_unions(graph, database, info):
    """PURPOSE: Verify only EDs with multiple selected paths, against one immutable DB view.
    INPUT: Execution graph, SQLite path and bound PI. OUTPUT: Independent per-ED proof receipts.
    """
    selected = {ed: sorted(set(paths)) for ed, paths in info['verified_attribution_paths'].items()
                if len(set(paths)) > 1}
    if not selected:
        return {}
    scope = info.get('case_scope')
    case_id = info['case_notion_et_id']
    target = next(e for e in graph['entity_types'] if e['id'] == case_id)
    paths = {p['id']: p for p in graph['attribution_paths']}
    definitions = {e['id']: e for e in graph['event_definitions']}
    result = {}
    try:
        if graph['database_fingerprint'] != database_fingerprint(database):
            raise ValueError('database_snapshot_changed')
        with closing(connect_readonly(database)) as connection:
            connection.execute('BEGIN')
            population = _population_keys(connection, target, scope)
            for ed, ids in selected.items():
                group = [paths[identifier] for identifier in ids]
                if any(path['to'] != case_id or path['event_definition_id'] != ed or
                       path['validation_status'] not in VALID_PATH or
                       (path['validation_status'] == 'valid' and path['case_map']['validation']['passed'] is not True)
                       or path_issues(path['joins'], graph['relationships']) for path in group):
                    result[ed] = {'status': 'invalid_path_union', 'path_ids': ids, 'basis': 'unverified_pi_path'}
                else:
                    result[ed] = _prove_event(graph, target, definitions[ed], group, connection, population, scope)
        if graph['database_fingerprint'] != database_fingerprint(database):
            raise ValueError('database_snapshot_changed')
    except (KeyError, OSError, sqlite3.Error, TypeError, ValueError) as error:
        reason = str(error) if str(error) == 'database_snapshot_changed' else type(error).__name__
        return {ed: {'status': 'invalid_path_union', 'path_ids': ids, 'basis': reason}
                for ed, ids in selected.items()}
    return result
