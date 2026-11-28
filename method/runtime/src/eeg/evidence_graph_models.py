"""Typed in-memory records for the DBU rewrite."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Column:
    """PURPOSE: Represent one physical column and immutable schema facts.
    INPUT: Names, declared type, constraint flags and ordinal.
    OUTPUT: Dataclass consumed by profiling and timestamp discovery.
    """
    id: str
    name: str
    declared_type: str
    not_null: bool
    pk_position: int
    ordinal: int
    unique: bool = False


@dataclass
class Table:
    """PURPOSE: Represent one SQLite user table with keys and FK groups.
    INPUT: DDL/PRAGMA-normalized schema facts.
    OUTPUT: Table record used throughout DBU.
    """
    id: str
    name: str
    ddl: str
    columns: list[Column]
    primary_key: list[str]
    unique_keys: list[list[str]]
    foreign_keys: list[dict[str, Any]]


def representative_key(table: Table, key_profiles=None) -> tuple[list[str], str] | None:
    """PURPOSE: Select a PK or deterministic UNIQUE NOT NULL key as one Table's representative Key.
    INPUT: Physical schema and optional exact declared-key profiles.
    OUTPUT: Ordered declared key plus key kind, or None when the table has no admissible key.
    """
    if table.primary_key:
        return list(table.primary_key), "primary_key"
    measured = {(tuple(k['columns'])): k for k in (key_profiles or []) if k['table'] == table.name}
    validated = [list(key) for key in table.unique_keys if measured.get(tuple(key), {}).get('unique')]
    if validated:
        return min(validated, key=lambda key: (len(key), key)), "unique_measured_non_null"
    not_null = {column.name for column in table.columns if column.not_null}
    candidates = [list(key) for key in table.unique_keys if key and set(key) <= not_null]
    if not candidates:
        return None
    return min(candidates, key=lambda key: (len(key), key)), "unique_not_null"


@dataclass
class EvidenceGraph:
    """PURPOSE: Expose deterministic graph records and Step-2 lookup APIs.
    INPUT: Fully assembled graph mapping.
    OUTPUT: Query-independent Evidence Graph facade.
    """
    data: dict[str, Any]
    _bindings: dict[str, dict[str, Any]] = field(init=False, repr=False)
    _timestamps: dict[str, dict[str, Any]] = field(init=False, repr=False)
    _concepts: dict[str, dict[str, Any]] = field(init=False, repr=False)
    _attribution_paths: dict[str, dict[str, Any]] = field(init=False, repr=False)
    _activity_object_links: dict[str, list[dict[str, Any]]] = field(init=False, repr=False)
    _binding_object_associations: dict[tuple[str, str], dict[str, Any]] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """PURPOSE: Build immutable lookup indexes after construction.
        INPUT: Graph lists in self.data.
        OUTPUT: In-memory binding and timestamp dictionaries.
        """
        self._bindings = {item["id"]: item for item in self.data.get("bindings", [])}
        self._timestamps = {item["ts_id"]: item for item in self.data.get("timestamps", [])}
        self._concepts = {item["id"]: item for item in self.data.get("concepts", [])}
        self._attribution_paths = {item["id"]: item
                                   for item in self.data.get("attribution_paths", [])}
        self._activity_object_links = {}
        for item in self.data.get('event_entity_links', []):
            self._activity_object_links.setdefault(item['event_definition_id'], []).append(item)
        self._binding_object_associations = {
            (item['event_definition_id'], item["object_concept_id"]): item
            for item in self.data.get('event_entity_associations', [])}

    def activity_candidates(self) -> list[dict[str, Any]]:
        """PURPOSE: Return the only search inventory exposed to Step 2.
        INPUT: This graph.
        OUTPUT: Defensive copies of name/description/binding IDs.
        """
        return [dict(item) for item in self.data.get("activity_candidates", [])]

    def binding(self, event_definition_id: str) -> dict[str, Any]:
        """PURPOSE: Resolve an enumerated binding for ES construction.
        INPUT: Existing binding ID.
        OUTPUT: Binding mapping; raises KeyError for hallucinated IDs.
        """
        return dict(self._bindings[event_definition_id])

    def paths(self, event_definition_id: str, to_object: str) -> list[dict[str, Any]]:
        """PURPOSE: Resolve pre-enumerated child-to-parent attribution paths.
        INPUT: Binding ID and target Object ID.
        OUTPUT: Matching path mappings.
        """
        physical = [dict(item) for item in self._bindings[event_definition_id].get("paths", [])
                    if item.get("to") == to_object]
        logical = [dict(item) for item in self._bindings[event_definition_id].get("concept_paths", [])
                   if item.get("to") == to_object]
        return [*physical, *logical]

    def concepts(self) -> list[dict[str, Any]]:
        """PURPOSE: Return logical case populations without hiding physical Objects.
        INPUT: This graph.
        OUTPUT: Defensive copies of entity/identity/supertype concepts.
        """
        return [dict(item) for item in self.data.get("concepts", [])]

    def table_reference_assessments(self) -> list[dict[str, Any]]:
        """PURPOSE: Expose threshold-based classifications of child->parent Table references.
        INPUT: This graph.
        OUTPUT: Defensive copies; endpoints are Tables with their stable table_key_id.
        """
        return [dict(item) for item in self.data.get("table_reference_assessments", [])]

    def identity_mapping_assessments(self) -> list[dict[str, Any]]:
        """PURPOSE: Expose key-identity mapping decisions between representative Keys.
        INPUT: This graph.
        OUTPUT: Defensive copies with decision, basis and evidence.
        """
        return [dict(item) for item in self.data.get("identity_mapping_assessments", [])]

    def object_relations(self) -> list[dict[str, Any]]:
        """PURPOSE: Deprecated read-only view in the pre-assessment ``object_relations`` shape.
        INPUT: This graph.
        OUTPUT: Records rebuilt from the assessment collections; never serialized.
        """
        from src.common.normalize_relation_assessments import legacy_object_relations
        return legacy_object_relations(self.data)

    def rollups(self, entity_type_id: str | None = None) -> list[dict[str, Any]]:
        """PURPOSE: Return opt-in descendant-to-parent rollup candidates for one ET (or all).
        INPUT: Optional ET/concept ID. Its member Tables (``members``: table_key_ids) are resolved
               first; a rollup matches when its parent Table is one of them. Raises KeyError for an
               unknown ID. ET IDs are never compared with table_key_ids.
        OUTPUT: Matching rollup candidates with evidence, in graph order.
        """
        if entity_type_id is None:
            return [dict(item) for item in self.data.get("rollups", [])]
        if entity_type_id not in self._concepts:
            raise KeyError(entity_type_id)
        from src.common.normalize_relation_assessments import rollup_parent_table_key_id
        member_table_key_ids = set(self._concepts[entity_type_id].get("members", []))
        return [dict(item) for item in self.data.get("rollups", [])
                if rollup_parent_table_key_id(item) in member_table_key_ids]

    def rollups_for_table_key(self, table_key_id: str) -> list[dict[str, Any]]:
        """PURPOSE: Return rollup candidates whose parent is one Table + representative Key record.
        INPUT: table_key_id (``O:<table>``). OUTPUT: Matching rollup candidates with evidence.
        """
        from src.common.normalize_relation_assessments import rollup_parent_table_key_id
        return [dict(item) for item in self.data.get("rollups", [])
                if rollup_parent_table_key_id(item) == table_key_id]

    def attribution_paths(self, event_definition_id: str, to_concept_id: str) -> list[dict[str, Any]]:
        """PURPOSE: Resolve executable event-to-logical-case candidates.
        INPUT: Existing binding and logical concept IDs.
        OUTPUT: Matching validated/ambiguous path records.
        """
        return [dict(item) for item in self._bindings[event_definition_id].get("concept_paths", [])
                if item.get("to") == to_concept_id]

    def object_links(self, event_definition_id: str) -> list[dict[str, Any]]:
        """PURPOSE: Resolve source-PK and declared-FK structural associations for a binding.
        INPUT: Existing Activity Binding ID.
        OUTPUT: Defensive link copies; structural association never implies lifecycle membership.
        """
        if event_definition_id not in self._bindings:
            raise KeyError(event_definition_id)
        return [dict(item) for item in self._activity_object_links.get(event_definition_id, [])]

    def binding_object_association(self, event_definition_id: str,
                                   concept_id: str) -> dict[str, Any] | None:
        """PURPOSE: Resolve executable attribution and lifecycle membership for one pair.
        INPUT: Existing Binding and Object Type IDs.
        OUTPUT: Defensive association copy or None when no candidate association exists.
        """
        if event_definition_id not in self._bindings:
            raise KeyError(event_definition_id)
        if concept_id not in self._concepts:
            raise KeyError(concept_id)
        value = self._binding_object_associations.get((event_definition_id, concept_id))
        return dict(value) if value else None

    def activity_bindings_for_concept(self, concept_id: str) -> list[dict[str, Any]]:
        """PURPOSE: Retrieve broad activity candidates and explain how each reaches one Concept.
        INPUT: Existing Object Type ID.
        OUTPUT: Unique bindings with structural and executable-attribution reason records.
        """
        if concept_id not in self._concepts:
            raise KeyError(concept_id)
        candidates: dict[str, dict[str, Any]] = {}
        for event_definition_id, binding in self._bindings.items():
            structural = [dict(link) for link in self._activity_object_links.get(event_definition_id, [])
                          if concept_id in link.get("target_object_concept_ids", [])]
            executable = [dict(path) for path in binding.get("concept_paths", [])
                          if path.get("to") == concept_id]
            if structural or executable:
                candidates[event_definition_id] = {"binding": dict(binding),
                                          "structural_links": structural,
                                          "attribution_paths": executable,
                                          "lifecycle_association": (
                                              dict(self._binding_object_associations[
                                                  (event_definition_id, concept_id)])
                                              if (event_definition_id, concept_id) in
                                              self._binding_object_associations else None)}
        return [candidates[key] for key in sorted(candidates)]

    def case_map(self, path_id: str) -> dict[str, Any]:
        """PURPOSE: Resolve one validated source-event-to-case mapping contract.
        INPUT: Existing attribution path ID.
        OUTPUT: Case-map record; unknown IDs raise KeyError.
        """
        return dict(self._attribution_paths[path_id]["case_map"])

    def timestamp(self, ts_id: str) -> dict[str, Any]:
        """PURPOSE: Resolve timestamp normalization metadata.
        INPUT: Existing timestamp ID.
        OUTPUT: TimestampUnit mapping; raises KeyError for unknown IDs.
        """
        return dict(self._timestamps[ts_id])

    def to_dict(self) -> dict[str, Any]:
        """PURPOSE: Return serializable graph content.
        INPUT: This graph.
        OUTPUT: Shallow graph mapping copy.
        """
        return dict(self.data)
