"""Entity-scoped event inventory reviews and request-local evidence decisions."""

from src.common.prompt_loader import load_prompt
from collections import Counter, defaultdict
from contextlib import closing
from copy import deepcopy
import hashlib
import json
from jsonschema import validate
from src.common.entity_identity import typed_entity_key
from src.common.event_clock import NON_OCCURRENCE_ROLES, scoped_event_clock
from src.common.llm_usage import chat_settings
from src.common.runtime_input_contract import EXECUTION_AXES, require_no_oracle_payload
from src.step1_understand.validate_event_attribution_paths import _json_key
from src.common.database_io import connect_readonly, quote_identifier
from src.step1_understand.review_entity_meanings import canonical_dictionary_citations
NEGATIVE = {'conflicting', 'rejected', 'invalid', 'failed'}
REVIEW = load_prompt('step1_understand', 'review_entity_event_inventory')
CONTEXT = load_prompt('step2_retrieve_and_interpret', 'resolve_request_context_definition')
from src.common.json_schema import record
TEXT = {'type': 'string'}
CITATIONS = dict(type='array', items=record(id=TEXT, quote=TEXT))
PATH_DECISION = record(path_id=TEXT, status=dict(type='string', enum=['supported', 'incompatible', 'uncertain']),
                       role=dict(type='string', enum=['subject', 'related', 'unspecified']),
                       reason=TEXT, citations=CITATIONS)
INVENTORY_DECISION = record(id=TEXT, paths=dict(type='array', items=PATH_DECISION),
                            duplicate_of=TEXT, reason=TEXT, citations=CITATIONS)
CONTEXT_DECISION = record(id=TEXT, span=TEXT, reason=TEXT, citations=CITATIONS)


