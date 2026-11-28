"""Read-only occurrence witnesses and exhaustive physical repair guards."""

from collections import Counter, defaultdict
from contextlib import closing
import sqlite3
import time
from src.common.database_io import connect_readonly
from src.step3_execute import compile_event_log_sql as compiler


def projection(es, rule, side, *, unknown_clock=False):
    """PURPOSE: Observe each physical occurrence before joins, NULL drops and dedup hide failures.
    INPUT: Normalized ES, one rule and a trusted proof-side tag. OUTPUT: Fixed read-only SQL branch.
    """
    source = es['event_sources'][rule['source_id']]
    if source['encoding'] not in {'row', 'column'}:
        raise ValueError('unsupported_witness_encoding')
    case = compiler.source_case(source, es['case'])
    branch = compiler._compiler_rule(source, [rule], case)
    parts, alias = compiler._from(branch, case, left=True)
    identity = branch['event_identity']
    key = compiler._json_key('s0', identity['key_columns'])
    occurrence = f"json_array({compiler.sql_literal(identity['namespace'])},{key},{compiler._discriminator(branch)})"
    case_value = compiler.case_expression(case, alias) or compiler._json_key(alias, case['columns'])
    case_present = ' AND '.join(f'{alias}.{compiler.qi(c)} IS NOT NULL' for c in case['columns'])
    key_present = ' AND '.join(f's0.{compiler.qi(c)} IS NOT NULL' for c in identity['key_columns'])
    reference_steps = []
    for index, edge in enumerate(branch.get('joins', [])):
        left = 's0' if index == 0 else f'j{index}'
        null_fk = ' OR '.join(f'{left}.{compiler.qi(col)} IS NULL' for col in edge['left_columns'])
        right_key = compiler.qi(edge['right_columns'][0])
        reference_steps.extend([f"WHEN {null_fk} THEN 'null_reference'",
                                f"WHEN j{index+1}.{right_key} IS NULL THEN 'unmatched_reference'"])
    reference_state = ("CASE " + ' '.join(reference_steps) + " ELSE 'matched' END"
                       if reference_steps else "'matched'")
    stamp = 'NULL' if unknown_clock else compiler._timestamp(branch['timestamp'], 's0')
    return (f'SELECT {compiler.sql_literal(side)} side, {occurrence} occ, '
            f'CASE WHEN {case_present} THEN {case_value} END cid, '
            f'{stamp} stamp, '
            f'{compiler._activity_expression(branch["activity"])} label, {reference_state} ref_state '
            + ' '.join(parts) + ' WHERE ' + key_present + ' AND ' + compiler._condition(branch))


def read_witness(database, before, after, rule_ids, *, sample, budget, seconds=10, unknown_clock=False):
    """PURPOSE: Sample changed occurrence keys, or enumerate the entire affected and unaffected relation.
    INPUT: Read-only DB, two ES drafts, affected IDs, per-round mutable SQL budget, timeout seconds.
    OUTPUT: Tagged physical rows and population members. Sampling always bounds keys and returned rows.
    """
    if budget['used'] >= budget['limit']:
        raise ValueError('witness_budget_exhausted')
    if before.get('case_selection', {}).get('kind', 'all_cases') != 'all_cases' or before.get('source_priority'):
        raise ValueError('unsupported_projection_policy')
    branches = []
    for es, side in ((before, 'old'), (after, 'new')):
        for rule in es['event_rules']:
            if rule['id'] in rule_ids:
                branches.append(projection(es, rule, side, unknown_clock=unknown_clock and side == "old"))
            elif not sample and side == 'old':
                branches.append(projection(es, rule, 'other'))
    population = compiler.population_cte(before['case'])
    if population and not sample:
        branches.append("SELECT 'population',case_id,NULL,NULL,NULL,NULL FROM entity_cases")
    ctes = [population] if population and not sample else []
    ctes.append('w AS (' + ' UNION ALL '.join(branches) + ')')
    if sample:
        ctes.extend(["variants AS (SELECT occ,cid,stamp,label,"
                     "SUM(CASE WHEN side='old' THEN 1 ELSE -1 END) balance FROM w GROUP BY occ,cid,stamp,label)",
                     "changed AS (SELECT DISTINCT occ FROM variants WHERE balance<>0 ORDER BY occ LIMIT 5)"])
        ending = 'SELECT w.* FROM w JOIN changed USING(occ) ORDER BY occ,side,cid,stamp LIMIT 30'
    else:
        ending = 'SELECT * FROM w'
    budget['used'] += 1
    deadline = time.monotonic() + seconds
    with closing(connect_readonly(database)) as conn:
        conn.set_progress_handler(lambda: int(time.monotonic() > deadline), 1000)
        conn.row_factory = sqlite3.Row
        return [dict(row) for row in conn.execute('WITH ' + ','.join(ctes) + ' ' + ending)]


def log_relation(rows):
    """PURPOSE: Keep multiplicities while comparing case, time and activity by physical occurrence.
    INPUT: Successfully executed event rows. OUTPUT: Counter of physical log tuples.
    """
    return Counter((r['source_occurrence_id'], r['case_id'], r['timestamp'], r['activity']) for r in rows)


