"""Deliver a complete candidate catalog with detail ordered by request evidence."""

from src.common.rank_evidence_documents import rank_documents


def prepare_cards(cards, requirements, families, *, detail_limit):
    """PURPOSE: Prioritize semantic detail without reducing the candidate inventory.
    INPUT: Existing review cards, grounded requirements, family records, detail budget.
    OUTPUT: Priority-ordered lightweight proposal cards and IDs whose evidence was expanded.
    """
    documents = [{'id': card['id'], 'text': ' '.join(str(card.get(key) or '')
                                                    for key in ('name', 'meaning', 'code_meaning', 'carrier_code'))}
                 for card in cards]
    priority = set()
    for item in requirements:
        ranked = rank_documents(' '.join((item['span'], item['meaning'])), documents)
        priority.update(match['id'] for match in ranked[:detail_limit] if match['similarity']['bm25'] > 0)
    for family in families:
        members = set(family.get('member_event_definition_ids', []))
        members.add(family.get('broad_event_definition_id'))
        if priority & members and len(members) <= detail_limit:
            priority.update(members)
    by_family = {}
    for family in families:
        for identifier in [family.get('broad_event_definition_id'), *family.get('member_event_definition_ids', [])]:
            by_family.setdefault(identifier, []).append(family['id'])
    ordered = sorted(cards, key=lambda card: (card['id'] not in priority, card['id']))
    result = []
    for card in ordered:
        compact = dict(card)
        if card['id'] in by_family:
            compact['family_ids'] = by_family[card['id']]
        if card['id'] not in priority:
            fields = ('meaning', 'code_meaning', 'dictionary_evidence', 'source_context')
            compact = {k: v for k, v in compact.items() if k not in fields}
            # The role label and ID remain resolvable until independent review reads the evidence.
            compact['role_projections'] = [{k: v for k, v in role.items() if k != 'evidence'}
                                           for role in compact['role_projections']]
        result.append(compact)
    return result, sorted(priority & {card['id'] for card in cards})
