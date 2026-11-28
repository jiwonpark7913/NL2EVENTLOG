"""Shared Step 2 quotation validation, independent of payload transport representation."""

from __future__ import annotations
import re
VERSION = 'step2-citation-v2-source-attribution'
QUOTATIONS = re.compile(r'"([^"\n]+)"|“([^”]+)”|(?<!\w)\'([^\'\n]+)\'(?!\w)|‘([^’]+)’')
SOURCE = re.compile(r'\b(?:dictionary|DD|source|column|evidence|definition|request|original_request)\b', re.I)
SOURCE_ID = re.compile(r'(?<!\w)[A-Z][A-Z0-9_]{0,24}:[A-Za-z0-9_:@.\-]+')
ATTRIBUTION_END = re.compile(
    r'(?:\b(?:says?|states?|reads?|quotes?)\s*(?:that\s*)?:?|'
    r'\b(?:definition|wording|text)\s+(?:is|reads)\s*:?|'
    r'\b(?:defines?|describes?|documents?)\b[^;\n]*\bas\s*:?|'
    r'\b(?:calls?|labels?|names?)\s+(?:it|this|that|the \w+)\s*:?|'
    r'\b(?:uses?|gives?)\s+(?:(?:the|a|this)\s+)?(?:label|wording|text|term)\s*:?)\s*$', re.I)
REQUEST_ALIGNMENT = re.compile(
    r'^\s*(?:(?:explicitly|directly)\s+)?(?:sets?|specifies?|identifies?|expresses?|requests?|names?|matches?)\b', re.I)


def nodes(value):
    """PURPOSE: Walk JSON independently of transport modules. INPUT: JSON value. OUTPUT: Node iterator."""
    yield value
    children = value.values() if isinstance(value, dict) else value if isinstance(value, list) else ()
    for child in children:
        yield from nodes(child)


def source_index(payload):
    """PURPOSE: Preserve source-specific text rather than treating unrelated evidence as interchangeable.
    INPUT: Original/restored payload. OUTPUT: ID-to-source-text lists, including duplicate supplied records.
    """
    indexed = {}
    for node in nodes(payload):
        if isinstance(node, dict):
            identifier = node.get('evidence_id') or node.get('id') or node.get('metadata_id')
            if isinstance(identifier, str):
                texts = [part for part in nodes(node) if isinstance(part, str) and part != identifier]
                indexed.setdefault(identifier, []).extend(texts)
    return indexed


def quotation_claim(text, match, question):
    """PURPOSE: Classify explicit source quotations without interpreting all quoted terms as citations.
    INPUT: Free-text explanation, quote match and original question.
    OUTPUT: (kind, source ID) or None; this syntactic classifier is not a semantic proof.
    """
    left = text[max(0, match.start()-300):match.start()]
    # A source mentioned in an earlier sentence/clause does not attribute a later category label.
    left = re.split(r'[;\n]|[.!?]\s+', left)[-1]
    right = text[match.end():match.end()+160]
    id_matches = list(SOURCE_ID.finditer(left))
    identifiers = [m.group().rstrip('.,;:') for m in id_matches]
    has_source = bool(SOURCE.search(left) or identifiers)
    adjacent_id = bool(id_matches and not left[id_matches[-1].end():].strip())
    literal = bool(ATTRIBUTION_END.search(left) or left.rstrip().endswith(':') or adjacent_id)
    if has_source and literal:
        if re.search(r'\b(?:request|original_request)\b', left, re.I) and not identifiers:
            return 'request', None
        return 'evidence', identifiers[-1] if identifiers else None
    # Quoted request wording followed by an alignment claim, e.g. “When ...” specifies the requested information.
    if REQUEST_ALIGNMENT.search(right):
        if re.search(r'\b(?:request(?:ed)?|case unit|information)\b', right, re.I):
            return 'request', None
        quote = next(part for part in match.groups() if part is not None)
        if quote.casefold() in question.casefold():
            return 'request', None
    if re.search(r'\b(?:verbatim|exact (?:quote|quotation)|quoted text)\s*:?\s*$', left, re.I):
        return 'evidence', None
    return None


def quoted_evidence_review(value, payload):
    """PURPOSE: Validate attributed quotes exactly and report ordinary quotations separately.
    INPUT: Parsed role response and the same original/restored payload for all encodings.
    OUTPUT: Diagnostics or ValueError for an unknown source or non-verbatim attributed quotation.
    Unattributed category/scare quotes are not asserted citations; structured citation gates remain unchanged.
    """
    corpus = [node for node in nodes(payload) if isinstance(node, str)]
    question = payload.get('original_request', '') if isinstance(payload, dict) else ''
    indexed = source_index(payload)
    counts = {'validator_version': VERSION, 'attributed_quotes': 0, 'ordinary_quoted_expressions': 0}
    for node in nodes(value):
        if not isinstance(node, str):
            continue
        for match in QUOTATIONS.finditer(node):
            claim = quotation_claim(node, match, question)
            if claim is None:
                counts['ordinary_quoted_expressions'] += 1
                continue
            counts['attributed_quotes'] += 1
            kind, identifier = claim
            if kind == 'request':
                sources = [question]
            elif identifier is not None:
                if identifier not in indexed:
                    raise ValueError('step2_unknown_citation_id')
                sources = indexed[identifier]
            else:
                sources = corpus
            quote = next(part for part in match.groups() if part is not None)
            if not quote.strip() or not any(quote in source for source in sources):
                raise ValueError('step2_quote_not_verbatim_in_supplied_payload')
    return counts


def validate_quoted_evidence(value, payload):
    """PURPOSE: Enforce the common citation guard for every Step 2 encoding.
    INPUT: Parsed output and unchanged domain payload. OUTPUT: None or a strict citation error.
    """
    quoted_evidence_review(value, payload)
