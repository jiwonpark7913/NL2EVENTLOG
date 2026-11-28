"""Resolve role scope and prove the union of selected attribution paths."""

from collections import defaultdict
from contextlib import closing
import json
import re
import sqlite3

from src.common.attribution_policy import mentions_role, path_issues
from src.common.database_io import connect_readonly
from src.common.entity_identity import typed_entity_key
from src.common.schema_metadata import database_fingerprint, stable_id


def path_role(path):
    """PURPOSE: Read the documented role of a path from either native role certificate.
    INPUT: Verified EEG path. OUTPUT: Reference ID/label/evidence, or an empty mapping.
    """
    proof = path.get('role_validation') or {}
    return (proof.get('reference') if proof.get('status') == 'pass' else None) or path.get('case_role') or {}


def union_policy(graph, definition, target, role_names):
    """PURPOSE: Identify an explicitly documented multi-Case relationship.
    INPUT: Public DD, ED, ET, and roles responsible for different assignments to one occurrence.
    OUTPUT: Dictionary evidence for that exact source, clock, target and role set, or None.
    """
    clock = definition.get('occurrence_time_source') or {}
    source_columns = clock.get('columns') or definition.get('timestamp_columns') or []
    targets = {mapping['table'] for mapping in target.get('population', {}).get('maps', [])}
    for index, rule in enumerate((graph.get('data_dictionary') or {}).get('business_rules', []), 1):
        if not isinstance(rule, dict):
            continue
        contract = rule.get('event_attribution') or {}
        documented_roles = contract.get('roles', [])
        if (contract.get('multiple_cases') is True and isinstance(documented_roles, list)
                and contract.get('source_table') == definition.get('source_table')
                and contract.get('case_table') in targets
                and contract.get('occurrence_columns') == source_columns and len(role_names) > 1
                and role_names <= {name.casefold() for name in documented_roles if isinstance(name, str)}
                and str(rule.get('text') or rule.get('definition') or '').strip()):
            return f'BR:{index}'
    return None


def path_pairs(connection, path, target_maps):
    """PURPOSE: Verify the saved projection on the active read-only database.
    INPUT: One validated, scoped path and canonical population maps.
    OUTPUT: Deduplicated source/Case pairs or an error for missing coverage, invalid keys or within-path fanout.
    """
    case_map = path.get('case_map') or {}
    probe = case_map.get('validation') or {}
    if path['validation_status'] == 'rule_confirmed_no_occurrences':
        if probe.get('source_rows') == 0 and path.get('identification_rule_ids'):
            return set()
        raise ValueError('unproved_empty_path')
    if (probe.get('max_cases_per_source') != 1 or probe.get('unmatched_source_rows', 0)
            or probe.get('duplicate_source_case_pairs', 0)):
        raise ValueError('invalid_path_cardinality')
    mapping = target_maps[path['target_table_key_id']]
    statement = case_map['map_sql']
    if not isinstance(statement, str) or not statement.lstrip().upper().startswith('SELECT '):
        raise ValueError('missing_read_only_case_map')
    pairs = set()
    sources = set()
    for source, raw_case in connection.execute(statement, case_map.get('map_parameters', [])):
        values = json.loads(raw_case)
        if len(values) == len(mapping['key_columns']) + 1 and values[0] == mapping['table']:
            values = values[1:]
        if len(values) != len(mapping['key_columns']) or None in values or source in sources:
            raise ValueError('duplicate_or_invalid_mapping')
        sources.add(source)
        pairs.add((source, typed_entity_key(mapping, values)))
    if len(pairs) != probe['matched_source_rows'] or len(pairs) != probe.get('attributable_source_rows', len(pairs)):
        raise ValueError('selected_path_coverage_changed')
    return pairs


