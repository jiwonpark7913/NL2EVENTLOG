"""Source-centred candidate retrieval with measured, direction-aware diagnostics."""

from __future__ import annotations
from src.common.attribution_policy import MAX_ATTRIBUTION_HOPS, bounded_hops
import copy
import hashlib
import json
import sqlite3
import time
from src.common.attribution_policy import attribution_adjacency, path_issues
from contextlib import closing
from collections import defaultdict, deque
from src.common.database_io import connect_readonly
from src.common.schema_metadata import normalize, stable_id, database_fingerprint, event_source_condition, timestamp_columns
from src.common.sql_identifiers import quote_identifier as qi
from src.step3_execute.compile_event_log_sql import _timestamp, _json_key, _from, _condition as compile_source_condition
from src.step3_execute.profile_temporal_evidence import build_temporal_evidence, TemporalProbeUnavailable


def view_card(query):
    """PURPOSE: Resolve the exact selected process-view card.
    INPUT: Parsed query with process-view seeds and V_q.
    OUTPUT: Matching input-K card, or an empty dictionary.
    """
    wanted = query['V_q'].get('process_view_id')
    candidate_id = query['V_q'].get('process_view_candidate_id')
    return next((v['card'] for v in query['seeds']['process_views']
                 if v['process_view'] == wanted or v.get('candidate_id') == candidate_id), {})


def _candidate_semantic_context(graph, binding, timestamp):
    """PURPOSE: Attach row/time role and alternative-representation evidence to a candidate.
    INPUT: Evidence graph, one physical activity binding and timestamp candidate.
    OUTPUT: Structured context and evidence records; hypotheses never remove candidates.
    """
    evidence_graph = graph.get('evidence_graph', {})
    table_role = next((
        item for item in evidence_graph.get(
            'table_roles', graph.get('table_role_hypotheses', []))
        if item.get('table') == binding.get('source_table')), None)
    timestamp_columns_set = set(timestamp_columns(timestamp))
    representations = []
    for item in evidence_graph.get('event_representations', []):
        observed = item.get('observed', {})
        if observed.get('source') != binding.get('source_table'):
            continue
        if (binding.get('source_kind') == 'row_activity'
                and observed.get('encoding_type') == 'row_categorical'
                and observed.get('carrier') == binding.get('activity_column')):
            representations.append(item)
        elif (binding.get('source_kind') == 'column_event'
              and observed.get('encoding_type') == 'milestone_column'
              and timestamp_columns_set & set(observed.get('columns', []))):
            representations.append(item)
    representation_ids = {item['id'] for item in representations}
    alternatives = [
        item for item in evidence_graph.get('representation_relations', [])
        if (item.get('left_representation_id') in representation_ids
            or item.get('right_representation_id') in representation_ids)
        and (not item.get('matched_labels')
             or binding.get('activity_label', binding.get('activity')) in item.get('matched_labels', []))]
    records = []
    if table_role:
        for hypothesis in table_role.get('interpretation', []):
            records.append({
                'id': stable_id('evidence', [
                    table_role['id'], hypothesis.get('role'), hypothesis.get('source')]),
                'layer': ('model_interpretation'
                          if hypothesis.get('source') == 'model_interpretation'
                          else 'profile'),
                'kind': 'table_role_hypothesis',
                'table_role_id': table_role['id'],
                'role': hypothesis.get('role'),
                'strength': hypothesis.get('strength'),
                'row_meaning': hypothesis.get('row_meaning')})
    for hypothesis in timestamp.get('role_hypotheses', []):
        records.append({
            'id': stable_id('evidence', [
                timestamp.get('id'), hypothesis.get('role'), hypothesis.get('source')]),
            'layer': ('documentation'
                      if hypothesis.get('source') == 'documentation'
                      else 'data_dictionary'
                      if hypothesis.get('source') == 'data_dictionary'
                      else 'model_interpretation'
                      if hypothesis.get('source') == 'model_interpretation'
                      else 'profile'),
            'kind': 'timestamp_role_hypothesis',
            'timestamp_candidate_id': timestamp.get('id'),
            **hypothesis})
    for relation in alternatives:
        records.append({
            'id': stable_id('evidence', [relation['id'], 'alternative']),
            'layer': ('data_dictionary'
                      if relation.get('status') == 'documented' else 'profile'),
            'kind': 'representation_relation',
            'relation_id': relation['id'],
            'relation_type': relation.get('relation_type'),
            'left_representation_id': relation.get('left_representation_id'),
            'right_representation_id': relation.get('right_representation_id'),
            'alternative_group_id': relation.get('alternative_group_id'),
            'preferred_representation_id': relation.get('preferred_representation_id'),
            'candidate_representation_ids': sorted(representation_ids),
            'selection_effect': relation.get('selection_effect'),
            'row_priority': relation.get('row_priority'),
            'shared_columns': list(relation.get('shared_columns', [])),
            'duplicate_risk': relation.get('duplicate_risk'),
            'independent_event': relation.get('independent_event'),
            'semantic_support': relation.get('semantic_support'),
            'status': relation.get('status')})
    return {
        'table_role': table_role,
        'representation_ids': sorted(representation_ids),
        'alternatives': alternatives,
        'timestamp_roles': list(timestamp.get('role_hypotheses', []))}, records


