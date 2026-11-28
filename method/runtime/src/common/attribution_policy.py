"""Functional case attribution through verified references, independent of entity identity maps."""

from collections import defaultdict
import re
POLICY = 'verified-functional-reference-simple-path-v4'
MAX_ATTRIBUTION_HOPS = None
DEFAULT_MAX_REVISIONS = 2


def bounded_hops(value):
    """PURPOSE: Normalize legacy depth arguments to the simple-path policy.
    INPUT: Optional historical nonnegative integer. OUTPUT: None (no depth cutoff).
    """
    if value is not None and (type(value) is not int or value < 0):
        raise ValueError('max_hops must be None or a nonnegative legacy integer')
    return None


from src.common.sql_identifiers import quote_identifier


def declared_foreign_key_groups(connection, child_table):
    """PURPOSE: Read declared FKs with an omitted parent column list resolved to the parent's ordered PK.
    INPUT: Open SQLite connection and the child table name; reads PRAGMA metadata only.
    OUTPUT: FK groups ordered by PRAGMA id: {'parent_table', 'columns': [(child_column, parent_column)]}
            in key order. An omitted target stays None only when the parent has no PK of the same arity;
            it is never guessed.
    """
    groups = {}
    for row in connection.execute('PRAGMA foreign_key_list(' + quote_identifier(child_table) + ')'):
        group = groups.setdefault(int(row[0]), {'parent_table': row[2], 'pairs': []})
        group['pairs'].append((int(row[1]), row[3], row[4]))
    result = []
    for _, value in sorted(groups.items()):
        pairs = sorted(value['pairs'])
        if all(right is None for _, _, right in pairs):
            parent_schema = connection.execute(
                'PRAGMA table_info(' + quote_identifier(value['parent_table']) + ')').fetchall()
            parent_key = [row[1] for row in sorted(parent_schema, key=lambda row: row[5]) if row[5]]
            if len(parent_key) == len(pairs):
                pairs = [(position, left, right) for (position, left, _), right in zip(pairs, parent_key)]
        result.append({'parent_table': value['parent_table'],
                       'columns': [(left, right) for _, left, right in pairs]})
    return result


def reference_path_row_states(connection, source_table, joins, target_columns, *,
                              predicate='1=1', parameters=(), row_key_columns=None):
    """PURPOSE: Classify each in-scope source row along one forward reference path with one NULL policy.
    INPUT: Read-only connection, source table (alias s0), ordered child-to-parent joins, target key
           columns on the last table, an optional parameterized row predicate on s0, and the source
           row key. With a row key, counts are per source row even if a non-unique join fans out;
           without one, every hop must match at most one row (PK/UNIQUE targets).
    OUTPUT: {'scope_rows', 'null_reference_rows', 'unmatched_reference_rows', 'matched_rows'}.
            A reference with any NULL component is not attributable through this path (SQLite
            MATCH SIMPLE: such a row is not constrained); it is excluded, never counted as unmatched.
            A fully non-NULL reference with no target row is unmatched.
    """
    parts, states = [quote_identifier(source_table) + ' s0'], []
    alias = 's0'
    for index, join in enumerate(joins, 1):
        nxt = 'j' + str(index)
        left, right = join['left_columns'], join['right_columns']
        parts.append('LEFT JOIN ' + quote_identifier(join['right_table']) + ' ' + nxt + ' ON ' + ' AND '.join(
            alias + '.' + quote_identifier(a) + '=' + nxt + '.' + quote_identifier(b) for a, b in zip(left, right)))
        states.append('WHEN ' + ' OR '.join(alias + '.' + quote_identifier(a) + ' IS NULL' for a in left)
                      + ' THEN 2')
        states.append('WHEN ' + nxt + '.' + quote_identifier(right[0]) + ' IS NULL THEN 1')
        alias = nxt
    states.append('WHEN ' + ' OR '.join(alias + '.' + quote_identifier(c) + ' IS NULL' for c in target_columns)
                  + ' THEN 2')
    # Rank 0 matched, 1 unmatched non-NULL reference, 2 NULL reference; a fanned-out row keeps its best rank.
    rows = ('SELECT ' + ''.join('s0.' + quote_identifier(c) + ' AS k' + str(i) + ', '
                                for i, c in enumerate(row_key_columns or []))
            + 'CASE ' + ' '.join(states) + ' ELSE 0 END AS state FROM ' + ' '.join(parts) + ' WHERE ' + predicate)
    if row_key_columns:
        rows = ('SELECT MIN(state) AS state FROM (' + rows + ') GROUP BY '
                + ', '.join('k' + str(i) for i in range(len(row_key_columns))))
    counts = dict(connection.execute('SELECT state, COUNT(*) FROM (' + rows + ') GROUP BY state',
                                     list(parameters)).fetchall())
    return {'scope_rows': sum(counts.values()), 'null_reference_rows': counts.get(2, 0),
            'unmatched_reference_rows': counts.get(1, 0), 'matched_rows': counts.get(0, 0)}


