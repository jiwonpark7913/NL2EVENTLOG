"""Step 2 delivery views over the existing validated EEG inventories."""

from collections import defaultdict
from copy import deepcopy
import json
from time import perf_counter

from src.common.rank_evidence_documents import rank_documents


EVENT_LISTS = ('activities', 'candidates', 'complete_tier1_inventory')
CARD_FIELDS = ('name', 'meaning', 'code_meaning')
POLICY_VERSION = 'eeg-delivery-v1'


def role_cards(payload):
    """PURPOSE: Enumerate the role's explicit ET/ED inventories. INPUT: PI role payload.
    OUTPUT: Candidate cards including selection and review evidence, in wire order.
    """
    yield from payload.get('entity_types', [])
    if payload.get('case', {}).get('id'):
        yield payload['case']
    if payload.get('selection', {}).get('entity_type', {}).get('id'):
        yield payload['selection']['entity_type']
    for container in (payload, payload.get('selection', {}), payload.get('activity_review', {})):
        for key in EVENT_LISTS:
            yield from container.get(key, [])


def layer_payload(payload, definitions):
    """PURPOSE: Combine semantic cards and reusable source evidence.
    INPUT: Existing role payload and original ED index.
    OUTPUT: Independent payload with the original candidate IDs, roles, and verbatim evidence.
    """
    wire = deepcopy(payload)
    sources = defaultdict(list)
    for card in role_cards(wire):
        source = card.get('source')
        contexts = card.get('source_context')
        if source and contexts:
            for context in contexts:
                if context not in sources[source]:
                    sources[source].append(context)
            del card['source_context']
        quotes = card.get('dictionary_evidence')
        if quotes:
            card['dictionary_evidence'] = list(dict.fromkeys(quotes))
        definition = definitions.get(card.get('id'))
        if definition and 'time_role' in card and card['time_role'] is None:
            timestamp = (definition.get('timestamp_candidates') or [{}])[0]
            role = timestamp.get('time_role')
            if role and role not in ('unknown', 'unresolved'):
                card['time_role'] = role
    if sources:
        wire['source_context_by_table'] = dict(sources)
    return wire


def ranked_cards(cards, hints, limit):
    """PURPOSE: Search each available span independently and union the leading grounded matches.
    INPUT: Unique-ID cards, request phrases and per-phrase limit.
    OUTPUT: Selected IDs and phrases with no shared lexical tokens.
    """
    if len(cards) <= limit:
        return {card['id'] for card in cards}, []
    documents = [{'id': card['id'],
                  'text': ' '.join(str(card.get(field) or '') for field in CARD_FIELDS)}
                 for card in cards]
    chosen, missing = set(), []
    for hint in dict.fromkeys(hint for hint in hints if hint):
        matches = [item for item in rank_documents(hint, documents) if item['similarity']['bm25'] > 0]
        if matches:
            chosen.update(item['id'] for item in matches[:limit])
        else:
            missing.append(hint)
    return chosen, missing