def _cases(graph, query):
    """PURPOSE: Deduplicate physical case anchors across induced and schema evidence.
    INPUT: Schema graph and interpreted query.
    OUTPUT: Case candidates keyed by table plus ordered key columns.
    """
    proposed, result = [], {}
    concept_id = (query.get('process_view', {}).get('target_object_concept_id') or
                  query.get('process_view', {}).get('case_concept_id'))
    concept = next((item for item in graph.get('entity_types', [])
                    if item.get('id') == concept_id), None)
    entity_type_id = (query.get('process_view', {}).get('anchor_entity_type_id') or
                      query.get('V_q', {}).get('anchor_entity_type_id'))
    object_type = next((item for item in graph.get('table_key_records', [])
                        if item.get('id') == entity_type_id), None)
    if object_type:
        identities = object_type.get('identity_candidates', [])
        preferred = next((item for item in identities if item.get('kind') == 'primary_key'),
                         identities[0] if identities else None)
        if preferred:
            proposed.append((object_type['anchor_table'], preferred['columns'], 'schema'))
    card = view_card(query)
    if card.get('case_projection'):
        projection = card['case_projection']
        induced = card.get('origin') == 'discovered'
        return [{'id': stable_id('case_candidate', projection), 'table': '__json_projection__', 'columns': ['value'],
                 'projection': projection, 'evidence': [{
                     'layer': 'profile' if induced else 'documentation',
                     'kind': 'induced_case_projection' if induced else 'case_projection',
                     'source': 'json_reference_profile' if induced else card.get('source'),
                     'id': stable_id('evidence', ['case_projection', projection,
                                                  'profile' if induced else 'documentation'])}]}]
    anchor = card.get('case_anchor', card.get('case_binding', {}))
    if anchor:
        proposed.append((anchor['table'], anchor.get('columns') or [anchor['column']], 'documentation'))
    for table in graph['tables']:
        if normalize(table['name']) == normalize(str(query['V_q'].get('case_notion') or '')):
            for key in table['key_candidates']:
                if key['kind'] == 'primary_key':
                    proposed.append((table['name'], key['columns'], 'schema'))
                    break
    tables = {t['name']: t for t in graph['tables']}
    for table, columns, layer in proposed:
        if table not in tables or not set(columns) <= {c['name'] for c in tables[table]['columns']}:
            continue
        cid = stable_id('case_candidate', [table, columns])
        physical = next((value for value in graph.get('table_key_records', [])
                         if value.get('anchor_table') == table), None)
        item = result.setdefault(cid, {
            'id': cid, 'table': table, 'columns': columns, 'evidence': [],
            'entity_type_id': (concept or physical or {}).get('id'),
            'entity_type_name': ((concept or physical or {}).get('name') or
                                 (concept or physical or {}).get('label') or table),
            'table_key_id': (physical or {}).get('id'),
        })
        item['evidence'].append({'layer': layer, 'kind': 'case_anchor', 'id': stable_id('evidence', [cid, layer])})
    if concept and concept.get('population'):
        for value in result.values():
            value['population'] = concept['population']
    return list(result.values())


def _physical_object_reference(graph, table):
    """PURPOSE: Describe a table row as an Object only when DB Understanding created one.
    INPUT: Evidence Graph and a physical source-table name.
    OUTPUT: Object type/identity metadata or None; no name-only Object is invented.
    """
    physical = next((item for item in graph.get('table_key_records', [])
                     if item.get('anchor_table') == table), None)
    if not physical:
        return None
    concept = next((item for item in graph.get('entity_types', [])
                    if physical.get('id') in item.get('member_object_ids', [])), None)
    logical = concept or physical
    return {
        'table': table,
        'columns': list(physical.get('key_columns') or []),
        'entity_type_id': logical.get('id'),
        'entity_type_name': (logical.get('name') or logical.get('label') or table),
        'table_key_id': physical.get('id'),
        'evidence_basis': 'db_understanding_object_identity',
    }


def _adjacency(graph):
    """PURPOSE: Enumerate traversal directions without merging FK roles.
    INPUT: Graph relationship records.
    OUTPUT: Table-indexed directed edges carrying original FK IDs and composite columns.
    """
    result = attribution_adjacency(graph['relationships'])
    tables = {table['name']: table for table in graph['tables']}
    original = {e['id']: e for e in graph['relationships']}
    for child, edges in result.items():
        for edge in edges:
            ref = original[edge['relationship_id']]
            edge.update(fk_child_table=ref['left_table'], fk_child_columns=ref['left_columns'],
                fk_parent_table=ref['right_table'], fk_parent_columns=ref['right_columns'],
                fk_child_not_null=all(next((c.get('not_null',False) for c in tables[ref['left_table']]['columns']
                    if c['name']==name),False) for name in ref['left_columns']),
                prior_confidence=ref.get('prior_confidence',1.0), bridge_table=False)
    for values in result.values():
        values.sort(key=lambda e: (-e['prior_confidence'], e['relationship_id'], e['right_table']))
    return result


