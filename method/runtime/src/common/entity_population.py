"""Shared ES v6 entity-population contracts and deterministic case expressions."""

from __future__ import annotations
from copy import deepcopy
from contextlib import closing
from src.common.entity_identity import identity_scope_id
import sqlite3
from src.common.database_io import connect_readonly
from src.common.sql_identifiers import quote_identifier
from src.common.attribution_policy import (
    attribution_adjacency, database_path_issues, documented_reference_roles, path_issues, reference_exists_sql,
)


def member_cases(case):
    """PURPOSE: Expand one logical ET candidate into physical probe targets, retaining one selection ID.
    INPUT: Case candidate with optional validated population. OUTPUT: Physical member case bindings.
    """
    population = case.get('population')
    if not population:
        return [case]
    return [{**case, 'table': m['table'], 'columns': list(m['key_columns']),
             'table_key_id': m['representation_id'], 'entity_instance_map_id': m['id']}
            for m in population['maps']]


def case_expression(case, alias):
    """PURPOSE: Encode ET/internal collision component/typed ordered keys without delimiter or coercion collisions.
    INPUT: Physical member binding and SQL alias. OUTPUT: SQL expression or None for legacy case IDs.
    """
    population = case.get('population')
    if not population:
        return None
    mapping = next((m for m in population['maps'] if m['table'] == case['table'] and
                    m['key_columns'] == case['columns']), None)
    if mapping is None:
        raise ValueError('Physical case member is not in the frozen entity population')
    literal = lambda v: "'" + str(v).replace("'", "''") + "'"
    keys = [f'{alias}.{quote_identifier(c)}' for c in mapping['key_columns']]
    typed = 'json_array(' + ','.join(f'json_array(typeof({key}),{key})' for key in keys) + ')'
    return f'json_array({literal(population["entity_type_id"])},{literal(identity_scope_id(mapping))},{typed})'


def source_case(source, case):
    """PURPOSE: Resolve a v6 branch's target Table while preserving the global ET population.
    INPUT: ES Event Source and logical case. OUTPUT: Physical per-source case binding.
    """
    if not case.get('population'):
        return case
    anchor = source.get('case_attribution', {}).get('anchor') or {}
    member = {**case, **{k: deepcopy(anchor[k]) for k in ('table', 'columns', 'table_key_id') if k in anchor}}
    mapping = next((m for m in case['population']['maps'] if m['table'] == member['table'] and
                    m['key_columns'] == member['columns']), None)
    if mapping:
        member.update(table_key_id=mapping['representation_id'], entity_instance_map_id=mapping['id'])
    return member


def upgrade_entity_es(es):
    """PURPOSE: Mark a physically materialized ES as v6 only when it carries an ET population.
    INPUT: v5/v6 ES. OUTPUT: Same mutable ES with explicit population version and attribution policy.
    """
    if es.get('case', {}).get('population'):
        es['es_version'] = 6
        es['activity_source_policy'] = 'entity_population'
    return es