class EEGDelivery:
    """Expose candidate restrictions only at the model input boundary."""

    def __init__(self, graph, mode, *, event_limit=4, entity_limit=3):
        """PURPOSE: Prepare local semantic collections and executable graph adjacency.
        INPUT: One complete runtime snapshot and B/C condition. OUTPUT: Per-query delivery adapter.
        """
        if mode not in ('layer', 'query'):
            raise ValueError('Unsupported EEG delivery mode')
        self.mode = mode
        self.event_limit = event_limit
        self.entity_limit = entity_limit
        self.definitions = {item['id']: item for item in graph.get('event_definitions', [])}
        self.event_cases = defaultdict(set)
        for path in graph.get('attribution_paths', []):
            if path.get('validation_status') == 'valid':
                self.event_cases[path.get('event_definition_id') or path.get('binding_id')].add(
                    path.get('target_entity_type_id') or path.get('to'))
        self.families = defaultdict(set)
        for definition in self.definitions.values():
            family = definition.get('canonical_activity_id')
            if family:
                self.families[family].add(definition['id'])
        self.related = defaultdict(set)
        for relation in graph.get('event_definition_pair_relationships', []):
            pair = relation.get('binding_pair', [])
            if relation.get('status') == 'supported' and len(pair) == 2:
                left, right = pair
                self.related[left].add(right)
                self.related[right].add(left)
        self.event_families = graph.get('event_families', [])
        for family in self.event_families:
            members = set(family['member_event_definition_ids'])
            for event_id in members:
                self.related[event_id].update(members - {event_id})
        self.audit = []

    def __call__(self, role, payload):
        """PURPOSE: Deliver one role-specific view, retaining structural checks on the full graph.
        INPUT: Actual existing role and payload. OUTPUT: Wire payload and a local diagnostic.
        """
        started = perf_counter()
        filtered, initial, expanded, fallback = self._restrict(role, payload) if self.mode == 'query' else (
            payload, set(), set(), 'projection_only')
        wire = layer_payload(filtered, self.definitions)
        before = sorted({card['id'] for card in role_cards(payload)})
        after = sorted({card['id'] for card in role_cards(wire)})
        if self.event_families and role in {'pi_events', 'pi_crosscheck', 'pi_focus'}:
            ids = set(after)
            relevant = []
            for family in self.event_families:
                broad = family['broad_event_definition_id']
                members = [eid for eid in family['member_event_definition_ids'] if eid in ids]
                if members or broad in ids:
                    relevant.append({'id': family['id'], 'phase': family['phase'], 'search_label': family['label'],
                                     'member_event_definition_ids': members,
                                     **({'overlapping_broad_ed': broad} if broad in ids else {})})
            if relevant:
                wire['event_families'] = relevant
        if self.mode == 'layer' and before != after:
            raise ValueError('Layer-wise delivery changed candidate IDs')
        self.audit.append({'role': role, 'mode': self.mode, 'policy': POLICY_VERSION,
                           'before_ids': before, 'after_ids': after,
                           'initial_search_ids': sorted(initial), 'expanded_ids': sorted(expanded),
                           'fallback': fallback, 'seconds': perf_counter() - started,
                           'before_bytes': len(json.dumps(payload, ensure_ascii=False).encode()),
                           'after_bytes': len(json.dumps(wire, ensure_ascii=False).encode())})
        return wire

    def _restrict(self, role, payload):
        """PURPOSE: Narrow explicit choice inventories with conservative fallbacks.
        INPUT: Role and existing permitted cards. OUTPUT: Payload, search seeds, expansion, fallback reason.
        """
        if role == 'pi_cases':
            parsed = payload['request_interpretation']
            if parsed['activity_scope'] != 'explicit':
                return payload, set(), set(), 'retain_all_cases_for_implicit_scope'
            cards = payload['entity_types']
            case = parsed['case_requirement']
            seeds, _ = ranked_cards(cards, (case['span'], case['meaning'], payload['original_request']),
                                    self.entity_limit)
            docs = [{'id': d['id'], 'name': d.get('activity_label') or d.get('activity'),
                     'meaning': (d.get('activity_semantics') or {}).get('meaning')}
                    for d in self.definitions.values()]
            requirements = parsed['activity_requirements']
            event_seeds, _ = ranked_cards(docs, (r['meaning'] for r in requirements), self.event_limit)
            confirmed = set().union(*(self.event_cases[e] for e in event_seeds))
            kept = seeds | confirmed
            matches = [card for card in cards if card['id'] in kept]
            if not seeds or len(matches) < payload['max_candidates']:
                return payload, seeds | event_seeds, kept, 'case_inventory_too_small'
            return dict(payload, entity_types=matches,
                        case_scopes=[scope for scope in payload['case_scopes'] if scope['et'] in kept]), (
                            seeds | event_seeds), kept, ''
        if role == 'pi_events':
            cards = payload['activities']
            requirements = payload['activity_requirements']
        elif role == 'pi_crosscheck' and payload.get('activity_review'):
            review = payload['activity_review']
            cards, requirements = review['candidates'], review['requirements']
        else:
            return payload, set(), set(), 'preserve_role_inventory'
        if not cards or not requirements:
            return payload, set(), set(), 'empty_explicit_inventory'
        # Reviewing all phases of a family and all paths is part of the existing PI policy.
        if any(r.get('coverage') == 'all' for r in requirements):
            return payload, set(), set(), 'retain_complete_activity_family_scope'
        seeds, expanded = set(), set()
        for req in requirements:
            eligible = [card for card in cards if 'requirement_ids' not in card
                        or req['id'] in card['requirement_ids']]
            found, missing = ranked_cards(eligible, (req['span'], req['meaning']), self.event_limit)
            if not found or len(missing) == 2:
                return payload, seeds | found, expanded, 'no_grounded_match_for_requirement'
            seeds.update(found)
        expanded.update(seeds)
        for event_id in seeds:
            family = self.definitions.get(event_id, {}).get('canonical_activity_id')
            if family:
                expanded.update(self.families[family])
            expanded.update(self.related[event_id])
        if role == 'pi_crosscheck':
            expanded.update(payload['selection']['ids'])
            diagnostic_ids = {card['id'] for card in cards if not card.get('eligible', True)
                              or card.get('case_attribution') != 'pass'}
            expanded.update(diagnostic_ids)
            if payload.get('complete_tier1_inventory'):
                return payload, seeds, expanded, 'retain_full_context_definition_review'
            return dict(payload, activity_review=dict(review, candidates=[
                card for card in cards if card['id'] in expanded])), seeds, expanded, ''
        return dict(payload, activities=[card for card in cards if card['id'] in expanded]), seeds, expanded, ''