def _paths(adjacency, source, target, max_hops, budget):
    """PURPOSE: Enumerate bounded simple source-to-case paths.
    INPUT: Adjacency, source/target table, hop limit and expansion budget.
    OUTPUT: (paths, truncated); paths are candidates, not semantic ownership proofs.
    """
    max_hops = bounded_hops(max_hops)
    if source == target:
        return [[]], False
    queue, found, examined = deque([(source, [], {source})]), [], 0
    truncated = False
    while queue and examined < budget:
        table, path, seen = queue.popleft()
        examined += 1
        for edge in adjacency.get(table, []):
            nxt = edge['right_table']
            if nxt in seen:
                continue
            extended = [*path, edge]
            if nxt == target:
                found.append(extended)
            else:
                queue.append((nxt, extended, seen | {nxt}))
    return found, truncated or bool(queue)


def classify_attribution_path(path):
    """PURPOSE: Classify a physical source-to-anchor path without claiming lifecycle relevance.
    INPUT: Ordered directed relationship edges from source toward the case anchor.
    OUTPUT: Direction/integrity evidence and cautious anchor-directed classification.
    """
    directions = [edge['direction'] for edge in path]
    declared = all(edge.get('declared') for edge in path)
    bridge_projection = bridge_association = many_case_attribution = False
    anchor_directed = bool(path) and not path_issues(path)
    local = not path
    kind = ('local' if local else 'bridge_projection' if bridge_projection else
            'bridge_association' if bridge_association else
            'anchor_directed' if anchor_directed else 'shared_or_divergent')
    return {'kind': kind, 'anchor_directed': local or anchor_directed,
            'directions': directions, 'hop_count': len(path),
            'declared_edge_count': sum(bool(edge.get('declared')) for edge in path),
            'candidate_edge_count': sum(not edge.get('declared') for edge in path),
            'reverse_edge_count': sum(value == 'parent_to_child' for value in directions),
            'bridge_projection': bridge_projection,
            'bridge_association': bridge_association,
            'many_case_attribution': many_case_attribution,
            'mandatory_child_fk_count': sum(bool(edge.get('fk_child_not_null')) for edge in path),
            'semantics': 'structural attribution evidence, not Process View membership'}


def _coverage(conn, left_table, left_columns, right_table, right_columns):
    """PURPOSE: Measure distinct non-null values participating in a relationship.
    INPUT: Read connection and two table/composite-column sides.
    OUTPUT: Source/matched counts and ratio; empty sources have ratio None.
    """
    a = ','.join(qi(c) for c in left_columns)
    b = ','.join(qi(c) for c in right_columns)
    nn = ' AND '.join(qi(c) + ' IS NOT NULL' for c in left_columns)
    equals = ' AND '.join(f'a.{qi(x)}=b.{qi(y)}' for x, y in zip(left_columns, right_columns))
    sql = (f'WITH a AS (SELECT DISTINCT {a} FROM {qi(left_table)} WHERE {nn}), '
           f'b AS (SELECT DISTINCT {b},1 AS matched FROM {qi(right_table)}) '
           f'SELECT COUNT(*),COALESCE(SUM(b.matched),0) FROM a LEFT JOIN b ON {equals}')
    total, matched = conn.execute(sql).fetchone()
    return {'source_distinct': total, 'matched_distinct': matched, 'ratio': matched / total if total else None}


def _edge_probe(conn, edge, cache):
    """PURPOSE: Separate declared FK integrity from directional traversal coverage.
    INPUT: Read connection, directed relationship and mutable probe cache.
    OUTPUT: Cached diagnostics; reverse sparsity does not reject declared relationships.
    """
    key = edge['relationship_id'] + ':' + edge['left_table']
    if key in cache:
        return cache[key]
    traversal = _coverage(conn, edge['left_table'], edge['left_columns'], edge['right_table'], edge['right_columns'])
    integrity = _coverage(conn, edge['fk_child_table'], edge['fk_child_columns'], edge['fk_parent_table'], edge['fk_parent_columns']) if edge['declared'] else None
    # Reverse sparsity never invalidates a declared relationship. Even dangling
    # references are a data diagnostic; the rule's event-to-case probe owns loss.
    result = {'relationship_id': edge['relationship_id'], 'direction': edge['direction'],
              'traversal_coverage': traversal, 'child_parent_integrity': integrity,
              'accepted': edge['declared'] or traversal['matched_distinct'] > 0}
    cache[key] = result
    return result


