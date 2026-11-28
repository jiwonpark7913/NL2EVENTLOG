"""Compile and verify typed predicates for documented relational occurrences."""
from src.common.attribution_policy import database_path_issues, has_unique_key
from src.common.sql_identifiers import quote_identifier as qi


def transition_sql(term, alias):
    """PURPOSE: Compare the current row to its immediate predecessor.
    INPUT: Verified state history partition, sequence, and initial-state policy. OUTPUT: SQL predicate.
    """
    prior = 'previous_state'
    partition, order = term['partition_by'], term['order_by']
    column = qi(term['column'])
    same = ' AND '.join(f'{prior}.{qi(c)} = {alias}.{qi(c)}' for c in partition)
    left, right = (', '.join(f'{side}.{qi(c)}' for c in order) for side in (prior, alias))
    descending = ', '.join(f'{prior}.{qi(c)} DESC' for c in order)
    nonnull = ' AND '.join(f'{alias}.{qi(c)} IS NOT NULL' for c in [*partition, *order])
    compare = f'({prior}.{column} IS NOT NULL AND {prior}.{column} <> {alias}.{column})'
    previous = (f'(SELECT {compare} FROM {qi(term["table"])} {prior} WHERE {same}'
                f' AND ({left}) < ({right}) ORDER BY {descending} LIMIT 1)')
    initial = int(term.get('initial_is_transition') is True)
    return f'({nonnull} AND COALESCE({previous}, {initial}) = 1)'


def related_rows(term, alias):
    """PURPOSE: Correlate an occurrence to a verified functional FK chain.
    INPUT: Declared oriented joins, terminal column and outer alias.
    OUTPUT: FROM text, correlation predicate and terminal expression.
    """
    joins = term['joins']
    first = joins[0]
    from_sql = f'{qi(first["right_table"])} related_0'
    correlation = ' AND '.join(f'{alias}.{qi(a)} = related_0.{qi(b)}'
                               for a,b in zip(first['left_columns'], first['right_columns'], strict=True))
    for index, step in enumerate(joins[1:], 1):
        equal = ' AND '.join(f'related_{index-1}.{qi(a)} = related_{index}.{qi(b)}'
                             for a,b in zip(step['left_columns'], step['right_columns'], strict=True))
        from_sql += f' JOIN {qi(step["right_table"])} related_{index} ON {equal}'
    return from_sql, correlation, f'related_{len(joins)-1}.{qi(term["column"])}'


def occurrence_terms(condition):
    """PURPOSE: Enumerate the typed relational terms in an optional conjunction. INPUT: Predicate. OUTPUT: List."""
    if not condition:
        return []
    if condition.get('kind') == 'and':
        return [term for item in condition.get('conditions', []) for term in occurrence_terms(item)]
    return [condition] if condition.get('kind') in {'state_transition','related_value'} else []


def occurrence_condition_issues(connection, table, condition):
    """PURPOSE: Verify relational occurrence predicates against physical keys and columns.
    INPUT: Read-only SQLite, source table and structured predicate. OUTPUT: List of validation issues.
    """
    issues = []
    for term in occurrence_terms(condition):
        if term['kind'] == 'state_transition':
            columns = {row[1] for row in connection.execute(f'PRAGMA table_info({qi(table)})')}
            partition = term.get('partition_by') or []
            order = term.get('order_by') or []
            declared = term.get('order_key') or []
            ordered_columns = set(partition + order)
            if (term.get('table') != table or not partition or not order
                    or not ordered_columns | {term.get('column')} <= columns):
                issues.append('invalid state history columns')
                continue
            keys = [order, list(dict.fromkeys(partition + order))]
            if declared and set(declared) <= ordered_columns:
                keys.append(declared)
            if not any(has_unique_key(connection, table, key) for key in keys):
                issues.append('state history order requires a declared unique key')
            null = ' OR '.join(f'{qi(column)} IS NULL' for column in sorted(ordered_columns))
            if connection.execute(f'SELECT 1 FROM {qi(table)} WHERE {null} LIMIT 1').fetchone():
                issues.append('state history partition and order contain NULL coordinates')
        else:
            joins = term.get('joins') or []
            if not joins or joins[0].get('left_table') != table or any(
                    not j.get('declared') or j.get('direction') != 'child_to_parent' for j in joins):
                issues.append('occurrence lookup requires a declared forward FK chain')
                continue
            issues.extend(database_path_issues(connection, joins))
            columns = {row[1] for row in connection.execute(f'PRAGMA table_info({qi(joins[-1]["right_table"])})')}
            if term.get('column') not in columns or term.get('value') is None:
                issues.append('occurrence lookup requires an existing column and a non-null value')
    return issues