def forward_adjacency(references):
    """PURPOSE: Expose declared or explicitly documented verified reference steps, forward only.
    INPUT: Native references or runtime relationships. OUTPUT: Child-indexed normalized joins.
    Identity mappings and value overlap alone are not traversal edges; inferred references require explicit DD evidence.
    """
    adjacency = defaultdict(list)
    for reference in references:
        declared = reference.get('kind') == 'declared' or reference.get('declared') is True
        evidence = reference.get('reference_evidence', {})
        inferred = (evidence.get('status') == 'supported' and
                    evidence.get('source') == 'dictionary_reference_definition' and
                    evidence.get('exact_inclusion', 0) >= max(0.95, evidence.get('threshold', 0.95)))
        if not declared and not inferred:
            continue
        child = reference.get('child_table', reference.get('left_table'))
        parent = reference.get('parent_table', reference.get('right_table'))
        pairs = reference.get('columns', [])
        left = reference.get('left_columns', [p[0] for p in pairs])
        right = reference.get('right_columns', [p[1] for p in pairs])
        if not child or not parent or not left or len(left) != len(right):
            continue
        adjacency[child].append({'relationship_id': reference['id'],
            'left_table': child, 'left_columns': list(left), 'right_table': parent,
            'right_columns': list(right), 'direction': 'child_to_parent',
            'declared': declared, **({'reference_evidence': evidence} if evidence else {}),
            'cardinality': reference.get('cardinality', 'N:1')})
    return adjacency


def has_unique_key(connection, table, columns):
    """PURPOSE: Require a real full PK/UNIQUE constraint rather than observed uniqueness.
    INPUT: SQLite connection, table and complete column group.
    OUTPUT: True for a matching primary key or non-partial unique index, including composites.
    """
    info = connection.execute('PRAGMA table_info(' + quote_identifier(table) + ')').fetchall()
    keys = [[r[1] for r in sorted(info, key=lambda r: r[5]) if r[5]]]
    for index in connection.execute('PRAGMA index_list(' + quote_identifier(table) + ')'):
        if index[2] and not index[4]:
            keys.append([r[2] for r in connection.execute(
                'PRAGMA index_info(' + quote_identifier(index[1]) + ')')])
    return bool(columns) and any(len(key) == len(columns) and set(key) == set(columns) for key in keys)


def attribution_adjacency(references):
    """PURPOSE: Add only schema-proved functional reverse FK paths, preserving each FK role.
    INPUT: Reference catalog with child_key_unique facts from the physical schema.
    OUTPUT: Forward steps plus declared parent-to-child steps whose FK columns form a full UNIQUE key.
    """
    adjacency = forward_adjacency(references)
    catalog = {reference['id']: reference for reference in references}
    reverse = []
    for edges in list(adjacency.values()):
        for step in edges:
            if step['declared'] and catalog[step['relationship_id']].get('child_key_unique') is True:
                reverse.append({'relationship_id': step['relationship_id'],
                    'left_table': step['right_table'], 'left_columns': list(step['right_columns']),
                    'right_table': step['left_table'], 'right_columns': list(step['left_columns']),
                    'direction': 'parent_to_child', 'declared': True, 'child_key_unique': True,
                    'cardinality': '1:1'})
    for step in reverse:
        adjacency[step['left_table']].append(step)
    return adjacency


