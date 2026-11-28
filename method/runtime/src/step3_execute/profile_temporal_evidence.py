"""Bounded, view-specific observations: temporal patterns are not process laws."""

from __future__ import annotations
from collections import Counter, defaultdict
import json
from src.common.timestamp_policy import EPOCH_UNITS, binding_timezone, timestamp_order
from itertools import combinations
import re
from src.common.schema_metadata import stable_id, timestamp_columns
TEMPORAL_VERSION = 1
DEFAULT_BUDGET = {'max_candidates': 24, 'max_pairs': 96, 'max_cases': 200, 'min_support': 5, 'max_events': 10000}


class TemporalProbeUnavailable(RuntimeError):
    """A bounded observation probe cannot complete; not evidence of absence."""


def scoped_assertions(candidate):
    """PURPOSE: Read sourced semantic assertions without last-write-wins conflicts.
    INPUT: Candidate with timestamp columns and layered evidence dictionaries.
    OUTPUT: Assertion mapping; disagreements become 'conflicting'; no mutation.
    """
    values = defaultdict(list)
    columns = set(timestamp_columns(candidate['timestamp']))
    for evidence in candidate.get('evidence', []):
        if evidence.get('layer') != 'documentation' or not evidence.get('source'):
            continue
        for key, value in evidence.get('assertions', {}).items():
            if key in ('timestamp_role', 'timezone', 'clock_domain', 'temporal_anchor') and evidence.get('column') not in columns:
                continue
            values[key].append(value)
    return {key: items[0] if all(v == items[0] for v in items) else 'conflicting' for key, items in values.items()}


def parse_event_time(value, *, assumed_timezone=None, clock_domain=None, encoding=None):
    """PURPOSE: Measure a source clock at supported observational precision.
    INPUT: Raw clock, documented zone/domain and physical encoding.
    OUTPUT: Integer-microsecond interval, or None for invalid or unrepresentable clocks.
    """
    day = clock = None
    if encoding in ('date_clock', 'compact_hhmmss', 'seconds_since_midnight'):
        try:
            day, clock = json.loads(value)
        except (TypeError, ValueError):
            return None
    rank, _, key = timestamp_order(value, assumed_timezone, encoding, day=day, clock=clock)
    if rank >= 2:
        return None
    text = str(clock if clock is not None else value)
    fraction = re.search(r'^.*?(?:[T ]|^)\d{2}:?\d{2}:?\d{2}[.,](\d+)', text)
    if encoding in EPOCH_UNITS:
        precision = 1000000 / EPOCH_UNITS[encoding]
    elif fraction:
        precision = 10 ** (6 - len(fraction[1]))
    elif encoding in ('compact_hhmmss', 'seconds_since_midnight') or re.search(r'\d{2}:\d{2}:\d{2}', text):
        precision = 1000000
    elif re.search(r'\d{2}:\d{2}', text):
        precision = 60000000
    else:
        precision = 86400000000
    start = key * 1000000
    if precision < 1 or start.denominator != 1:
        return None
    domain = 'UTC' if rank == 0 else ('local:' + clock_domain
              if isinstance(clock_domain, str) and clock_domain and clock_domain != 'conflicting' else None)
    return {'start': int(start), 'end': int(start) + int(precision), 'domain': domain,
            'precision_us': int(precision)}


def compare_event_times(left, right):
    """PURPOSE: Compare intervals without assigning order to ties/overlap.
    INPUT: Two parse_event_time outputs, including None or unknown clock domains.
    OUTPUT: before, after, tie, precision_overlap, or incomparable.
    """
    if not left or not right or not left['domain'] or left['domain'] != right['domain']:
        return 'incomparable'
    if left['start'] == right['start'] and left['end'] == right['end']:
        return 'tie'
    if left['end'] <= right['start']:
        return 'before'
    if right['end'] <= left['start']:
        return 'after'
    return 'precision_overlap'


