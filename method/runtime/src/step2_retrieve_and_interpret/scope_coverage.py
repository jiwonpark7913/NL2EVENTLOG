"""Check independent scope judgments against the offered candidates and PI selection."""

import re

from src.step2_retrieve_and_interpret.event_definition_granularity import definition_subsumption
from src.step2_retrieve_and_interpret.verify_activity_requirements import is_source_span


def check_scope(question, decisions, offered, selected, definitions, *, required=(), exhaustive=True):
    """PURPOSE: Detect missing judgments, excluded/extra selections and unmet required occurrences.
    INPUT: Original text, model judgments, offered cards, selected and independently required ED IDs.
    OUTPUT: Stable diagnostic codes and IDs; no model or DB calls.
    """
    offered_by_id = {card['id']: card for card in offered}
    judged = {item['event_definition_id']: item for item in decisions}
    missing = sorted(offered_by_id.keys() - judged.keys())
    malformed = set(judged) - offered_by_id.keys()
    included, uncertain = set(required), []
    for identifier, item in sorted(judged.items()):
        if identifier not in offered_by_id:
            continue
        card = offered_by_id[identifier]
        quotes = [*card.get('dictionary_evidence', []), *card.get('source_context', [])]
        basis = item['quote'].strip()
        grounded = (is_source_span(question, item['span']) and basis and
                    any(basis in text for text in quotes or [card.get('meaning') or card['name']]))
        if not grounded:
            malformed.add(identifier)
        if item['decision'] == 'include':
            included.add(identifier)
        elif item['decision'] == 'unresolved':
            uncertain.append(identifier)
    chosen = set(selected)
    universe = chosen | included
    subsumes = definition_subsumption(universe, definitions) if universe <= definitions.keys() else {}
    covered = chosen | {child for identifier in chosen for child in subsumes.get(identifier, ())}
    # A generic ED can satisfy a required specialization only if the physical occurrence
    # range itself is equivalent. Subsumption alone is insufficient.
    missing_required = sorted(included - chosen - {i for i in covered if any(
        i in subsumes.get(j, ()) and j in subsumes.get(i, ()) for j in chosen)})
    return {
        'missing_judgments': missing,
        'invalid_judgments': sorted(malformed),
        'duplicate_judgments': len(judged) != len(decisions),
        'unknown_scope': uncertain,
        'missing_required': missing_required,
        'unsupported_selection': sorted(chosen - included),
        'required_ids': sorted(included),
        'exhaustive': exhaustive,
    }


def documented_family_members(requirement, reviewed_ids, candidates):
    """PURPOSE: Detect documented co-members that a singleton verdict would silently hide.
    INPUT: Original requirement and its review IDs plus the attributable candidate cards.
    OUTPUT: Required peer IDs for source-supported bounded family wording.
    """
    span = requirement['span'].casefold()
    words = re.findall(r'[a-z]+', span)
    qualified = requirement.get('coverage') == 'all' or bool(re.search(r'\b(all|each|every|both)\b|\bfrom\b.+\bto\b', span))
    plural = bool(words and words[-1].endswith('s') and not words[-1].endswith(('ss', 'us', 'is')))
    if not (qualified or plural):
        return set()
    seed_ids = set(reviewed_ids)
    required = set()
    for seed in candidates:
        if seed['id'] not in seed_ids or not seed.get('carrier_code') or not seed.get('eligible'):
            continue
        for peer in candidates:
            if (peer['id'] == seed['id'] or not peer.get('carrier_code')
                    or not peer.get('eligible') or peer.get('case_attribution') != 'pass'
                    or (peer['source'], peer.get('occurrence_time')) != (seed['source'], seed.get('occurrence_time'))):
                continue
            code_words = (str(seed['carrier_code']), str(peer['carrier_code']))
            for text in seed.get('source_context', []):
                # One documented clause must explicitly co-classify both values. Shared
                # source tables, shared clocks and generic FK reachability are insufficient.
                for clause in re.split(r'[.;\n]', text):
                    if (re.search(r'\b(and|both)\b', clause, re.I)
                            and all(re.search(r'(?<!\w)' + re.escape(code) + r'(?!\w)', clause) for code in code_words)
                            and (re.search(r'\b(actual|completed|started|occurs?|represents?)\b', clause, re.I))):
                        required.add(peer['id'])
    return required