def _identity(conn, table, cache, missing_key_policy):
    """PURPOSE: Choose a verified source key, trying alternatives before failure.
    INPUT: Read connection, table/key candidates, mutable cache, reject/drop policy.
    OUTPUT: Uniqueness/null probes and selected key or explicit validation/search failure.
    """
    if table['name'] in cache:
        return cache[table['name']]
    probes, chosen, drop_candidate = [], None, None
    for key in table['key_candidates']:
        cols = ','.join(qi(c) for c in key['columns'])
        null = ' OR '.join(qi(c) + ' IS NULL' for c in key['columns'])
        nulls = conn.execute(f'SELECT COUNT(*) FROM {qi(table["name"])} WHERE {null}').fetchone()[0]
        dup = conn.execute(f'SELECT COUNT(*) FROM (SELECT {cols} FROM {qi(table["name"])} WHERE NOT ({null}) GROUP BY {cols} HAVING COUNT(*)>1)').fetchone()[0]
        probe = {**key, 'null_rows': nulls, 'duplicate_keys': dup}
        probes.append(probe)
        if not dup and not nulls:
            chosen = probe
            break
        if not dup and drop_candidate is None:
            drop_candidate = probe
    if chosen is None and missing_key_policy == 'drop':
        chosen = drop_candidate
    result = {'unique': chosen is not None, 'key_columns': chosen['columns'] if chosen else [],
              'null_rows': chosen['null_rows'] if chosen else None, 'probes': probes,
              'status': 'validated' if chosen else 'validation_failed' if probes else 'coverage_incomplete',
              'reason_code': None if chosen else 'identity_key_invalid' if probes else 'identity_candidates_missing',
              'policy': missing_key_policy}
    cache[table['name']] = result
    return result


def _condition(binding):
    """PURPOSE: Compile only event-defining conditions, not user filters.
    INPUT: Row-activity or column-event binding.
    OUTPUT: Safe SQL predicate on source alias s0.
    """
    return compile_source_condition({'source_condition': event_source_condition(binding)})


def _join_parts(binding, case, path, left=False):
    """PURPOSE: Reuse the compiler's path builder during candidate profiling.
    INPUT: Event binding, target case, enumerated path and LEFT/INNER choice.
    OUTPUT: SQL FROM/JOIN string and final case alias; validates path connectivity.
    """
    rule = {'source': {'table': binding['source_table']}, 'joins': path}
    parts, alias = _from(rule, case, left=left)
    return '\n'.join(parts), alias


class ProbeBudgetExceeded(TemporalProbeUnavailable):
    pass


def _rule_probe(conn, binding, case, path, identity, timestamp, *, max_rows=100000,
                max_vm_steps=2000000, include_observations=False,
                include_partition_keys=False, source_condition=None):
    """PURPOSE: Measure conditioned event-to-case coverage without unbounded joins.
    INPUT: Read connection, binding/case/path/key/time, budgets and optional exact ES predicate.
    OUTPUT: Coverage/multiplicity/digest; optional distinct observations. Budget overflow raises ProbeBudgetExceeded.
    """
    parts, alias = _join_parts(binding, case, path, left=True)
    key = _json_key('s0', identity['key_columns'])
    from src.common.entity_population import case_expression
    case_key = case_expression(case, alias) or _json_key(alias, case['columns'])
    nn_key = ' AND '.join(f's0.{qi(c)} IS NOT NULL' for c in identity['key_columns'])
    nn_case = ' AND '.join(f'{alias}.{qi(c)} IS NOT NULL' for c in case['columns'])
    pred = (compile_source_condition({'source_condition': source_condition})
            if source_condition is not None else _condition(binding))
    ts = _timestamp(timestamp, 's0')
    query = f'SELECT {key},{case_key},({nn_case}),{ts} {parts} WHERE ({pred}) AND ({nn_key})'
    events, links, variants, raw_links = set(), defaultdict(set), set(), 0
    steps = 0
    def progress():
        """PURPOSE: Abort a profile query exceeding its SQLite VM-step budget.
        INPUT: SQLite callback invocation; captured running step counter.
        OUTPUT: 0 to continue or 1 to interrupt; increments only the local counter.
        """
        nonlocal steps
        steps += 10000
        return int(steps > max_vm_steps)
    conn.set_progress_handler(progress, 10000)
    try:
        for number, (event, case_value, linked, time) in enumerate(conn.execute(query), 1):
            if number > max_rows:
                raise ProbeBudgetExceeded('row_budget')
            events.add(event)
            if linked:
                links[event].add(case_value)
                raw_links += 1
                variants.add((event, case_value, time))
    except sqlite3.OperationalError as error:
        if 'interrupted' in str(error).lower():
            raise ProbeBudgetExceeded('vm_step_budget') from error
        raise
    finally:
        conn.set_progress_handler(None, 0)
    digest = hashlib.sha256()
    mapping_digest = hashlib.sha256()
    for value in sorted(variants, key=lambda v: json.dumps(v)):
        digest.update(json.dumps(value, separators=(',', ':')).encode() + b'\n')
    for event, case_values in sorted(links.items()):
        for case_value in sorted(case_values):
            mapping_digest.update(json.dumps((event, case_value), separators=(',', ':')).encode() + b'\n')
    result = {'event_rows': len(events), 'linked_events': len(links),
            'event_to_case_coverage': len(links) / len(events) if events else 1.0,
            'max_cases_per_event': max(map(len, links.values()), default=0),
            'event_case_pairs': sum(map(len, links.values())), 'raw_join_rows': raw_links,
            'null_timestamp_pairs': sum(t is None for _, _, t in variants),
            'case_mapping_digest': mapping_digest.hexdigest(),
            'output_digest': digest.hexdigest(), 'output_rows': len(variants)}
    if include_observations:
        result['observations'] = sorted(variants, key=lambda v: json.dumps(v))
    if include_partition_keys:
        # Private, short-lived fields used to prove that alternative attribution
        # paths are mutually exclusive and jointly complete. They are removed
        # before retrieval artifacts leave this function.
        result['_event_keys'] = sorted(events)
        result['_event_case_links'] = {
            event: sorted(case_values) for event, case_values in links.items()}
    return result


