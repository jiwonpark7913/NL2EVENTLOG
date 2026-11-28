"""Check the entire frozen PI dependency set before materialization."""

from src.common.graph_identifiers import content_hash
from src.common.occurrence_conditions import occurrence_terms
from src.common.attribution_policy import forward_adjacency, path_issues

CONTRACT_VERSION = 'verified-pi-v2-integrated'
PI_FIELDS = ('case_notion_et_id', 'request_mode', 'case_scope', 'scope_policy',
             'selected_event_definition_ids', 'verified_attribution_paths', 'verified_attribution_partitions')
ED_FIELDS = ('source_table', 'source_kind', 'source_row_key', 'ts_id', 'timestamp_candidates',
             'row_selection', 'activity_column', 'raw_values', 'documented_source_conditions',
             'occurrence_identity_rule_id')
PATH_FIELDS = ('to', 'from_table', 'joins', 'target_table_key_id', 'case_role', 'role_scope',
               'cardinality', 'validation_status', 'entity_identity_validation')
VALID_PATH = {'valid', 'rule_confirmed_no_occurrences'}


def _record_hashes(records, identifiers, fields):
    """PURPOSE: Bind selected evidence fields independently of index storage details.
    INPUT: Record inventory, selected IDs, and contract keys. OUTPUT: ID to stable digest.
    """
    return {record['id']: content_hash({key: record.get(key) for key in fields})
            for record in records if record['id'] in identifiers}


def freeze_execution_contract(graph, query):
    """PURPOSE: Record the executable semantics accepted by PI before physical hydration.
    INPUT: Active semantic EEG and ready query. OUTPUT: Detached contract version and hashes.
    """
    info = query.get('process_information') or {}
    case_id = info.get('case_notion_et_id')
    selected = set(info.get('selected_event_definition_ids', []))
    paths = {identifier for group in (info.get('verified_attribution_paths') or {}).values()
             for identifier in group}
    return {
        'version': CONTRACT_VERSION,
        'pi': content_hash({key: info.get(key) for key in PI_FIELDS}),
        'case': _record_hashes(graph.get('entity_types', []), {case_id}, ('population',)),
        'definitions': _record_hashes(graph.get('event_definitions', []), selected, ED_FIELDS),
        'paths': _record_hashes(graph.get('attribution_paths', []), paths, PATH_FIELDS),
    }



def join_shape(join):
    """PURPOSE: Identify a declared FK independently of discovery and projection IDs.
    INPUT: Oriented join. OUTPUT: Source/target tables and ordered column pairs.
    """
    return join['left_table'], tuple(join['left_columns']), join['right_table'], tuple(join['right_columns'])

def _strict_dependencies(graph, query, view, info, paths, selected):
    """PURPOSE: Verify frozen PI evidence and the physical columns required by selected rules.
    INPUT: Full execution projection and PI fields. OUTPUT: Precise missing or mismatched dependencies.
    """
    issues = []
    expected = query.get('execution_contract') or {}
    actual = freeze_execution_contract(graph, query)
    for key, value in actual.items():
        if expected.get(key) != value:
            issues.append({'kind': 'frozen_' + key + '_mismatch'})
    nested = view.get('process_information') or {}
    if any(info.get(key) != nested.get(key) for key in PI_FIELDS):
        issues.append({'kind': 'process_view_contract_mismatch'})
    if set(selected) != paths.keys() or any(not ids for ids in paths.values()):
        issues.append({'kind': 'verified_attribution_paths_required'})
    tables = {row['name']: {column['name'] for column in row['columns']}
              for row in graph.get('tables', [])}
    identities = {rule['id']: rule for rule in graph.get('occurrence_identity_rules', [])}
    foreign_keys = {join_shape(join) for joins in forward_adjacency(graph.get('relationships', [])).values()
                    for join in joins if join['declared']}
    for ed in graph.get('event_definitions', []):
        if ed['id'] not in selected:
            continue
        table = ed.get('source_table')
        identity = identities.get(ed.get('occurrence_identity_rule_id'))
        if not ed.get('source_row_key') or not identity or identity.get('event_definition_id') != ed['id']:
            issues.append({'kind': 'occurrence_key', 'id': ed['id']})
        required = {table: set(ed.get('source_row_key') or [])}
        for timestamp in ed.get('timestamp_candidates', []):
            if timestamp.get('id') == ed.get('ts_id'):
                required[table].update(timestamp.get('columns') or ([timestamp['column']] if timestamp.get('column') else []))
        if not any(t.get('id') == ed.get('ts_id') for t in ed.get('timestamp_candidates', [])):
            issues.append({'kind': 'selected_timestamp', 'id': ed['id']})
        for condition in ed.get('documented_source_conditions') or []:
            for term in occurrence_terms(condition):
                if term['kind'] == 'state_transition':
                    required[table].update([term.get('column'), *term.get('partition_by', []), *term.get('order_by', [])])
                else:
                    joins = term.get('joins') or []
                    if not joins or 'value' not in term:
                        issues.append({'kind': 'relational_predicate', 'id': ed['id']})
                        continue
                    for join in joins:
                        if join_shape(join) not in foreign_keys:
                            issues.append({'kind': 'occurrence_lookup_fk', 'id': ed['id']})
                        required.setdefault(join['left_table'], set()).update(join['left_columns'])
                        required.setdefault(join['right_table'], set()).update(join['right_columns'])
                    required[joins[-1]['right_table']].add(term.get('column'))
        for name, columns in required.items():
            if name not in tables or not columns <= tables[name]:
                issues.append({'kind': 'source_table_or_columns', 'id': ed['id'], 'table': name})
    case = next((e for e in graph.get('entity_types', []) if e['id'] == info.get('case_notion_et_id')), {})
    for member in (case.get('population') or {}).get('maps', []):
        if (not (member.get('identity_scope_id') or member.get('namespace_id'))
                or not set(member.get('key_columns', [])) <= tables.get(member.get('table'), set())):
            issues.append({'kind': 'case_namespace_or_key', 'id': member.get('representation_id')})
    chosen = {identifier for ids in paths.values() for identifier in ids}
    for path in graph.get('attribution_paths', []):
        if path['id'] in chosen and path_issues(path.get('joins', []), graph.get('relationships', [])):
            issues.append({'kind': 'attribution_relationship', 'id': path['id']})
    return issues


