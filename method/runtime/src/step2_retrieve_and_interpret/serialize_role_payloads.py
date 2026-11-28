"""Lossless Step 2 wire representations; no candidate or semantic filtering."""

from __future__ import annotations
from src.common.prompt_loader import load_prompt
from collections import Counter
import copy
import hashlib
import json
import re
VERSION = 'step2-wire-v3-flat-evidence-verbatim'
REF = '__step2_ref__'
ENVELOPE = '__step2_pool__'
POOL_ID = re.compile(r'(?<![\w])POOL:\d+(?![\w])')
VERBATIM_INSTRUCTIONS = load_prompt('step2_retrieve_and_interpret', 'preserve_verbatim_evidence')
INSTRUCTIONS = load_prompt('step2_retrieve_and_interpret', 'decode_pooled_evidence') + VERBATIM_INSTRUCTIONS
DETAIL_ROOTS = frozenset({'dictionary_evidence', 'table_dictionary', 'key_dictionary',
    'evidence', 'validation_evidence', 'membership_evidence', 'joins', 'map_sql',
    'map_parameters', 'statistics', 'details', 'entity_identity_validation'})
INLINE = frozenset({'event_definition_id', 'candidate_id', 'object_id', 'target_ot_id',
    'selected_candidate_ids', 'candidate_ids', 'activity', 'activity_label', 'name',
    'business_meaning', 'business_meaning_hint', 'business_definition',
    'instance_granularity', 'instance_granularity_hint', 'status', 'passed',
    'validation_status', 'interpretation_status', 'eligible', 'history_supported',
    'confirmation_allowed', 'review_eligible', 'source_member', 'membership',
    'source_table', 'reason', 'evidence_ids'})


def serialize(value, *, compact=True):
    """PURPOSE: Encode JSON without altering string content or scalar types.
    INPUT: JSON-compatible value and spacing switch. OUTPUT: Deterministic JSON; rejects NaN.
    """
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                      **({'separators': (',', ':')} if compact else {}))


def fingerprint(value):
    """PURPOSE: Compare complete typed JSON values. INPUT: JSON. OUTPUT: SHA256 of compact JSON."""
    return hashlib.sha256(serialize(value).encode()).hexdigest()


def walk(value):
    """PURPOSE: Traverse all JSON nodes without mutation. INPUT: JSON. OUTPUT: Iterator of nodes."""
    yield value
    values = value.values() if isinstance(value, dict) else value if isinstance(value, list) else ()
    for child in values:
        yield from walk(child)


def check_reserved(value):
    """PURPOSE: Detect ambiguous transport markers before pooling.
    INPUT: Original JSON. OUTPUT: None or ValueError; original text is never rewritten.
    """
    for node in walk(value):
        if isinstance(node, dict) and ({REF, ENVELOPE} & node.keys()):
            raise ValueError('step2_reserved_key_collision')
        if isinstance(node, str) and POOL_ID.search(node):
            raise ValueError('step2_reserved_pool_id_collision')


def contains_inline(value):
    """PURPOSE: Keep nested identity and core validation fields visible.
    INPUT: Candidate detail node. OUTPUT: Whether replacing the entire node would hide protected keys.
    """
    return any(isinstance(n, dict) and INLINE.intersection(n) for n in walk(value))


def pool_payload(payload, *, minimum_bytes=240):
    """PURPOSE: Share large identical detail values once per request with flat refs.
    INPUT: Full original payload and minimum node size; never a truncation limit.
    OUTPUT: Envelope whose expansion is type/array/source equivalent to the original, or explicit error.
    """
    check_reserved(payload)
    counts = Counter()

    def eligible_nodes(node, detail=False):
        """PURPOSE: Enumerate eligible DD/path/detail nodes. INPUT: JSON/subtree scope. OUTPUT: Canonical values."""
        if detail and isinstance(node, (dict, list, str)) and not contains_inline(node):
            raw = serialize(node)
            if len(raw.encode()) >= minimum_bytes:
                yield raw
        if isinstance(node, dict):
            for key, child in node.items():
                if key not in INLINE:
                    yield from eligible_nodes(child, detail or key in DETAIL_ROOTS)
        elif isinstance(node, list):
            for child in node:
                yield from eligible_nodes(child, detail)

    counts.update(eligible_nodes(payload))
    selected = {raw for raw, count in counts.items() if count > 1 and
                (count - 1) * len(raw.encode()) > count * 48 + 80}
    registry, ids = {}, {}

    def encode(node, detail=False):
        """PURPOSE: Encode the maximal eligible duplicate with original flat content.
        INPUT: JSON node/detail scope. OUTPUT: Copy or local ref; pool entries never recursively encode.
        """
        if detail and isinstance(node, (dict, list, str)) and not contains_inline(node):
            raw = serialize(node)
            if raw in selected:
                if raw not in ids:
                    ident = 'POOL:' + str(len(ids) + 1).zfill(4)
                    ids[raw] = ident
                    registry[ident] = copy.deepcopy(node)
                return {REF: ids[raw]}
        if isinstance(node, dict):
            return {key: copy.deepcopy(child) if key in INLINE else
                    encode(child, detail or key in DETAIL_ROOTS) for key, child in node.items()}
        if isinstance(node, list):
            return [encode(child, detail) for child in node]
        return node

    encoded = encode(payload)
    envelope = {ENVELOPE: VERSION, 'data': encoded, 'evidence_pool': registry}
    restored = restore_payload(envelope)
    if serialize(restored) != serialize(payload):
        raise ValueError('step2_payload_preservation_failed')
    return envelope