def _attach_complete_attribution_partitions(candidate_collections):
    """PURPOSE: Prove and annotate mutually exclusive paths that jointly cover one Event source.
    INPUT: Candidate mappings whose probes temporarily retain event keys and case mappings.
    OUTPUT: None; complete path members receive a partition certificate and private keys are removed.
    """
    from itertools import combinations

    candidates = [candidate for collection in candidate_collections
                  for values in collection.values() for candidate in values]
    grouped = defaultdict(list)
    for candidate in candidates:
        grouped[(candidate.get('grounding_candidate_id'),
                 candidate.get('case_candidate_id'))].append(candidate)
    for key, members in grouped.items():
        unique = {candidate['id']: candidate for candidate in members}
        ordered = sorted(unique.values(), key=lambda item: (
            not item.get('attribution_evidence', {}).get('anchor_directed', False),
            item.get('attribution_evidence', {}).get('candidate_edge_count', 0),
            len(item.get('path', [])), item['id']))
        event_universe = set(ordered[0].get('connection_probe', {}).get('_event_keys', [])) if ordered else set()
        selected = None
        for size in range(2, len(ordered) + 1):
            for subset in combinations(ordered, size):
                occurrence_counts = defaultdict(int)
                case_links = defaultdict(set)
                for candidate in subset:
                    probe = candidate['connection_probe']
                    for event, cases in probe.get('_event_case_links', {}).items():
                        occurrence_counts[event] += 1
                        case_links[event].update(cases)
                if (set(occurrence_counts) == event_universe and
                        all(occurrence_counts[event] == 1 for event in event_universe) and
                        all(len(case_links[event]) == 1 for event in event_universe)):
                    selected = subset
                    break
            if selected:
                break
        if selected:
            member_ids = sorted(candidate['id'] for candidate in selected)
            partition_id = stable_id('attribution_partition', [key, member_ids])
            certificate = {
                'id': partition_id, 'verified_complete': True,
                'member_candidate_ids': member_ids,
                'event_count': len(event_universe),
                'basis': 'exact_event_key_disjoint_union'}
            for candidate in selected:
                candidate['connection_probe']['attribution_partition'] = copy.deepcopy(certificate)
        for candidate in ordered:
            probe = candidate.get('connection_probe', {})
            probe.pop('_event_keys', None)
            probe.pop('_event_case_links', None)


def _docs(graph, binding, timestamp, path):
    """PURPOSE: Attach only sourced knowledge relevant to a candidate interpretation.
    INPUT: Graph annotations, event binding, timestamp and relationship path.
    OUTPUT: Relevant document snippets, preserving source references.
    """
    columns = {binding.get('activity_column'), *[v for k, v in timestamp.items() if k.endswith('column')]}
    subjects = {stable_id('table', binding['source_table']), *[stable_id('column', [binding['source_table'], c]) for c in columns if c]}
    relations = {edge['relationship_id'] for edge in path}
    result = []
    for item in graph.get('annotations', []):
        if item.get('source_kind') and item['source_kind'] != binding['source_kind']:
            continue
        if item.get('activity') and item['activity'] != binding['activity']:
            continue
        if not item.get('source'):
            continue  # document assertions must have a traceable source
        if item.get('subject_id') in subjects or item.get('relationship_id') in relations or (item.get('table') == binding['source_table'] and (not item.get('column') or item['column'] in columns)):
            result.append(item)
    return result


def _binding_family(binding):
    """PURPOSE: Identify sibling activities recorded by one physical event carrier.
    INPUT: One graph activity binding.
    OUTPUT: Hashable source-family key, or None for non-row encodings.
    """
    if binding.get('source_kind') != 'row_activity':
        return None
    return (binding.get('source_table'), binding.get('activity_column'))


