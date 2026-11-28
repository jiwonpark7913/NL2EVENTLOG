"""Persist a single EEG as three layers and their cross-layer links."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile


FORMAT_VERSION = 'eeg-layers-v2'
LAYER_FIELDS = {
    'entity_layer': frozenset({
        'objects', 'table_key_records', 'object_types', 'concepts', 'object_concepts',
        'selectable_object_concepts', 'entity_types', 'concept_rejected', 'entity_type_separations',
        'entity_instance_maps', 'entity_case_populations', 'semantic_entity_memberships',
        'identification_targets', 'identification_rules', 'entity_identification_rules',
        'entity_identity_decisions', 'identity_mapping_assessments', 'semantic_object_groups',
        'global_ot_review', 'rollups', 'entity_model_diagnostics', 'semantic_classification_pairs',
    }),
    'event_layer': frozenset({
        'bindings', 'event_definitions', 'activity_bindings', 'activity_candidates',
        'event_definition_pair_relationships', 'occurrence_identity_rules', 'event_table_candidates', 'event_families',
        'event_interpretation_candidates', 'event_review_queue', 'event_semantics_diagnostics',
        'carrier_lifecycle_pair_proofs', 'retired_event_definitions',
    }),
    'db_layer': frozenset({
        'database', 'database_fingerprint', 'tables', 'physical_schema', 'physical_tables',
        'key_profiles', 'profiles', 'data_dictionary', 'normalized_dictionary', 'references',
        'relations', 'relationships', 'relationship_candidates', 'table_reference_assessments',
        'reference_diagnostics', 'relationship_discovery_cost', 'relationship_budget_exhausted',
        'bridges', 'table_roles', 'table_semantic_profiles', 'business_value_evidence',
        'timestamps', 'unresolved_temporal_units', 'carrier_timestamp_matrix',
    }),
    'links': frozenset({
        'attribution_paths', 'event_entity_links', 'event_entity_associations',
        'timestamp_event_links', 'view_candidates',
    }),
    'metadata': frozenset(),
}
COLLECTION_LAYER = {field: layer for layer, fields in LAYER_FIELDS.items() for field in fields}
EVENT_COLLECTIONS = ('event_definitions', 'bindings', 'activity_bindings', 'retired_event_definitions')
LINK_FIELDS = {
    'event_sources': frozenset({
        'table', 'source_table', 'source_kind', 'source_key', 'activity_source',
        'activity_column', 'raw_values', 'ts_id', 'timestamp_candidates', 'timestamp_columns',
        'timestamp_pairing', 'occurrence_time_source', 'documented_source_conditions',
        'source_row_key', 'row_selection',
    }),
    'event_attributions': frozenset({
        'paths', 'concept_paths', 'event_entity_links', 'lifecycle_associations',
        'object_association_ids',
    }),
}
ENTITY_COLLECTIONS = ('entity_types', 'selectable_object_concepts', 'concepts', 'object_concepts',
                      'objects', 'table_key_records', 'object_types')
ENTITY_SOURCE_FIELDS = frozenset({
    'table', 'pk', 'key_kind', 'key_columns', 'anchor_table', 'member_tables', 'member_keys',
})
ARTIFACT_NAMES = tuple(f'{layer}.json' for layer in LAYER_FIELDS)


def digest_bytes(raw):
    """PURPOSE: Identify serialized content. INPUT: Bytes. OUTPUT: SHA256 hex digest."""
    return hashlib.sha256(raw).hexdigest()


def json_bytes(value):
    """PURPOSE: Encode a stable JSON snapshot. INPUT: JSON-compatible data. OUTPUT: UTF-8 bytes."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()