def restore_payload(envelope):
    """PURPOSE: Expand a self-contained pool and reject malformed/dangling/cyclic/nested refs.
    INPUT: Wire envelope. OUTPUT: New original payload; scalar types/strings/order stay unchanged.
    """
    if not isinstance(envelope, dict) or set(envelope) != {ENVELOPE, 'data', 'evidence_pool'}:
        raise ValueError('step2_invalid_envelope')
    if envelope[ENVELOPE] != VERSION or not isinstance(envelope['evidence_pool'], dict):
        raise ValueError('step2_invalid_envelope_version_or_pool')
    registry = envelope['evidence_pool']
    if any(not re.fullmatch(r'POOL:\d+', key) for key in registry):
        raise ValueError('step2_invalid_pool_id')
    def expand(node, active=()):
        """PURPOSE: Validate each pointer and expand it. INPUT: JSON and active ref stack. OUTPUT: JSON copy."""
        if isinstance(node, dict):
            if ENVELOPE in node:
                raise ValueError('step2_reserved_key_collision')
            if REF in node:
                if set(node) != {REF} or not isinstance(node[REF], str):
                    raise ValueError('step2_invalid_reference')
                ident = node[REF]
                if ident not in registry:
                    raise ValueError('step2_missing_reference')
                if ident in active:
                    raise ValueError('step2_cyclic_reference')
                result = expand(registry[ident], (*active, ident))
                if active:
                    raise ValueError('step2_nested_reference')
                return result
            return {key: expand(value, active) for key, value in node.items()}
        if isinstance(node, list):
            return [expand(value, active) for value in node]
        return node
    # Validate unused entries too; reject smuggled references even if data does not reach them.
    for ident, node in registry.items():
        expand(node, (ident,))
    return expand(envelope['data'])


def prepare_payload(payload, mode='compact'):
    """PURPOSE: Build original/A/B wire text and preservation audit without mutating domain data.
    INPUT: JSON and original|compact|pooled. OUTPUT: serialized/wire/suffix/encoding/hash metadata.
    Pooling errors fail explicitly; no silent candidate pruning. Small pools fall back to compact.
    """
    if mode not in {'original', 'compact', 'pooled'}:
        raise ValueError('step2_unknown_payload_encoding')
    original = fingerprint(payload)
    compact = serialize(payload)
    wire, suffix, effective, count = payload, '', mode, 0
    if mode == 'pooled':
        suffix = VERBATIM_INSTRUCTIONS
        candidate = pool_payload(payload)
        if candidate['evidence_pool'] and len(serialize(candidate).encode()) + len(INSTRUCTIONS.encode()) < len(compact.encode()):
            wire, suffix, count = candidate, INSTRUCTIONS, len(candidate['evidence_pool'])
        else:
            effective = 'compact'
    text = serialize(wire, compact=mode != 'original')
    restored = restore_payload(wire) if effective == 'pooled' else json.loads(text)
    if fingerprint(restored) != original:
        raise ValueError('step2_payload_preservation_failed')
    return {'serialized': text, 'wire': wire, 'system_suffix': suffix, 'encoding': effective,
            'requested_encoding': mode, 'pool_entries': count, 'payload_sha256': original,
            'wire_sha256': hashlib.sha256(text.encode()).hexdigest(), 'roundtrip_verified': True}


def reject_output_pool_ids(value):
    """PURPOSE: Forbid temporary transport IDs/refs in model or cached output.
    INPUT: Parsed response. OUTPUT: None or ValueError; original domain ID checks remain in interpreter.
    """
    for node in walk(value):
        if isinstance(node, dict) and ({REF, ENVELOPE} & node.keys()):
            raise ValueError('step2_output_transport_reference')
        if isinstance(node, str) and POOL_ID.search(node):
            raise ValueError('step2_output_pool_id')


def validate_quoted_evidence(value, payload):
    """PURPOSE: Retain the compatibility entry point for transport-independent citation checks.
    INPUT: Parsed output and original/restored payload. OUTPUT: None or a strict source/quote error.
    """
    from src.step2_retrieve_and_interpret.validate_evidence_citations import validate_quoted_evidence as validate
    validate(value, payload)