def _retrieval_bindings(graph, target_labels, selection_labels, preferred_binding_ids=()):
    """PURPOSE: Retrieve target bindings, prioritizing validated mention provenance.
    INPUT: Graph, output/eligibility labels and enumerated preferred binding IDs.
    OUTPUT: (bindings to profile, residual binding IDs); siblings never widen the view.
    """
    all_bindings = graph.get('event_definitions', [])
    preferred = set(preferred_binding_ids)
    direct = [b for b in all_bindings
              if b.get('activity') in target_labels | selection_labels or b.get('id') in preferred]
    direct.sort(key=lambda binding: (binding['id'] not in preferred, binding['id']))
    families = {_binding_family(b) for b in direct if _binding_family(b) is not None}
    siblings = [b for b in all_bindings if _binding_family(b) in families and b not in direct]
    siblings.sort(key=lambda binding: binding['id'])
    return [*direct, *siblings], {b['id'] for b in siblings}


def _preferred_path_shapes(query, event_definition_id):
    """PURPOSE: Read offline branch paths associated with one enumerated binding.
    INPUT: Interpreted query and binding ID.
    OUTPUT: Relationship-ID tuples used only to order, never bypass, live probes.
    """
    candidate_id = query.get('process_view', {}).get('discovery_candidate_id')
    selected = next((item.get('card', {}) for item in query.get('seeds', {}).get('process_views', [])
                     if item.get('candidate_id') == candidate_id), {})
    return {tuple(branch.get('path_shape', {}).get('relationship_ids', []))
            for branch in selected.get('branches', [])
            if any(item.get('event_definition_id') == event_definition_id
                   for item in branch.get('activity_hypotheses', []))}