def verify_path_union(graph, database, target, definition, paths):
    """PURPOSE: Classify only the selected role union under the existing single-Case event-log contract.
    INPUT: Runtime EEG, matching SQLite DB, target population, canonical ED, selected EEG paths.
    OUTPUT: Auditable union status with coverage, duplicate pair and conflicting fanout counts.
    """
    ids = sorted(path['id'] for path in paths)
    if not paths:
        return {'status': 'pass', 'path_ids': ids, 'basis': 'direct_keyed_source'}
    # The EEG already checked single path mappings. Distinct paths need a joint occurrence-level proof.
    if len(paths) == 1:
        return {'status': 'pass', 'path_ids': ids, 'basis': 'verified_path'}
    if not database:
        return {'status': 'path_union_unverified', 'path_ids': ids, 'basis': 'database_required'}
    maps = {mapping['representation_id']: mapping for mapping in target.get('population', {}).get('maps', [])}
    assignments = defaultdict(lambda: defaultdict(set))
    total_pairs = 0
    try:
        # A single read transaction covers every role. Compare the exact database after reading as well.
        if graph.get('database_fingerprint') != database_fingerprint(database):
            return {'status': 'path_union_unverified', 'path_ids': ids, 'basis': 'database_snapshot_changed'}
        with closing(connect_readonly(database)) as connection:
            connection.execute('BEGIN')
            for path in paths:
                pairs = path_pairs(connection, path, maps)
                role = path_role(path).get('role', '').casefold()
                for source, case in pairs:
                    assignments[source][case].add(role)
                total_pairs += len(pairs)
        if graph['database_fingerprint'] != database_fingerprint(database):
            return {'status': 'path_union_unverified', 'path_ids': ids, 'basis': 'database_snapshot_changed'}
    except (sqlite3.Error, ValueError, TypeError, KeyError, OSError) as error:
        return {'status': 'invalid_path_union', 'path_ids': ids, 'basis': type(error).__name__}
    multiple = [cases for cases in assignments.values() if len(cases) > 1]
    distinct_pairs = sum(map(len, assignments.values()))
    result = dict(path_ids=ids, source_occurrences=len(assignments), distinct_pairs=distinct_pairs,
                  repeated_pairs=total_pairs-distinct_pairs, multiple_case_occurrences=len(multiple))
    if not multiple:
        result.update(status='pass', basis='verified_union')
        if not result['repeated_pairs'] and len(assignments) == distinct_pairs:
            result['partition'] = dict(path_ids=ids, source_occurrences=len(assignments),
                                       id=stable_id('history_partition', [graph['database_fingerprint'],
                                            target['id'], definition['id'], ids, len(assignments)]))
        return result
    # A role used for more than one Case, or an unlabelled conflicting route, is still a join conflict.
    authority = []
    for cases in multiple:
        role_names = set().union(*cases.values())
        if '' in role_names or sum(map(len, cases.values())) != len(role_names):
            break
        cited = union_policy(graph, definition, target, role_names)
        if not cited:
            break
        authority.append(cited)
    if len(authority) == len(multiple):
        return dict(result, status='documented_multiple_cases', evidence_ids=sorted(set(authority)))
    return dict(result, status='cross_path_case_conflict')


def verify_explicit_path_unions(graph, database, process_information):
    """PURPOSE: Prove the exact cross-requirement path union for each multiply attributed ED.
    INPUT: Selected PI paths, source EEG and database after any request-local recovery.
    OUTPUT: Per-ED verification receipts. Single paths retain their existing verification.
    """
    selected = {identifier: sorted(set(paths)) for identifier, paths in
                process_information.get('verified_attribution_paths', {}).items() if len(set(paths)) > 1}
    if not selected:
        return {}
    target_id = process_information.get('case_notion_et_id')
    target = next((et for et in graph.get('entity_types', []) if et['id'] == target_id), None)
    definitions = {ed['id']: ed for ed in graph.get('event_definitions', []) if ed['id'] in selected}
    paths = {path['id']: path for path in graph.get('attribution_paths', []) if path.get('to') == target_id}
    receipts = {}
    for identifier, ids in selected.items():
        grouped = [paths[path_id] for path_id in ids if path_id in paths]
        valid = (target and identifier in definitions and len(grouped) == len(ids) and all(
            path.get('event_definition_id') == identifier
            and not path_issues(path.get('joins', []), graph.get('relationships', []))
            and (path.get('validation_status') == 'rule_confirmed_no_occurrences' or (
                path.get('validation_status') == 'valid'
                and (path.get('case_map', {}).get('validation') or {}).get('passed') is True))
            for path in grouped))
        if not valid:
            receipts[identifier] = dict(status='invalid_path_union', path_ids=ids, basis='unverified_pi_path')
        else:
            receipts[identifier] = verify_path_union(graph, database, target, definitions[identifier], grouped)
    return receipts


def role_scope_needs_review(spans, labels):
    """PURPOSE: Flag literal role clauses whose polarity needs semantic review.
    INPUT: Grounded request spans and documented role labels. OUTPUT: Whether a literal role match is unsafe.
    """
    return any(re.search(r"\b(?:except|exclud\w*|rather than|instead of|not|without|other than)\b", span, re.I)
               and any(mentions_role(span, role) for role in labels) for span in spans)


def scope_history_paths(attribution, spans, *, focus='', chosen_ids=None, review_required=False):
    """PURPOSE: Select documented role paths within the analyst's literal requested scope.
    INPUT: Admitted paths, grounded role-scope spans, optional topic or independently reviewed path IDs.
    OUTPUT: Selection status and candidate paths. Whole related history admits the documented role union.
    """
    paths = attribution['paths']
    roles = {path['id']: path_role(path) for path in paths}
    if chosen_ids is not None:
        return 'selected', [path for path in paths if path['id'] in chosen_ids]
    if review_required and any(roles.values()):
        return 'needs_role_review', paths
    named = {identifier for identifier, role in roles.items() if role.get('role') and
             any(mentions_role(span, role['role']) for span in spans)}
    if named:
        return 'selected', [path for path in paths if path['id'] in named]
    distinct = {role.get('step', {}).get('relationship_id') for role in roles.values() if role.get('role')}
    distinct.discard(None)
    if focus and len(distinct) > 1:
        return 'needs_role_review', paths
    return 'selected', paths