def prepare_observations(candidate, case, observations):
    """PURPOSE: Retain physical event occurrences, grouped by namespaced objects.
    INPUT: Candidate, case binding, unique (source_key_json,case_key_json,time) rows.
    OUTPUT: Per-object event lists plus parsing diagnostics; keys are hashed, not IDs alone.
    Repeated activity occurrences are retained; only identical event links deduplicate.
    """
    assertions = scoped_assertions(candidate)
    binding_time = candidate['timestamp']
    assumed = binding_timezone(binding_time) or binding_timezone(assertions)
    kind = binding_time.get('kind')
    encoding = {'date_compact_clock': 'compact_hhmmss', 'compact_date_seconds': 'seconds_since_midnight'}.get(
        kind, kind if kind in EPOCH_UNITS or kind == 'date_clock'
        else binding_time.get('detected_format') or binding_time.get('format'))
    cases, seen, counts = defaultdict(list), set(), Counter()
    binding = candidate['binding']
    discriminator = binding.get('timestamp_columns') if binding['source_kind'] == 'column_event' else 'row_event'
    for source_key, case_key, timestamp in observations:
        object_id = stable_id('object', [case['table'], case['columns'], case_key])
        event_id = stable_id('physical_event', [binding['source_table'], source_key, discriminator])
        signature = (object_id, event_id, timestamp)
        if signature in seen:
            continue
        seen.add(signature)
        interval = parse_event_time(timestamp, assumed_timezone=assumed,
                                    clock_domain=assertions.get('clock_domain'), encoding=encoding)
        counts['event_case_links'] += 1
        counts['null_timestamps' if timestamp is None else 'invalid_timestamps'] += int(interval is None)
        counts['unknown_clock_links'] += int(interval is not None and interval['domain'] is None)
        cases[object_id].append({'event_id': event_id, 'time': interval})
    return {'cases': dict(cases), 'diagnostics': dict(counts)}


def projected_transitions(left, right):
    """PURPOSE: Describe repeated occurrences without collapsing to first/min time.
    INPUT: Event lists for two different sources on one object.
    OUTPUT: Adjacent counts in the A/B projection and ambiguous-bucket count.
    These are NOT full-log directly-follows edges; tied/overlapping buckets break order.
    """
    events = [(e['time'], side) for side, rows in [('A', left), ('B', right)] for e in rows]
    if any(not t or not t['domain'] for t, _ in events) or len({t['domain'] for t, _ in events}) != 1:
        return {'counts': {}, 'ambiguous_buckets': 0, 'comparable': False}
    events.sort(key=lambda item: item[0]['start'])
    buckets = []
    for interval, side in events:
        if not buckets or interval['start'] >= buckets[-1]['end']:
            buckets.append({'end': interval['end'], 'sides': [side]})
        else:
            buckets[-1]['end'] = max(buckets[-1]['end'], interval['end'])
            buckets[-1]['sides'].append(side)
    counts = Counter()
    for first, second in zip(buckets, buckets[1:]):
        if len(first['sides']) == len(second['sides']) == 1:
            counts[first['sides'][0] + '->' + second['sides'][0]] += 1
    return {'counts': dict(counts), 'ambiguous_buckets': sum(len(b['sides']) > 1 for b in buckets), 'comparable': True}


def compare_candidate_profiles(left, right, frame):
    """PURPOSE: Measure milestone order separately from repeated-event sequences.
    INPUT: Two prepared candidate profiles and common sampled object identifiers.
    OUTPUT: Counts/ratios with explicit denominators, missingness and repetition support.
    Missingness is within the observed union sample, not all objects in the DB.
    """
    counts, transitions = Counter(), Counter()
    for object_id in frame:
        a, b = left['cases'].get(object_id, []), right['cases'].get(object_id, [])
        counts['left_missing_cases'] += int(not a)
        counts['right_missing_cases'] += int(not b)
        if not a or not b:
            continue
        counts['both_observed_cases'] += 1
        if len(a) == len(b) == 1:
            counts['single_occurrence_cases'] += 1
            counts[compare_event_times(a[0]['time'], b[0]['time'])] += 1
        else:
            counts['repeated_cases'] += 1
            projected = projected_transitions(a, b)
            counts['repeated_comparable_cases'] += int(projected['comparable'])
            counts['ambiguous_buckets'] += projected['ambiguous_buckets']
            transitions.update(projected['counts'])
    comparable = sum(counts[k] for k in ('before', 'after', 'tie', 'precision_overlap'))
    fields = ('both_observed_cases', 'single_occurrence_cases', 'repeated_cases', 'before', 'after', 'tie',
              'precision_overlap', 'incomparable', 'left_missing_cases', 'right_missing_cases',
              'repeated_comparable_cases', 'ambiguous_buckets')
    return {**{key: counts[key] for key in fields}, 'sampled_cases': len(frame), 'comparable_cases': comparable,
            'before_ratio': counts['before'] / comparable if comparable else None,
            'tie_ratio': counts['tie'] / comparable if comparable else None,
            'left_missing_ratio': counts['left_missing_cases'] / len(frame) if frame else None,
            'right_missing_ratio': counts['right_missing_cases'] / len(frame) if frame else None,
            'pair_projection_adjacent_counts': dict(transitions)}