def check_execution(execution, expected_rows, population, side):
    """PURPOSE: Match measured output against an independent complete source projection.
    INPUT: Execution, expected occurrence tuples, optional case set and proof-side tag.
    OUTPUT: Raises on a mismatch; unexecuted sides remain explicitly unmeasured.
    """
    if not execution.get('passed'):
        return
    if log_relation(execution['event_log']) != Counter(expected_rows):
        raise ValueError(side + '_full_log_does_not_match_source_proof')
    if population is not None and population != {r['case_id'] for r in execution['diagnostics']['case_population']}:
        raise ValueError('case_population_changed')


def verify_changes(rows, candidate, old_execution, new_execution, *, has_population, role_proven=False, unknown_clock=False, expected_after=None):
    """PURPOSE: Prove each permitted occurrence change and equivalence of all unaffected events.
    INPUT: Exhaustive raw proof and optional successful pre/post logs. OUTPUT: Counts and bounded witnesses;
    raises on unexpected loss, movement, multiplicity, population drift or unproved result changes.
    """
    groups = {side: defaultdict(list) for side in ('old', 'new', 'other')}
    population = set()
    optional = {r['occ'] for r in rows if r['side']=='old' and r.get('ref_state')=='null_reference'}
    for row in rows:
        if row['side'] == 'population':
            population.add(row['occ'])
        else:
            groups[row['side']][row['occ']].append((row['cid'], row['stamp'], row['label']))
    old, new = groups['old'], groups['new']
    if set(old) != set(new):
        raise ValueError('occurrence_identity_changed')
    counts = Counter()
    examples = []
    for occ in sorted(old):
        prior, current = old[occ], new[occ]
        if Counter(prior) == Counter(current):
            continue
        if len(current) != 1:
            raise ValueError('candidate_not_uniquely_attributable')
        cid, stamp, label = current[0]
        if any(p[2] != label for p in prior) or not label:
            raise ValueError('activity_changed')
        if candidate['kind']=='path' and (cid is None or (has_population and cid not in population)):
            raise ValueError('candidate_outside_population')
        if candidate['kind'] == 'timestamp':
            if len(prior) != 1 or prior[0][0] != cid:
                raise ValueError('timestamp_changed_case')
            if (prior[0][1] is None or stamp is None) and candidate['semantic_basis'] != 'selected_event_binding':
                raise ValueError('null_change_without_original_clock')
        else:
            if any(p[1] != stamp for p in prior):
                raise ValueError('path_changed_time')
            valid_cases = {p[0] for p in prior if p[0] is not None and
                           (not has_population or p[0] in population)}
            if occ in optional and not valid_cases and not role_proven:
                raise ValueError('optional_reference_without_role_evidence')
            if valid_cases and cid not in valid_cases and not role_proven:
                raise ValueError('unique_case_move_without_role_evidence')
        if len(examples) < 5:
            examples.append(dict(occurrence=occ, before=prior[:5], after=current))
        counts['affected_occurrences'] += 1
        counts['amplification_removed'] += max(0, len(prior) - len(current))
    relations = {}
    for side in ('old', 'new'):
        tuples = {(occ, cid, stamp, label) for name in (side, 'other')
                  for occ, variants in groups[name].items() for cid, stamp, label in variants
                  if cid is not None and stamp is not None and label is not None and
                  (not has_population or cid in population)}
        relations[side] = tuples
    expected_population = population if has_population else None
    check_execution(old_execution, relations['old'], expected_population, 'old')
    check_execution(new_execution, relations['new'], expected_population, 'new')
    if expected_after is not None:
        expected_after.update(rows=relations['new'], population=expected_population)
    maps = {}
    for side, tuples in relations.items():
        maps[side] = defaultdict(set)
        for occ, cid, stamp, label in tuples:
            maps[side][occ].add((cid, stamp, label))
    left, right = maps['old'], maps['new']
    counts['added'] = len(right.keys() - left.keys())
    counts['removed'] = len(left.keys() - right.keys())
    counts['moved'] = sum({x[0] for x in left[k]} != {x[0] for x in right[k]} for k in left.keys() & right.keys())
    counts['retimed'] = sum({x[1] for x in left[k]} != {x[1] for x in right[k]} for k in left.keys() & right.keys())
    if candidate['kind'] == 'path' and (counts['removed'] or counts['retimed']):
        raise ValueError('unexpected_path_diff')
    if candidate['kind'] == 'timestamp' and counts['moved']:
        raise ValueError('unexpected_timestamp_diff')
    if unknown_clock:
        if old_execution.get('passed') or candidate['semantic_basis'] != 'selected_event_binding':
            raise ValueError('unverified_baseline_clock')
        for field in ('added', 'removed', 'moved', 'retimed'):
            counts[field] = None
    return {'counts': dict(counts), 'examples': examples,
            'baseline_proof': 'executed_log' if old_execution.get('passed') else 'full_source_relation'}