def review_once(role, payload, client, model, cache=None):
    """PURPOSE: Execute one closed evidence review or reuse its exact reply.
    INPUT: Public cards and model client. OUTPUT: Decisions and usage/error receipt; no retry.
    """
    contextual = role == 'tier2_context'
    instruction = CONTEXT if contextual else REVIEW
    schema = record(decisions=dict(type='array', items=CONTEXT_DECISION if contextual else INVENTORY_DECISION))
    require_no_oracle_payload(payload)
    statements = {}
    cards = []
    for definition in payload['definitions']:
        card = dict(definition)
        dictionary = card.pop('dictionary')
        statements.update((s['id'], s) for s in dictionary)
        card['dictionary_ids'] = [s['id'] for s in dictionary]
        cards.append(card)
    wire = json.dumps(dict(payload, definitions=cards, dictionary=statements),
                      sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    key = role + ':' + hashlib.sha256(json.dumps([model, instruction, schema, wire]).encode()).hexdigest()
    audit = dict(task=role, role=role, model=model, cache_key=key, cache_hit=cache is not None and key in cache,
                 errors=[], usage={}, entity_type_id=payload['entity_type']['id'], prompt={'system':instruction,'user':wire})
    try:
        if audit['cache_hit']:
            reply = cache[key]
        elif client is None:
            audit['errors'].append('llm_unavailable')
            return [], audit
        else:
            messages = [dict(role='system', content=instruction), dict(role='user', content=wire)]
            budget = getattr(client, 'pi_request_budget', None) if contextual else None
            if budget:
                from src.step2_retrieve_and_interpret.execute_model_roles import _input_tokens
                budget.reserve(_input_tokens(model, messages, schema))
            response = client.chat.completions.create(model=model, **chat_settings(model),
                messages=messages,
                response_format={'type':'json_schema','json_schema':dict(name=role, strict=True, schema=schema)})
            usage = getattr(response, 'usage', None)
            audit['usage'] = dict(input_tokens=getattr(usage,'prompt_tokens',0) or 0,
                                  output_tokens=getattr(usage,'completion_tokens',0) or 0)
            reply = json.loads(response.choices[0].message.content)
        validate(reply, schema)
        require_no_oracle_payload(reply)
        ids = [d['id'] for d in reply['decisions']]
        allowed = {d['id'] for d in payload['definitions']}
        if len(set(ids)) != len(ids) or not set(ids) <= allowed or (not contextual and set(ids) != allowed):
            raise ValueError('incomplete, duplicate or unknown review IDs')
        if not contextual:
            offered = {item['id']: {path['id'] for path in item['paths']} for item in cards}
            for item in reply['decisions']:
                ids = [path['path_id'] for path in item['paths']]
                if len(ids) != len(set(ids)) or set(ids) != offered[item['id']]:
                    raise ValueError('review must account for every supplied attribution path')
        if cache is not None:
            cache[key] = reply
        audit.update(audit['usage'])
        audit['output'] = reply
        return reply['decisions'], audit
    except Exception as error:
        audit['errors'].append(f'{type(error).__name__}: {error}')
        return [], audit


def classify_candidate(event, time):
    """PURPOSE: Grade an existing definition without changing any construction judgment.
    INPUT: Native binding and time unit. OUTPUT: Tier and single unconfirmed axis, if present.
    """
    checks = event['extraction_checks']
    missing = [axis for axis in EXECUTION_AXES if checks.get(axis) != 'supported']
    if not missing:
        return 1, None
    denied_clock = time.get('role_status') == 'supported' and time.get('semantic_role') in (NON_OCCURRENCE_ROLES | {'transaction_time', 'planned_time'})
    denied_occurrence = event.get('activity_semantics', {}).get('occurrence_reason') in {
        'snapshot_is_not_occurrence_evidence', 'column_interpretation_rejected_occurrence'}
    denied = (denied_occurrence or denied_clock or event.get('activity_label_issue') or event.get('conflicts') or
              any(event.get(field) in NEGATIVE for field in ('candidate_status','interpretation_status','validation_status')) or
              (event.get('timestamp_pairing') or {}).get('status') in NEGATIVE)
    if (not denied and len(missing) == 1 and checks[missing[0]] in {'unknown','unresolved','uncertain','ambiguous'}
            and event.get('table') and event.get('row_selection', {}).get('kind') in {'all_rows','equals'}
            and time.get('columns')):
        return 2, missing[0]
    return None, None


def decision_evidence(event, decision):
    """PURPOSE: Verify a semantic decision against the candidate's own physical rule and DD.
    INPUT: Existing candidate and one review decision. OUTPUT: Grounded evidence or None.
    """
    evidence = canonical_dictionary_citations(decision.get('citations'), event['review_dictionary'])
    if not evidence or not str(decision.get('reason') or '').strip():
        return None
    return {'reason':decision['reason'], 'citations':evidence}


def may_promote(event):
    """PURPOSE: Require the independent executed SQL and occurrence-key proof for promotion.
    INPUT: Graded binding. OUTPUT: Whether a one-axis contextual promotion is physically possible.
    """
    probe = event.get('validation_axes', {}).get('rule_executable', {})
    return (event.get('candidate_tier') == 2 and probe.get('status') == 'pass'
            and probe.get('occurrence_key_validated') is True and probe.get('time_format_known') is True)


def occurrence_counts(connection, event, unit, paths, maps):
    """PURPOSE: Count actual events by typed case and clock, preserving multiplicity across source rows.
    INPUT: Existing validated case maps and time binding. OUTPUT: Counter, empty on absent evidence.
    """
    by_source = {}
    from src.step1_understand.project_runtime_evidence_graph import _timestamp_candidate
    from src.step3_execute.compile_event_log_sql import _timestamp
    clock = _timestamp(_timestamp_candidate(unit), 's')
    for path in paths:
        mapping = maps.get(path['target_table_key_id'])
        if not mapping:
            return Counter()
        case = path['case_map']
        key = _json_key('s', event['source_row_key'])
        sql = ('SELECT m.source_event_id, m.case_id, ' + clock + ' FROM (' + case['map_sql'] +
               ') m JOIN ' + quote_identifier(event['table']) + ' s ON ' + key + '=m.source_event_id')
        for source, instance, value in connection.execute(sql, case.get('map_parameters', [])):
            if value is None:
                return Counter()
            pair = (typed_entity_key(mapping, json.loads(instance)), value)
            if source in by_source and by_source[source] != pair:
                return Counter()
            by_source[source] = pair
    return Counter(by_source.values())


def review_entity_events(graph, dd, database, client, model, cache=None):
    """PURPOSE: Grade all bindings, then review every ET's complete attributable inventory once.
    INPUT: Finalized native graph, public DD and source DB. OUTPUT: ET-local decisions and call audits.
    """
    times = {t['ts_id']:t for t in graph['timestamps']}
    events = {b['id']:b for b in graph['bindings']}
    for event in events.values():
        event['candidate_tier'], event['unresolved_axis'] = classify_candidate(
            event, scoped_event_clock(event, times[event['ts_id']]))
        event['entity_reviews'] = {}
        columns = {*times[event['ts_id']]['columns'], *event['source_row_key'], event['alpha'].get('column')}
        event['review_dictionary'] = [s for s in dd.get('semantic_statements', [])
                                      if not s.get('table') or s['table'] == event['table'] and
                                      (not s.get('column') or s['column'] in columns)]
    grouped = defaultdict(lambda: defaultdict(list))
    for path in graph.get('attribution_paths', []):
        if path['validation_status'] in {'valid','rule_confirmed_no_occurrences'}:
            grouped[path['to']][path['event_definition_id']].append(path)
    audits = []
    with closing(connect_readonly(database)) as connection:
        for entity in graph.get('concepts', []):
            et = entity['id']
            groups = grouped[et]
            cards = []
            for eid, paths in sorted(groups.items()):
                event = events[eid]
                if event['candidate_tier'] is None:
                    continue
                cards.append(dict(id=eid, tier=event['candidate_tier'], axis=event['unresolved_axis'],
                    activity=event['alpha'], source=event['table'], rows=event['row_selection'],
                    timestamp=scoped_event_clock(event, times[event['ts_id']]), checks=event['extraction_checks'],
                    count=max(p['case_map']['validation']['source_rows'] for p in paths),
                    paths=[{'id': path['id'], 'joins': path['joins'],
                            'role': (path.get('role_validation') or {}).get('reference') or path.get('case_role'),
                            'subject_rule_ids': path.get('entity_subject_rule_ids', []),
                            'validation_status': path['validation_status']} for path in paths],
                    dictionary=attribution_dictionary(event, entity, paths, dd)))
            payload = dict(entity_type={'id':et,'name':entity.get('name')}, definitions=cards)
            decisions, audit = review_once('entity_event_review', payload, client, model, cache)
            graph.setdefault('entity_event_review_status', {})[et] = {
                'status':'incomplete' if audit['errors'] else 'reviewed', 'errors':list(audit['errors']),
                'candidate_count':len(cards), 'response_key':audit['cache_key']}
            audits.append(audit)
            duplicates = {}
            for decision in decisions:
                eid = decision['id']
                event = events[eid]
                paths = {path['id']: path for path in groups[eid]}
                review = {}
                for item in decision['paths']:
                    path_id = item['path_id']
                    dictionary = attribution_dictionary(event, entity, [paths[path_id]], dd)
                    evidence = decision_evidence({'review_dictionary': dictionary}, item)
                    if evidence:
                        review[path_id] = dict(evidence, status=item['status'], role=item['role'])
                event['entity_reviews'][et] = {'attribution_paths': review}
                if decision['duplicate_of'] and decision_evidence(event, decision):
                    duplicates[eid] = decision['duplicate_of']
            maps = {m['representation_id']:m for m in entity.get('population', {}).get('maps', [])}
            signatures = {}
            members = {card['id'] for card in cards}
            for eid, representative in duplicates.items():
                visited = {eid}
                while representative in duplicates and representative not in visited:
                    visited.add(representative)
                    representative = duplicates[representative]
                if representative in visited or representative not in members:
                    continue
                retained = events[representative]
                source = events[eid]
                if source['candidate_tier'] == 1 and retained['candidate_tier'] != 1:
                    continue
                for identifier in (eid, representative):
                    if identifier not in signatures:
                        event = events[identifier]
                        unit = times[event['ts_id']]
                        signatures[identifier] = occurrence_counts(connection, event, unit, groups[identifier], maps)
                if signatures[eid] and signatures[eid] == signatures[representative]:
                    events[eid]['entity_reviews'][et].update(duplicate_of=representative,
                        verified_occurrences=sum(signatures[eid].values()))
    return audits


def attribution_dictionary(event, entity, paths, dictionary):
    """PURPOSE: Collect public statements relevant to the ED and the edges under review.
    INPUT: Native definition, ET, paths and normalized DD. OUTPUT: Deduplicated citation inventory.
    """
    endpoints = {(edge[side + '_table'], column) for path in paths for edge in path['joins']
                 for side in ('left', 'right') for column in edge[side + '_columns']}
    tables = {table for table, _ in endpoints} | {m['table'] for m in entity.get('population', {}).get('maps', [])}
    evidence = {item['id']: item for item in event['review_dictionary']}
    evidence.update((item['id'], item) for item in dictionary.get('semantic_statements', [])
                    if (item.get('table'), item.get('column')) in endpoints
                    or item.get('table') in tables and not item.get('column'))
    return list(evidence.values())


def effective_binding(binding, et, approval=None):
    """PURPOSE: Apply an explicit request's evidence-only approval to an unresolved definition.
    INPUT: Binding, ET grounding the approval and optional request approval.
    OUTPUT: Canonical binding or transient evidence projection with the same label, clock, predicate and key.
    """
    if approval and (approval.get('entity_type') != et or approval.get('axis') != binding.get('unresolved_axis')
                     or not approval.get('span') or not decision_evidence(binding, approval)):
        approval = None
    if not approval or not may_promote(binding):
        return binding
    result = deepcopy(binding)
    axis = binding['unresolved_axis']
    result['extraction_checks'][axis] = 'supported'
    result.update(extraction_status='executable', unresolved_reasons=[])
    semantics = result['activity_semantics']
    if axis in {'activity','occurrence'}:
        semantics['status' if axis == 'activity' else 'occurrence_status'] = 'supported'
        if all(semantics.get(k) == 'supported' for k in ('status','occurrence_status')):
            result['interpretation_status'] = 'supported'
    if axis == 'time':
        if result.get('timestamp_pairing'):
            result['timestamp_pairing']['status'] = 'supported_by_review'
        for unit in result.get('timestamp_candidates', []):
            unit.update(role='business_occurrence', semantic_role='business_occurrence', role_status='supported',
                        time_role='valid_time', occurrence_time_policy=dict(eligible=True,status='supported',
                        semantic_role='business_occurrence', evidence=approval['citations']))
    if axis == 'identity':
        result['occurrence_identity_status'] = 'supported'
    return result


def graph_for_selection(graph, view):
    """PURPOSE: Read only final PI evidence into a transient SQL-validation view.
    INPUT: Shared EEG and frozen PI. OUTPUT: Graph with scoped selected definitions; base graph is reusable.
    """
    if not graph or not view:
        return graph
    info = view.get('process_information') or {}
    et = view.get('target_ot_id') or view.get('target_object_selection_id')
    approvals = info.get('tier2_approvals', {}) if info.get('request_mode') == 'explicit' else {}
    ids = set(view.get('event_definitions', []))
    if info.get('request_mode') == 'explicit' and info.get('recovered_event_decisions'):
        from src.common.project_recovered_events import project_recovered_events
        graph = project_recovered_events(graph, et, {i: d for i, d in info['recovered_event_decisions'].items() if i in ids})
    definitions = graph.get('event_definitions', [])
    if not any(b['id'] in ids and 'candidate_tier' in b for b in definitions):
        return graph
    return dict(graph, event_definitions=[effective_binding(b, et, approvals.get(b['id'])) if b['id'] in ids
                                          else b for b in definitions])


def request_approvals(question, spans, et, definitions, rows, client, model, cache):
    """PURPOSE: Judge remaining explicit spans once against the complete selected ET inventory.
    INPUT: Missing request substrings and physically attributable candidates. OUTPUT: Request-local approvals, audit.
    """
    cards = []
    confirmed = set()
    for eid, row in rows.items():
        binding = definitions[eid]
        tier = row.get('effective_tier')
        if row['attribution']['status'] != 'pass' or tier not in {1,2}:
            continue
        label = binding.get('activity_label') or binding.get('activity')
        if tier == 1:
            confirmed.add(str(label).strip().casefold())
        cards.append(dict(id=eid, tier=tier, activity=label, axis=binding.get('unresolved_axis'),
                          source=binding['source_table'], rows=binding.get('row_selection'),
                          time=binding.get('occurrence_time_source'), dictionary=binding.get('review_dictionary', [])))
    remaining = sorted({s for s in spans if s in question and s.strip().casefold() not in confirmed})
    if not remaining or not any(c['tier'] == 2 for c in cards):
        return {}, None
    payload = dict(original_request=question, missing_spans=remaining, entity_type=et, definitions=cards)
    decisions, audit = review_once('tier2_context', payload, client, model, cache)
    approvals = {}
    for decision in decisions:
        eid = decision['id']
        binding = definitions[eid]
        if decision['span'] not in remaining or rows[eid]['effective_tier'] != 2 or not may_promote(binding):
            continue
        evidence = decision_evidence(binding, decision)
        if evidence:
            approvals[eid] = dict(evidence, span=decision['span'], entity_type=et['id'], axis=binding['unresolved_axis'])
    return approvals, audit