def choose_temporal_candidates(retrieval, limit):
    """PURPOSE: Bound profiling while giving source alternatives round-robin coverage.
    INPUT: Retrieval candidates and maximum number of candidate interpretations.
    OUTPUT: Stable list of distinct candidates; source/path alternatives remain separate.
    """
    groups = defaultdict(dict)
    for collection in ('event_rule_candidates', 'selection_rule_candidates'):
        for candidates in retrieval.get(collection, {}).values():
            for candidate in candidates:
                groups[(candidate['case_candidate_id'], candidate['source_key'])][candidate['id']] = candidate
    ordered = [sorted(items.values(), key=lambda c: (len(c['path']), c['timestamp']['id'], c['id'])) for _, items in sorted(groups.items())]
    return [items[n] for n in range(max(map(len, ordered), default=0)) for items in ordered if n < len(items)][:limit]


def constraint_evidence(graph, query, left, right, stats, min_support):
    """PURPOSE: Score only independently documented order against a documented anchor.
    INPUT: Sourced temporal constraints, query view, pair interpretations and statistics.
    OUTPUT: Per-candidate bounded score evidence; observations alone never create rules.
    No scores for repeated events, mixed clocks, conflicting K, or weak support.
    """
    if stats['comparable_cases'] < min_support or stats['single_occurrence_cases'] != stats['both_observed_cases']:
        return []
    result = []
    for constraint in graph.get('annotations', []):
        if constraint.get('kind') != 'temporal_constraint' or not constraint.get('source') or constraint.get('relation') != 'before':
            continue
        if constraint.get('process_view_id') != query['V_q'].get('process_view_id'):
            continue
        if not constraint.get('process_view_id') and constraint.get('case_notion') != query['V_q'].get('case_notion'):
            continue
        labels = (left['activity'], right['activity'])
        expected = (constraint.get('before_activity'), constraint.get('after_activity'))
        if labels not in (expected, expected[::-1]):
            continue
        direction = 1 if labels == expected else -1
        strength = direction * (stats['before'] - stats['after']) / stats['comparable_cases']
        for subject, anchor in ((left, right), (right, left)):
            assertions = scoped_assertions(anchor)
            if assertions.get('temporal_anchor') is not True or assertions.get('timestamp_role') != 'occurrence':
                continue
            if assertions.get('eventness') != 'observed_event' or assertions.get('attribution') != 'included':
                continue
            result.append({'candidate_id': subject['id'], 'anchor_candidate_id': anchor['id'],
                           'constraint_id': constraint['id'], 'source': constraint['source'],
                           'score_delta': strength, 'support': stats['comparable_cases']})
    return result