def write_json(path, value):
    """PURPOSE: Replace one artifact atomically. INPUT: Path and JSON value. OUTPUT: SHA256 digest."""
    raw = json_bytes(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.write-', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(raw)
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return digest_bytes(raw)


def _partition_fields(sections, collection, groups):
    """PURPOSE: Move nested physical and path fields into links keyed by the original record ID.
    INPUT: Layer sections, collection name and mapping of link groups to field sets.
    OUTPUT: Updates the sections; leaves each record's order, ID and semantic fields in its layer.
    """
    layer = sections[COLLECTION_LAYER[collection]]
    if collection not in layer:
        return
    records = []
    for record in layer[collection]:
        remaining = record.copy()
        for group, fields in groups.items():
            fragment = {key: remaining.pop(key) for key in fields if key in remaining}
            if not fragment:
                continue
            by_id = sections['links'].setdefault('record_links', {}).setdefault(group, {}).setdefault(collection, {})
            identifier = record['id']
            if identifier in by_id:
                raise ValueError(f'Duplicate EEG record ID in {collection}: {identifier}')
            by_id[identifier] = fragment
        records.append(remaining)
    layer[collection] = records


def _split_view(view):
    """PURPOSE: Partition one graph projection with its lossless metadata.
    INPUT: A native or runtime EEG mapping. OUTPUT: One mapping per layer, plus links and metadata.
    """
    sections = {layer: {} for layer in LAYER_FIELDS}
    for field, value in view.items():
        sections[COLLECTION_LAYER.get(field, 'metadata')][field] = value
    for collection in EVENT_COLLECTIONS:
        _partition_fields(sections, collection, LINK_FIELDS)
    for collection in ENTITY_COLLECTIONS:
        _partition_fields(sections, collection, {'entity_representations': ENTITY_SOURCE_FIELDS})
    return sections


def _join_view(sections):
    """PURPOSE: Hydrate the existing flat API from one projection's layer files.
    INPUT: Validated sections. OUTPUT: Graph with the same fields, list order, IDs and paths as saved.
    """
    fields = {}
    for section in sections.values():
        fields.update(section)
    indexed = {}
    for collections in fields.pop('record_links', {}).values():
        for collection, by_id in collections.items():
            if collection not in indexed:
                indexed[collection] = {record['id']: record for record in fields[collection]}
            records = indexed[collection]
            for identifier, fragment in by_id.items():
                record = records[identifier]
                if record.keys() & fragment.keys():
                    raise ValueError(f'Overlapping EEG link fields for {collection}: {identifier}')
                record.update(fragment)
    return fields


def write_eeg_layers(directory, runtime, *, native_bundle=None):
    """PURPOSE: Persist the full runtime EEG and optional native builder state in layered files.
    INPUT: Destination and existing graph mappings; the caller publishes the manifest after the write.
    OUTPUT: Filenames and SHA256 checksums. The input objects are unchanged.
    """
    directory = Path(directory)
    runtime_fields = dict(runtime)
    views = {'runtime': runtime_fields}
    if 'dbu_rewrite' in runtime_fields and isinstance(runtime_fields['dbu_rewrite'], dict):
        views['runtime_native'] = runtime_fields.pop('dbu_rewrite')
    native_is_runtime_native = False
    if native_bundle is not None:
        build_fields = dict(native_bundle)
        native_graph = build_fields.pop('data')
        native_is_runtime_native = 'runtime_native' in views and native_graph == views['runtime_native']
        if not native_is_runtime_native:
            views['native'] = native_graph
        views['native_build'] = build_fields

    artifacts = {layer: {} for layer in LAYER_FIELDS}
    for view, graph in views.items():
        for layer, section in _split_view(graph).items():
            artifacts[layer][view] = section
    artifacts['metadata']['native_is_runtime_native'] = native_is_runtime_native
    return {f'{layer}.json': write_json(directory / f'{layer}.json', content)
            for layer, content in artifacts.items()}


def read_eeg_layers(directory, checksums):
    """PURPOSE: Restore independent runtime and native EEG projections from verified layer files.
    INPUT: Directory and manifest checksums. OUTPUT: (runtime EEG, optional native builder bundle).
    Missing or corrupted artifacts raise before the projections are returned.
    """
    directory = Path(directory)
    sections = {}
    for name in ARTIFACT_NAMES:
        raw = (directory / name).read_bytes()
        if digest_bytes(raw) != checksums[name]:
            raise ValueError(f'EEG layer checksum mismatch: {name}')
        sections[name.removesuffix('.json')] = json.loads(raw)
    metadata = sections['metadata']
    native_is_runtime_native = metadata.pop('native_is_runtime_native')
    views = {view: _join_view({layer: content[view] for layer, content in sections.items()})
             for view in metadata}
    runtime = views['runtime']
    if 'runtime_native' in views:
        runtime['dbu_rewrite'] = views['runtime_native']
    native_bundle = views.get('native_build')
    if native_bundle is not None:
        native_bundle['data'] = (deepcopy(views['runtime_native']) if native_is_runtime_native
                                 else views['native'])
    return runtime, native_bundle
