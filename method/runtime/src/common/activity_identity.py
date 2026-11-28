"""Separate evidence-supported activity identity from output names."""

from src.common.graph_identifiers import content_hash


def activity_identity(definition):
    """PURPOSE: Return a conservative, label-independent grouping identity.
    INPUT: Runtime ED with physical source, semantic signature and optional proven equivalence identifier.
    OUTPUT: Stable Activity ID scoped to its evidence basis, lifecycle and occurrence grain.
    """
    if identity := definition.get('activity_identity'):
        return identity
    signature = definition.get('semantic_signature') or {}
    proven = definition.get('verified_activity_equivalence_id')
    source = definition.get('source_table')
    grain = definition.get('source_row_key', [])
    if proven and signature.get('interpretation_status') == 'supported':
        phase = (definition.get('timestamp_pairing') or {}).get('phase') or signature.get('temporal_role')
        subject = signature.get('subject_id') or source
        basis = ['equivalence', proven, phase, subject, grain]
    else:
        # The ED ID already encodes its physical lifecycle clock and occurrence scope.
        basis = ['definition', definition['id'], source, grain]
    return 'activity:' + content_hash(basis)