def build_temporal_evidence(graph, query, retrieval, load_observations, *, cache=None, budget=None):
    """PURPOSE: Build bounded, cached temporal knowledge for a single query view.
    INPUT: Snapshot graph, V_q, retrieval, bounded candidate-reader callback;
    optional mutable in-memory cache and candidate/pair/case/support budgets.
    OUTPUT: Scoped observation edges and score cards; cache is updated, DB is read only
    by callback. Probe-budget exceptions are reported, never converted into Q0.
    """
    limits = {**DEFAULT_BUDGET, **(budget or {})}
    if any(not isinstance(v, int) or v <= 0 for v in limits.values()):
        raise ValueError('Temporal budgets must be positive integers')
    cache = {} if cache is None else cache
    candidates = choose_temporal_candidates(retrieval, limits['max_candidates'])
    cases = {c['id']: c for c in retrieval.get('case_candidates', [])}
    profiles, unavailable, hits = {}, [], 0
    scope = {'version': TEMPORAL_VERSION, 'snapshot': graph['database_fingerprint'],
             'view': query['V_q'], 'view_candidates': query['seeds']['process_views'],
             'annotation_digest': stable_id('annotations', graph.get('annotations', []))}
    for candidate in candidates:
        case = cases[candidate['case_candidate_id']]
        key = stable_id('temporal_cache', [scope, candidate['id'], case, candidate['timestamp'], candidate['path'], limits])
        if key in cache:
            profiles[candidate['id']] = cache[key]
            hits += 1
            continue
        try:
            observations = load_observations(candidate, case)
        except TemporalProbeUnavailable as error:
            unavailable.append({'candidate_id': candidate['id'], 'reason': str(error)})
            continue
        profile = prepare_observations(candidate, case, observations)
        profiles[candidate['id']] = profile
        cache[key] = profile
    available = [c for c in candidates if c['id'] in profiles]
    frames = defaultdict(set)
    for candidate in available:
        frames[candidate['case_candidate_id']].update(profiles[candidate['id']]['cases'])
    sampled = {key: sorted(values)[:limits['max_cases']] for key, values in frames.items()}
    pairs = [(a, b) for a, b in combinations(available, 2)
             if a['case_candidate_id'] == b['case_candidate_id'] and a['source_key'] != b['source_key']]
    edges, scores = [], defaultdict(list)
    for left, right in pairs[:limits['max_pairs']]:
        stats = compare_candidate_profiles(profiles[left['id']], profiles[right['id']], sampled[left['case_candidate_id']])
        edge = {'id': stable_id('observed_temporal', [scope, left['id'], right['id'], limits]),
                'kind': 'OBSERVED_TEMPORAL_RELATION', 'layer': 'temporal', 'source': 'query_scoped_db_profile',
                'left_candidate_id': left['id'], 'right_candidate_id': right['id'],
                'case_candidate_id': left['case_candidate_id'], 'snapshot': graph['database_fingerprint'],
                'process_view': query['V_q'], 'statistics': stats, 'semantics': 'observation_not_causality'}
        edges.append(edge)
        for evidence in constraint_evidence(graph, query, left, right, stats, limits['min_support']):
            scores[evidence['candidate_id']].append({**evidence, 'observation_id': edge['id']})
    total_candidates = len({c['id'] for values in retrieval.get('event_rule_candidates', {}).values() for c in values})
    return {'version': TEMPORAL_VERSION, 'scope': scope, 'budget': limits, 'edges': edges,
            'candidate_scores': dict(scores), 'profiled_candidates': len(profiles), 'cache_hits': hits,
            'interpretations': {c['id']: {'source_key': c['source_key'], 'source_table': c['binding']['source_table'],
                'activity': c['activity'], 'raw_values': c['binding'].get('raw_values'),
                'source_kind': c['binding']['source_kind'], 'timestamp': c['timestamp'],
                'case': cases[c['case_candidate_id']], 'path': c['path'],
                'identity_columns': c['identity_probe']['key_columns'],
                'clock_assumptions': {k: v for k, v in scoped_assertions(c).items() if k in ('timezone', 'clock_domain')}}
                for c in available},
            'unavailable': unavailable, 'candidate_budget_exhausted': total_candidates > len(candidates),
            'pair_budget_exhausted': len(pairs) > limits['max_pairs'],
            'sampling': {'method': 'deterministic hashed-object sample from observed union, not all DB cases',
                         'observed_cases': {k: len(v) for k, v in frames.items()},
                         'sampled_cases': {k: len(v) for k, v in sampled.items()}},
            'diagnostics': {key: p['diagnostics'] for key, p in profiles.items()}}
