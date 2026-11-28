"""Internal typed Entity keys; no independent namespace semantic judgment."""

from __future__ import annotations


def identity_scope_id(mapping):
    """PURPOSE: Read the collision-prevention component of a validated identification mapping.
    INPUT: New mapping or legacy mapping containing namespace_id.
    OUTPUT: Stable internal component ID; disagreeing aliases raise rather than merge Entities.
    """
    current, legacy = mapping.get('identity_scope_id'), mapping.get('namespace_id')
    if current and legacy and current != legacy:
        raise ValueError('Identity scope aliases disagree')
    value = current or legacy
    if not value:
        raise ValueError('Missing internal identity scope')
    return value


def typed_entity_key(mapping, values):
    """PURPOSE: Compare canonical Entity keys without dropping type or composite-key components.
    INPUT: Validated mapping and ordered complete SQLite scalar tuple.
    OUTPUT: Hashable internal component + typed tuple; not an additional business/LLM concept.
    """
    parts = tuple(('null' if v is None else 'integer' if isinstance(v, int) else
                   'real' if isinstance(v, float) else 'blob' if isinstance(v, bytes) else 'text', v)
                  for v in values)
    return identity_scope_id(mapping), parts


def correspondence_judgment(value):
    """PURPOSE: Read old identity-review output once through an explicitly deprecated field alias.
    INPUT: Review object with identity_correspondence or legacy same_key_namespace.
    OUTPUT: Copy containing only the current correspondence field; conflicting aliases become UNKNOWN.
    The legacy field is never sent in new schemas and is never a second acceptance condition.
    """
    result = dict(value)
    legacy = result.pop('same_key_namespace', None)
    if legacy is not None:
        current = result.get('identity_correspondence', legacy)
        result['identity_correspondence'] = current if current == legacy else 'UNKNOWN'
    if 'namespace_evidence_validated' in result:
        result['correspondence_evidence_validated'] = result.pop('namespace_evidence_validated')
    return result


def identity_review_judgment(value):
    """PURPOSE: Read a representative-key identity review in the current (v4) field names.
    INPUT: Current review, a stored pre-v4 review, or a legacy targeted-review judgment used as override.
    OUTPUT: Copy with ``same_entity_type`` (from legacy ``same_object_type``) and the current
    correspondence field; conflicting aliases become UNKNOWN. Legacy targeted reviews keep their own
    contract; this adapter is applied only at the identity-review boundary.
    """
    result = correspondence_judgment(value)
    legacy = result.pop('same_object_type', None)
    if legacy is not None:
        current = result.get('same_entity_type', legacy)
        result['same_entity_type'] = current if current == legacy else 'UNKNOWN'
    return result