def path_issues(joins, references=None):
    """PURPOSE: Reject nonfunctional, unsupported or fabricated attribution steps and repeated tables.
    INPUT: Ordered join list and optional immutable reference catalog. OUTPUT: Issue strings.
    A zero-hop source/identity projection is allowed; no instance identity is inferred here.
    """
    known = None
    if references is not None:
        known = {(e['relationship_id'], e['direction']): e
                 for edges in attribution_adjacency(references).values() for e in edges}
    issues = []
    visited = {joins[0].get('left_table')} if joins else set()
    previous = None
    for index, step in enumerate(joins):
        prefix = f'attribution hop {index}'
        inferred = step.get('reference_evidence', {}).get('status') == 'supported'
        forward = step.get('direction') == 'child_to_parent' and (step.get('declared') is True or inferred)
        reverse = (step.get('direction') == 'parent_to_child' and step.get('declared') is True
                   and step.get('child_key_unique') is True)
        if not (forward or reverse):
            issues.append(prefix + ': forward reference or declared UNIQUE reverse FK required')
        if previous is not None and step.get('left_table') != previous:
            issues.append(prefix + ': disconnected path')
        previous = step.get('right_table')
        if previous in visited:
            issues.append(prefix + ': repeated table')
        visited.add(previous)
        if known is not None:
            expected = known.get((step.get('relationship_id'), step.get('direction')))
            if expected is None or any(step.get(k, {}) != expected.get(k, {}) for k in (
                    'left_table', 'left_columns', 'right_table', 'right_columns', 'declared', 'reference_evidence')):
                issues.append(prefix + ': not a catalogued functional reference')
    return issues


def database_path_issues(connection, joins):
    """PURPOSE: Verify ES joins against actual keys and FK constraints or recomputed documented inclusion.
    INPUT: Read-only SQLite connection and ordered steps. OUTPUT: Schema or recomputed inferred-reference failures.
    No data writes, Gold or model calls; composite key order and partial indexes are respected.
    """
    return path_issues(joins) + reference_constraint_issues(connection, joins)