def execution_dependencies(graph, query):
    """PURPOSE: Reject incomplete lookups before they silently shrink verified extraction scope.
    INPUT: Request-local executable EEG projection and validated PI, or an unresolved query.
    OUTPUT: Dependency status, missing element receipts and sizes. No semantic decisions are made.
    """
    if query.get('status') != 'ready':
        return {'status': 'not_applicable', 'missing': [], 'counts': {}}
    return bound_execution_dependencies(graph, query)


def bound_execution_dependencies(graph, query):
    """PURPOSE: Check a concrete physical dependency contract independently of semantic approval.
    INPUT: Executable EEG projection and fixed PI with optional frozen dependency hashes.
    OUTPUT: Missing dependencies, counts and structural status.
    """
    report = {'status': 'not_applicable', 'missing': [], 'counts': {}}
    view = query.get('process_view') or {}
    information = query.get('process_information') or view.get('process_information') or {}
    case = information.get('case_notion_et_id') or view.get('target_ot_id')
    selected = information.get('selected_event_definition_ids', view.get('event_definitions', []))
    strict = query.get('pi_contract_version') == CONTRACT_VERSION or 'execution_contract' in query
    paths = information.get('verified_attribution_paths') or {}
    if strict:
        report['missing'].extend(_strict_dependencies(graph, query, view, information, paths, selected))
    if 'event_definitions' in view and set(view['event_definitions']) != set(selected):
        report['missing'].append({'kind': 'pi_event_scope_mismatch'})
    if view.get('target_ot_id') and view['target_ot_id'] != case:
        report['missing'].append({'kind': 'pi_case_scope_mismatch'})
    definitions = {item['id']: item for item in graph.get('event_definitions', [])}
    cases = {item['id']: item for item in graph.get('entity_types', [])}
    index = {item['id']: item for item in graph.get('attribution_paths', [])}
    key_records = {item['id'] for item in graph.get('table_key_records', [])}
    population = (cases.get(case) or {}).get('population') or {}
    if population.get('status') != 'valid':
        report['missing'].append({'kind': 'case_population', 'id': case})
    for provider in population.get('maps', []):
        if provider['representation_id'] not in key_records:
            report['missing'].append({'kind': 'case_representation', 'id': provider['representation_id']})
    for identifier in selected:
        definition = definitions.get(identifier)
        if not definition:
            report['missing'].append({'kind': 'event_definition', 'id': identifier})
            continue
        if not definition.get('timestamp_candidates'):
            report['missing'].append({'kind': 'timestamp', 'event_definition_id': identifier})
        expected = paths.get(identifier)
        if expected is None and not strict:
            expected = [p['id'] for p in index.values()
                        if p.get('event_definition_id') == identifier and p.get('to') == case
                        and p.get('validation_status') in VALID_PATH]
        if not expected:
            report['missing'].append({'kind': 'attribution', 'event_definition_id': identifier})
        for path_id in expected or ():
            rule = index.get(path_id)
            if (rule is None or rule.get('event_definition_id') != identifier or rule.get('to') != case
                    or rule.get('validation_status') not in VALID_PATH
                    or rule.get('target_table_key_id') not in key_records or 'joins' not in rule):
                report['missing'].append({'kind': 'attribution_path', 'id': path_id,
                                          'event_definition_id': identifier})
    report['status'] = 'incomplete' if report['missing'] else 'complete'
    report['counts'] = {'selected_events': len(selected), 'case_representations': len(population.get('maps', [])),
                        'verified_attribution_paths': len({rule for per_ed in paths.values() for rule in per_ed})}
    return report