def retrieve_subgraph(graph, query, *, max_hops=MAX_ATTRIBUTION_HOPS, k_paths=3, path_budget=200, missing_key_policy='reject',
                      temporal=True, temporal_budget=None, temporal_cache=None):
    """PURPOSE: Retrieve source-centred candidates and optional view-specific temporal evidence.
    INPUT: Graph, V_q/seeds, path/key policies and optional temporal budgets/cache.
    OUTPUT: Candidates, diagnostics and temporal_knowledge; DB read-only, cache may update.
    """
    view = query.get('process_view', {})
    if (view.get('process_information') or {}).get('recovered_event_decisions'):
        from src.common.event_definition_eligibility import graph_for_selection
        graph = graph_for_selection(graph, view)
    if (query.get('status')=='ready' and
            query.get('process_view',{}).get('object_scope_policy')=='attributable_history'):
        # Native EEG already executed every selected occurrence-to-Entity rule.
        # ES materialization uses those frozen rules; Step 4 still validates the live DB.
        return {'status':'candidates_ready','reason_code':None,'first_failure_stage':None,
            'case_candidates':[],'event_rule_candidates':{},'selection_rule_candidates':{},
            'residual_rule_candidates':{},'case_selection':{'kind':'all_cases'},
            'missing_slots':[],'identity_failures':[],'unconnected_sources':[],
            'search_budget_exhausted':False,'temporal_knowledge':{},
            'process_view_fingerprint':query['process_view'].get('fingerprint'),
            'discovery_scope':'frozen_verified_eeg_recorded_history',
            'selected_event_definition_ids':query['process_view'].get('event_definitions',[]),
            'lazy_probe_cost':{'counts':{},'total_calls':0,'elapsed_seconds':0,
                               'behavior_contract':'reuse_executed_eeg_rules_then_live_full_validation'}}
    max_hops = bounded_hops(max_hops)
    if missing_key_policy not in ('reject', 'drop'):
        raise ValueError('missing_key_policy must be reject or drop')
    probe_started = time.perf_counter()
    probe_counts = {'attribution': 0, 'relationship': 0, 'behavior': 0, 'temporal': 0}
    if query['status'] != 'ready':
        return {'status': query['status'], 'reason_code': query.get('reason_code'),
                'first_failure_stage': query.get('first_failure_stage', 'process_view_expansion'),
                'encoding_types': query.get('encoding_types', []),
                'reason': '; '.join(query['reasons']), 'evidence': query.get('evidence', [])}
    if database_fingerprint(graph['database']) != graph['database_fingerprint']:
        return {'status': 'validation_failed', 'reason_code': 'grounding_failed',
                'first_failure_stage': 'schema_validation',
                'reason': 'DB changed; rebuild graph'}
    case_selection = view_card(query).get('case_selection', {'kind': 'all_cases'})
    if case_selection['kind'] not in ('all_cases', 'exists_activity'):
        return {'status': 'unsupported_representation',
                'reason_code': 'unsupported_representation',
                'first_failure_stage': 'process_view_expansion',
                'encoding_types': ['process_view_operator'],
                'reason': 'This process-view operator is not implemented; not a correct Q0 refusal'}
    from src.common.entity_population import member_cases
    cases, tables, adjacency = _cases(graph, query), {t['name']: t for t in graph['tables']}, _adjacency(graph)
    if not cases:
        return {'status': 'coverage_incomplete', 'reason_code': 'attribution_infeasible',
                'first_failure_stage': 'attribution', 'detail_code': 'case_candidates_missing'}
    targets = set(query.get('process_view', {}).get('target_activities', []))
    selection_labels = set(case_selection.get('activities', []))
    provenance = query.get('process_view', {}).get('activity_provenance', [])
    preferred_binding_ids = {
        event_definition_id for item in provenance for event_definition_id in item.get('event_definition_ids', [])}
    bindings, residual_binding_ids = _retrieval_bindings(
        graph, targets, selection_labels, preferred_binding_ids)
    rules, selection_rules, residual_rules = defaultdict(list), defaultdict(list), defaultdict(list)
    edges, identities, cache, failures, residual_failures, unconnected = {}, {}, {}, [], [], []
    budget_exhausted = graph.get('relationship_budget_exhausted', False) and not all(c.get('projection') for c in cases)
    probe_limits = []
    with closing(connect_readonly(graph['database'])) as conn:
        conn.execute('BEGIN')
        for binding in bindings:
            activity_label = binding.get('activity_label') or binding['activity']
            table = tables[binding['source_table']]
            reachable = []
            for case in [m for logical in cases for m in member_cases(logical)]:
                pkey = (table['name'], case['id'], case['table'])
                if pkey not in cache:
                    if case.get('projection'):
                        available = case['projection']['column'] in {c['name'] for c in table['columns']}
                        paths, truncated = ([[]] if available else []), False
                    else:
                        paths, truncated = _paths(adjacency, table['name'], case['table'], max_hops, path_budget)
                    cache[pkey] = (paths, truncated)
                paths, truncated = cache[pkey]
                budget_exhausted |= truncated
                for path in paths:
                    probe_counts['relationship'] += len(path)
                valid = [p for p in paths if all(_edge_probe(conn, e, edges)['accepted'] for e in p)]
                if case.get('population'):
                    validated_shapes = {tuple(p.get('edge_ids', [])) for p in binding.get('concept_paths', [])
                        if p.get('to') == case.get('entity_type_id') and
                        p.get('target_table_key_id') == case.get('table_key_id') and
                        p.get('validation_status') == 'valid'}
                    valid = [p for p in valid if tuple(e['relationship_id'] for e in p) in validated_shapes]
                preferred_shapes = _preferred_path_shapes(query, binding['id'])
                valid.sort(key=lambda path: (
                    tuple(edge['relationship_id'] for edge in path) not in preferred_shapes,
                    len(path), tuple(edge['relationship_id'] for edge in path)))
                if valid:
                    reachable.append((case, valid))
            if not reachable:
                unconnected.append(binding['source_key'])
                continue
            identity = _identity(conn, table, identities, missing_key_policy)
            if not identity['unique']:
                failure = {'source_key': binding['source_key'], 'activity': activity_label, **identity}
                (residual_failures if binding['id'] in residual_binding_ids else failures).append(failure)
                continue
            for case, paths in reachable:
                for ts in binding['timestamp_candidates']:
                    retained = 0
                    for path in paths:
                        try:
                            probe_counts['attribution'] += 1
                            probe = _rule_probe(conn, binding, case, path, identity, ts,
                                                include_partition_keys=True)
                        except ProbeBudgetExceeded as error:
                            budget_exhausted = True
                            probe_limits.append({'source_key': binding['source_key'], 'timestamp_id': ts['id'],
                                                 'relationship_ids': [e['relationship_id'] for e in path], 'reason': str(error)})
                            continue
                        if probe['event_rows'] and not probe['linked_events']:
                            continue
                        docs = _docs(graph, binding, ts, path)
                        grounding_id = stable_id('grounding_candidate', {
                            'event_definition_id': binding['id'], 'timestamp_id': ts['id'],
                            'identity_columns': identity['key_columns']})
                        attribution_id = stable_id('attribution_candidate', {
                            'source_table': binding['source_table'], 'case_id': case['id'],
                            'path': [(edge['relationship_id'], edge['direction']) for edge in path]})
                        raw = {'grounding_candidate_id': grounding_id,
                               'attribution_candidate_id': attribution_id}
                        cid = stable_id('rule', raw)
                        path_evidence = classify_attribution_path(path)
                        source_profile = {'columns': [dict(c, sample_values=[]) for c in table['columns']], 'row_count': table['row_count']}
                        semantic_context, semantic_evidence = _candidate_semantic_context(
                            graph, binding, ts)
                        item = {'id': cid, 'grounding_candidate_id': grounding_id,
                                'attribution_candidate_id': attribution_id,
                                'source_key': binding['source_key'], 'activity': activity_label, 'binding': binding,
                                'case_candidate_id': case['id'], 'case_binding': dict(case), 'timestamp': ts, 'path': path,
                                'attribution_evidence': path_evidence, 'identity_probe': identity,
                                'connection_probe': probe, 'source_profile': source_profile,
                                'semantic_context': semantic_context,
                                'source_object': _physical_object_reference(
                                    graph, binding['source_table']),
                                'evidence': [*binding['evidence'], *ts['evidence'],
                                    {'layer': 'schema', 'kind': 'attribution_path_structure',
                                     'id': stable_id('evidence', [attribution_id, 'structure']),
                                     'value': path_evidence},
                                    {'layer': 'profile', 'kind': 'event_to_case_probe',
                                     'id': stable_id('evidence', [cid, 'probe']), 'value': probe},
                                    *semantic_evidence, *docs]}
                        # Per-snapshot equivalence only; preserve *all* role/path alternatives.
                        item['snapshot_equivalence_id'] = stable_id('equivalence', [graph['database_fingerprint'], case['id'], binding['source_key'], ts['id'], probe['output_digest']])
                        if activity_label in targets:
                            rules[activity_label].append(item)
                        elif binding['id'] in residual_binding_ids:
                            residual_rules[binding['activity']].append(item)
                        if activity_label in selection_labels:
                            selection_rules[activity_label].append(item)
                        retained += 1
                        if retained >= k_paths:
                            budget_exhausted |= len(paths) > retained
                            break
        _attach_complete_attribution_partitions(
            [rules, selection_rules, residual_rules])
        temporal_knowledge = None
        if temporal and rules:
            def load_observations(candidate, case):
                """PURPOSE: Reuse bounded SQL profiling for query-scoped time evidence.
                INPUT: Enumerated event candidate and target case binding.
                OUTPUT: Unique source-event/case/time tuples; read-only, budget may raise.
                """
                probe_counts['temporal'] += 1
                probe_counts['behavior'] += 1
                probe = _rule_probe(conn, candidate['binding'], case, candidate['path'],
                                    candidate['identity_probe'], candidate['timestamp'],
                                    max_rows=(temporal_budget or {}).get('max_events', 10000),
                                    include_observations=True)
                return probe['observations']
            temporary = {'case_candidates': cases, 'event_rule_candidates': dict(rules),
                         'selection_rule_candidates': dict(selection_rules)}
            temporal_knowledge = build_temporal_evidence(graph, query, temporary, load_observations,
                                                       cache=temporal_cache, budget=temporal_budget)
        conn.commit()
    required = targets | selection_labels
    present = {a for a, values in rules.items() if values} | {a for a, values in selection_rules.items() if values}
    missing = sorted(required - present)
    status = 'selection_required'
    reason_code = 'ambiguous_selection'
    first_failure_stage = 'selection'
    if failures:
        status, reason_code, first_failure_stage = 'validation_failed', 'grounding_failed', 'grounding'
    if missing or (not rules):
        if failures:
            status, reason_code, first_failure_stage = 'validation_failed', 'grounding_failed', 'grounding'
        elif unconnected:
            status, reason_code, first_failure_stage = 'coverage_incomplete', 'attribution_infeasible', 'attribution'
        else:
            status, reason_code, first_failure_stage = 'coverage_incomplete', 'no_event_evidence', 'candidate_retrieval'
    lazy_cost = {'counts': probe_counts, 'total_calls': sum(probe_counts.values()),
                 'elapsed_seconds': time.perf_counter() - probe_started,
                 'behavior_contract': 'ranking_only_no_veto'}
    return {'status': status, 'reason_code': reason_code,
            'first_failure_stage': first_failure_stage,
            'case_candidates': cases, 'event_rule_candidates': dict(rules),
            'selection_rule_candidates': dict(selection_rules), 'residual_rule_candidates': dict(residual_rules),
            'case_selection': case_selection, 'missing_slots': missing,
            'identity_failures': failures, 'residual_identity_failures': residual_failures,
            'identity_probes': identities, 'edge_probes': edges,
            'unconnected_sources': unconnected, 'search_budget_exhausted': budget_exhausted,
            'discovery_scope': 'immutable process-view targets plus same-carrier residual evidence',
            'process_view_fingerprint': query.get('process_view', {}).get('fingerprint'), 'probe_limits': probe_limits,
            'temporal_knowledge': temporal_knowledge,
            'lazy_probe_cost': lazy_cost,
            'validated_replacement_candidates': {
                'paths': sorted({candidate['attribution_candidate_id']
                    for values in [*rules.values(), *selection_rules.values(), *residual_rules.values()]
                    for candidate in values
                    if candidate.get('connection_probe', {}).get('event_to_case_coverage') == 1
                    and candidate.get('connection_probe', {}).get('max_cases_per_event', 2) <= 1}),
                'timestamps': sorted({candidate['timestamp']['id']
                    for values in [*rules.values(), *selection_rules.values(), *residual_rules.values()]
                    for candidate in values
                    if candidate.get('timestamp', {}).get('temporal_probe', {}).get('accepted', True)})},
            'candidate_factorization': {
                'grounding_candidate_ids': sorted({candidate['grounding_candidate_id']
                    for values in [*rules.values(), *selection_rules.values(), *residual_rules.values()]
                    for candidate in values}),
                'attribution_candidate_ids': sorted({candidate['attribution_candidate_id']
                    for values in [*rules.values(), *selection_rules.values(), *residual_rules.values()]
                    for candidate in values}),
                'contract': 'grounding and case attribution identities are independent; ES composes selected IDs'}}