def validate_population(es, graph=None, database=None):
    """PURPOSE: Validate frozen population structure/evidence and optionally actual key domains.
    INPUT: ES, optional EG and live DB. OUTPUT: Independent contract/live statuses and issues.
    Preflight never marks unexecuted live validation as pass.
    """
    population = es.get('case', {}).get('population')
    if not population:
        return {'contract_status': 'fail' if es.get('es_version') == 6 else 'not_run',
                'live_status': 'not_run', 'issues': ['ES v6 requires an entity population'] if es.get('es_version') == 6 else []}
    required = {'id','representation_id','entity_type_id','table','key_columns', 'validation'}
    if (not isinstance(population, dict) or not isinstance(population.get('maps'), list) or
            any(not isinstance(m,dict) or not required <= set(m) for m in population.get('maps', []))):
        return {'contract_status':'fail','live_status':'not_run','issues':['Malformed entity population contract']}
    issues = []
    if es.get('es_version') != 6 or population.get('status') != 'valid' or not population.get('maps'):
        issues.append('Entity population is not an accepted ES v6 contract')
    if population.get('entity_type_id') != es['case'].get('entity_type_id'):
        issues.append('Entity population type does not match the selected case type')
    frozen = es.get('process_view', {}).get('entity_population_contract')
    if frozen is not None and frozen != population:
        issues.append('Entity population differs from Frozen PI')
    selection = es.get('case_selection', {'kind': 'all_cases'})
    scoped = selection.get('kind') == 'reference_role'
    step = selection.get('step') if scoped else None
    maps = population.get('maps', [])
    pi = es.get('process_view', {}).get('process_information') or {}
    frozen_scope = pi.get('case_scope')
    if frozen_scope and selection != frozen_scope:
        issues.append('Case selection differs from the frozen PI role scope')
    if scoped:
        if (len(maps) != 1 or not isinstance(step, dict) or step.get('left_table') != maps[0]['table']
                or step.get('direction') != 'parent_to_child' or path_issues([step])
                or frozen_scope != selection):
            issues.append('Case role scope does not match the frozen Entity population')
        elif graph is not None:
            references = graph.get('relationships', [])
            known = documented_reference_roles(attribution_adjacency(references), graph.get('data_dictionary') or {})
            role = known.get(step.get('relationship_id')) or {}
            if path_issues([step], references) or role.get('role') != selection.get('role'):
                issues.append('Case role scope has no verified reference and dictionary evidence')
    elif population.get('selection_independent') and selection.get('kind') != 'all_cases':
        issues.append('The current Entity population contract does not permit this case-condition filter')
    if len({m.get('representation_id') for m in maps}) != len(maps):
        issues.append('Representation has multiple primary population mappings')
    for mapping in maps:
        try:
            identity_scope_id(mapping)
        except ValueError:
            issues.append('Invalid internal identity scope aliases')
        if mapping.get('entity_type_id') != population.get('entity_type_id'):
            issues.append('Invalid map entity type')
        if mapping.get('mapping_kind') != 'direct_key' or not mapping.get('key_columns') or mapping.get('scope') != 'all_rows':
            issues.append('Unsupported entity instance mapping')
        if mapping.get('validation', {}).get('status') != 'pass':
            issues.append('Unvalidated entity instance mapping')
    if graph is not None:
        expected = next((p for p in (graph.get('entity_case_populations') or []) if p.get('id') == population.get('id')), None)
        if expected != population:
            issues.append('Entity population changed or is absent from the Evidence Graph')
    for source in es.get('event_sources', {}).values():
        if source.get('encoding') == 'json':
            issues.append('ES v6 JSON event arrays require a supported explicit entity mapping')
        member = source_case(source, es['case'])
        matched = next((m for m in maps if m['table'] == member.get('table') and m['key_columns'] == member.get('columns')), None)
        if matched is None:
            issues.append('Source attribution is outside the selected entity population')
        elif source.get('case_attribution', {}).get('entity_instance_map_id') != matched['id']:
            issues.append('Source instance mapping is absent or changed')
    contract_status = 'fail' if issues else 'pass'
    live = 'not_run'
    if database is not None and not issues:
        live = 'pass'
        try:
            with closing(connect_readonly(database)) as connection:
                if scoped:
                    scope_issues = database_path_issues(connection, [step])
                    if scope_issues:
                        live = 'fail'
                        issues.extend(scope_issues)
                for m in maps:
                    table = quote_identifier(m['table']); cols = ','.join(quote_identifier(c) for c in m['key_columns'])
                    nulls = ' OR '.join(quote_identifier(c)+' IS NULL' for c in m['key_columns'])
                    total = connection.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
                    distinct = connection.execute(f'SELECT COUNT(*) FROM (SELECT DISTINCT {cols} FROM {table})').fetchone()[0]
                    null_count = connection.execute(f'SELECT COUNT(*) FROM {table} WHERE {nulls}').fetchone()[0]
                    if total != distinct or null_count:
                        live = 'fail'; issues.append('Live entity key is null or nonunique: ' + m['id'])
        except sqlite3.Error as error:
            live = 'fail'
            issues.append('Live entity population validation failed: ' + str(error))
    return {'contract_status': contract_status, 'live_status': live, 'issues': issues}


def population_cte(case, selection=None):
    """PURPOSE: Compile DISTINCT UNION over all validated representations without materializing graph instances.
    INPUT: Logical ET case and optional validated role selection. OUTPUT: CTE text or None for a legacy case.
    """
    if not case.get('population'):
        return None
    branches = [f'SELECT {case_expression(member, "ec")} AS case_id FROM '
                f'{quote_identifier(member["table"])} ec' for member in member_cases(case)]
    if (selection or {}).get('kind') == 'reference_role':
        branches[0] += ' WHERE ' + reference_exists_sql('ec', [selection['step']])
    return 'entity_cases AS (\n' + '\nUNION\n'.join(branches) + '\n)'