def reference_constraint_issues(connection, joins):
    """PURPOSE: Check physical references independently of event-path traversal.
    INPUT: DB connection and catalogued forward edges. OUTPUT: FK/key or documented-inclusion failures.
    """
    issues = []
    def quote(name):
        """PURPOSE: Quote a schema identifier for PRAGMA. INPUT: Name. OUTPUT: Escaped SQL identifier."""
        return '"' + str(name).replace('"', '""') + '"'
    for index, step in enumerate(joins):
        reverse = step.get('direction') == 'parent_to_child'
        child = step.get('right_table') if reverse else step.get('left_table')
        parent = step.get('left_table') if reverse else step.get('right_table')
        left = step.get('right_columns', []) if reverse else step.get('left_columns', [])
        right = step.get('left_columns', []) if reverse else step.get('right_columns', [])
        info = connection.execute('PRAGMA table_info(' + quote(parent) + ')').fetchall()
        pk = [r[1] for r in sorted(info, key=lambda r: r[5]) if r[5]]
        keys = [pk] if pk else []
        for row in connection.execute('PRAGMA index_list(' + quote(parent) + ')').fetchall():
            if row[2] and not row[4]:
                keys.append([c[2] for c in connection.execute('PRAGMA index_info(' + quote(row[1]) + ')')])
        matches = [group['parent_table'] == parent and [c for c, _ in group['columns']] == left and
                   [p for _, p in group['columns']] == right
                   for group in declared_foreign_key_groups(connection, child)]
        if reverse and (step.get('declared') is not True or not any(matches)
                        or not has_unique_key(connection, child, left)):
            issues.append(f'attribution hop {index}: reverse traversal requires actual UNIQUE FK columns')
        target_key_valid = any(len(right)==len(key) and set(right)==set(key) for key in keys)
        inferred_valid = False
        evidence = step.get('reference_evidence', {})
        if not any(matches) and target_key_valid and evidence.get('status') == 'supported':
            source_columns = {r[1] for r in connection.execute('PRAGMA table_info(' + quote(child) + ')')}
            shape_matches = (evidence.get('source_table') == child and evidence.get('source_columns') == left and
                             evidence.get('target_table') == parent and evidence.get('target_columns') == right)
            quote_text = evidence.get('quote', '')
            semantic_support = (evidence.get('source') == 'dictionary_reference_definition' and
                re.search(r'\b(references?|refers? to)\b', quote_text, re.I) and
                re.search(r'(?<!\w)' + re.escape(parent) + r'(?!\w)', quote_text, re.I))
            if shape_matches and semantic_support and set(left) <= source_columns:
                source_projection = ','.join(quote(c) for c in left)
                target_projection = ','.join(quote(c) for c in right)
                nonnull = ' AND '.join(quote(c)+' IS NOT NULL' for c in left)
                target_nonnull = ' AND '.join(quote(c)+' IS NOT NULL' for c in right)
                source = {tuple(row) for row in connection.execute(
                    'SELECT DISTINCT '+source_projection+' FROM '+quote(child)+' WHERE '+nonnull)}
                target = {tuple(row) for row in connection.execute(
                    'SELECT DISTINCT '+target_projection+' FROM '+quote(parent)+' WHERE '+target_nonnull)}
                ratio = len(source & target)/len(source) if source else 0
                inferred_valid = ratio >= max(0.95, evidence.get('threshold', 0.95))
        if not left or not target_key_valid or not (any(matches) or inferred_valid):
            issues.append(f'attribution hop {index}: actual FK→PK/UNIQUE constraint missing')
    return issues


def role_words(text):
    """PURPOSE: Normalize role labels and request phrases. INPUT: Text from public evidence. OUTPUT: Ordered words."""
    return re.findall(r"[^\W_]+", str(text or '').casefold())


def mentions_role(text, role):
    """PURPOSE: Match a complete documented role label within request terms.
    INPUT: Text and role label. OUTPUT: Whether the consecutive label words occur.
    """
    words, label = role_words(text), role_words(role)
    return bool(label) and any(words[i:i+len(label)] == label for i in range(len(words)))


def documented_reference_roles(adjacency, dictionary):
    """PURPOSE: Identify distinct roles of sibling, declared UNIQUE foreign keys.
    INPUT: Functional directed references and normalized public DD.
    OUTPUT: Role receipts keyed by reference ID. Every sibling must have distinct documented evidence.
    """
    columns = {(c['table'], c['column']): c for c in dictionary.get('columns', [])}
    groups = defaultdict(list)
    for steps in adjacency.values():
        for step in steps:
            if step['direction'] == 'parent_to_child':
                groups[step['left_table'], step['right_table'], tuple(step['left_columns'])].append(step)
    receipts = {}
    for siblings in groups.values():
        if len(siblings) < 2:
            continue
        tokens = [list(dict.fromkeys(w for col in edge['right_columns'] for w in role_words(col)))
                  for edge in siblings]
        roles = []
        for index, step in enumerate(siblings):
            records = [columns.get((step['right_table'], col), {}) for col in step['right_columns']]
            phrases = [c.get('definition', '') for c in records if c.get('definition')]
            quote = ' '.join(phrases)
            explicit = {c['reference_role'] for c in records if c.get('reference_role')}
            if len(explicit) == 1:
                label = ' '.join(role_words(next(iter(explicit))))
            else:
                other_words = {w for i, words in enumerate(tokens) if i != index for w in words}
                documented_words = set(role_words(quote))
                label = ' '.join(w for w in tokens[index] if w not in other_words and w in documented_words)
            if not label or not quote:
                break
            roles.append(dict(role=label, dictionary_id=next((c.get('id') for c in records if c.get('id')), None),
                              quote=quote, step=step, alternatives=[other for other in siblings if other is not step]))
        if len(roles) == len(siblings) and len({item['role'] for item in roles}) == len(siblings):
            receipts.update({item['step']['relationship_id']: item for item in roles})
    return receipts


def reference_exists_sql(alias, steps):
    """PURPOSE: Test a declared reference chain by correlation without changing case identity.
    INPUT: SQL source alias and nonempty, independently validated oriented steps. OUTPUT: EXISTS predicate.
    """
    names = [f'rs{i}' for i in range(len(steps))]
    first = steps[0]

    def match(left, right, step):
        """PURPOSE: Compile equality on ordered keys. INPUT: Aliases and reference step. OUTPUT: JOIN expression."""
        return ' AND '.join(f'{left}.{quote_identifier(a)}={right}.{quote_identifier(b)}'
                            for a, b in zip(step['left_columns'], step['right_columns'], strict=True))

    tables = f"{quote_identifier(first['right_table'])} {names[0]}"
    for i, step in enumerate(steps[1:], 1):
        tables += f" JOIN {quote_identifier(step['right_table'])} {names[i]} ON {match(names[i-1], names[i], step)}"
    return f'EXISTS (SELECT 1 FROM {tables} WHERE {match(alias, names[0], first)})'


def role_source_scope_sql(scope, alias='s0'):
    """PURPOSE: Exclude rows proved to belong only to the complementary relationship role.
    INPUT: Source prefix and supported role/complement references. OUTPUT: SQL retaining unknown membership for validation.
    """
    prefix = scope['prefix']
    others = ' OR '.join(reference_exists_sql(alias, [*prefix, other])
                         for other in role_scope_alternatives(scope))
    selected = reference_exists_sql(alias, [*prefix, scope['step']])
    return f'(NOT ({others}) OR {selected})'


def role_scope_steps(condition):
    """PURPOSE: Find relationship restrictions in a structured event predicate.
    INPUT: ES condition tree. OUTPUT: Role restriction records from conjunctions.
    """
    if not condition:
        return []
    if condition.get('kind') == 'reference_role':
        return [condition]
    return [scope for term in condition.get('conditions', []) for scope in role_scope_steps(term)]


def role_scope_alternatives(scope):
    """PURPOSE: Read sibling reference evidence. INPUT: Current or legacy scope. OUTPUT: Alternative steps."""
    return scope.get('alternatives') or ([scope['other']] if scope.get('other') else [])


def role_scope_issues(scope, source_path, references=None):
    """PURPOSE: Validate the scope against the source path and its complementary FK.
    INPUT: Structured role scope, expected source path and optional graph relationships.
    OUTPUT: Structural errors for malformed, ungrounded or misoriented restrictions.
    """
    prefix, step = scope.get('prefix'), scope.get('step')
    alternatives = role_scope_alternatives(scope)
    family = ('direction', 'left_table', 'left_columns', 'right_table')
    if (not isinstance(prefix, list) or not isinstance(step, dict) or not alternatives
            or [*prefix, step] != source_path[:len(prefix)+1]
            or step.get('direction') != 'parent_to_child'
            or any(not isinstance(other, dict) or step.get('relationship_id') == other.get('relationship_id')
                   or any(step.get(key) != other.get(key) for key in family) for other in alternatives)):
        return ['Role source scope does not match the selected attribution path']
    return [issue for edge in [step, *alternatives] for issue in path_issues([*prefix, edge], references)]
