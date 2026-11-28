"""Serialized EEG records for table-reference and key-identity assessments.

Two different judgments used to share one ``object_relations`` collection. Their endpoints are
physical Tables and their representative Keys, never Entity Types or Entities:

* ``table_reference_assessments``: a verified child->parent Table reference classified by
threshold-based observations (coverage/multiplicity, interval nesting, DD wording).
* ``identity_mapping_assessments``: whether equal values of two Tables' representative Keys may be
treated as the same Entity (an executable identity mapping), with the decision and its basis.
* ``entity_type_separations``: legacy-path ET classification constraints between two Tables.

``table_key_id`` is the stable ID of the "Table + representative Key" record (``O:<table>``). It is
kept unchanged because ET populations, attribution paths and ES reference it; ``table`` is the
physical table name. This module only renames/restructures records: no decision is re-made, and a
reason that a stored record does not contain is never reconstructed.

Writers emit only the new collections. Readers call :func:`normalize_graph_record` at the
read boundary to accept graphs stored with ``object_relations`` / ``*_object_id`` rollup fields.
Legacy consumers whose payload or logic must stay byte-identical use the ``legacy_*`` views."""

from __future__ import annotations
from copy import deepcopy
from typing import Any
VERSION = "relation-assessments-v1"
DECISIONS = {"MERGE": "mapping_approved", "SEPARATE": "mapping_rejected",
             "UNRESOLVED": "mapping_unresolved"}
LEGACY_DECISIONS = {value: key for key, value in DECISIONS.items()}
CLASSIFICATIONS = (
    ("supertype_member", None, "polymorphic_target"),
    ("candidate_part_of", None, "functional_reference"),
    ("part_of", "structural+temporal", "interval_nested_reference"),
    ("part_of", None, "documented_part_reference"),
    ("reference", None, "reference_only"),
)
LEGACY_KINDS = {classification: kind for kind, _, classification in CLASSIFICATIONS}
TABLE_REFERENCE_RENAMES = {"structural_evidence": "functional_reference_observation",
                           "temporal_evidence": "interval_nesting_observation",
                           "text_evidence": "dictionary_wording"}
WORDING_RENAMES = {"same_object_phrase_found": "same_instance_phrase_found",
                   "independent_object_phrase_found": "independent_record_phrase_found"}
IDENTITY_RENAMES = {"key_mapping": "column_correspondence", "same_object_type": "same_entity_type"}


def _rename(mapping: dict[str, Any], renames: dict[str, str]) -> dict[str, Any]:
    """PURPOSE: Rename present keys only (absent stays absent). INPUT: Record, old->new map. OUTPUT: Copy."""
    return {renames.get(key, key): deepcopy(value) for key, value in mapping.items()}


def _endpoint(table_key_id: Any, table: Any) -> dict[str, Any] | None:
    """PURPOSE: Describe one Table endpoint. INPUT: Stable record ID and table name. OUTPUT: Endpoint or None."""
    if table_key_id is None and table is None:
        return None
    return {"table": table, "table_key_id": table_key_id}


def classification_of(kind: str, decision_reason: Any) -> str:
    """PURPOSE: Map a legacy relation kind to its observation-based classification.
    INPUT: Old kind and decision reason. OUTPUT: Classification; unknown kinds raise.
    """
    for old_kind, reason, classification in CLASSIFICATIONS:
        if kind == old_kind and (reason is None or reason == decision_reason):
            return classification
    raise ValueError(f"unknown table reference relation kind: {kind}")


def observed_exceptions(observation: dict[str, Any] | None,
                        nesting: dict[str, Any] | None) -> dict[str, Any] | None:
    """PURPOSE: Expose exception counts behind threshold ratios without re-measuring.
    INPUT: Recorded coverage/multiplicity and interval-nesting observations.
    OUTPUT: Integer counts computed exactly from recorded numerators/denominators, or None.
    The reference join is an equality join, so linked child keys equal ``matched_child_rows``.
    """
    if not observation or observation.get("status") != "assessed":
        return None
    matched = observation.get("matched_child_rows")
    result = {"basis": "recorded_counts_and_ratios",
              "child_rows_without_resolved_parent": (
                  observation["child_rows"] - matched
                  if isinstance(observation.get("child_rows"), int) and isinstance(matched, int) else None),
              "child_keys_with_multiple_parents": (
                  round(observation["multi_parent_ratio"] * matched)
                  if isinstance(matched, int) and observation.get("multi_parent_ratio") is not None else None)}
    if nesting and nesting.get("status") in {"passed", "failed"}:
        linked = nesting.get("linked_complete_intervals")
        ratio = nesting.get("interval_containment_ratio")
        result["linked_intervals_not_nested"] = (
            linked - round(ratio * linked) if isinstance(linked, int) and ratio is not None else None)
    return result


def table_reference_assessment(record: dict[str, Any],
                               references: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """PURPOSE: Serialize one classified Table reference without changing its decision.
    INPUT: Internal relation record and verified references by ID.
    OUTPUT: Assessment whose endpoints name Tables and their stable table_key_id.
    """
    reference = references.get(record.get("reference_id"), {})
    result = {key: value for key, value in _rename(record, TABLE_REFERENCE_RENAMES).items()
              if key not in {"kind", "left", "right"}}
    result["classification"] = classification_of(record["kind"], record.get("decision_reason"))
    if "dictionary_wording" in result and isinstance(result["dictionary_wording"], dict):
        result["dictionary_wording"] = _rename(result["dictionary_wording"], WORDING_RENAMES)
    if record["kind"] == "supertype_member":
        member = next((item for item in reference.get("members", [])
                       if item.get("object_id") == record.get("left")), {})
        result["polymorphic_target"] = _endpoint(record.get("left"), member.get("table"))
        result["child"] = _endpoint(reference.get("child"), reference.get("child_table"))
        result["parent"] = None
        result["reference_columns"] = deepcopy(reference.get("source_columns", []))
    else:
        result["child"] = _endpoint(record.get("left"), reference.get("child_table"))
        result["parent"] = _endpoint(record.get("right"), reference.get("parent_table")
                                     if record.get("right") is not None else None)
        result["reference_columns"] = deepcopy(reference.get("columns", []))
    result["rollup_eligible"] = record["kind"] == "part_of" and record.get("validation_status") == "valid"
    if "functional_reference_observation" in result:
        result["observed_exceptions"] = observed_exceptions(
            result.get("functional_reference_observation"), result.get("interval_nesting_observation"))
    return result


def legacy_table_reference(assessment: dict[str, Any]) -> dict[str, Any]:
    """PURPOSE: Rebuild the old relation record from an assessment (inverse view).
    INPUT: Table reference assessment. OUTPUT: ``object_relations``-shaped record.
    """
    derived = {"classification", "child", "parent", "polymorphic_target", "reference_columns",
               "rollup_eligible", "observed_exceptions"}
    old = {key: deepcopy(value) for key, value in assessment.items() if key not in derived}
    old = _rename(old, {new: key for key, new in TABLE_REFERENCE_RENAMES.items()})
    if isinstance(old.get("text_evidence"), dict):
        old["text_evidence"] = _rename(old["text_evidence"], {new: key for key, new in WORDING_RENAMES.items()})
    old["kind"] = LEGACY_KINDS[assessment["classification"]]
    if assessment["classification"] == "polymorphic_target":
        old["left"] = (assessment.get("polymorphic_target") or {}).get("table_key_id")
        old["right"] = None
    else:
        old["left"] = (assessment.get("child") or {}).get("table_key_id")
        old["right"] = (assessment.get("parent") or {}).get("table_key_id")
    return old


def _key_side(record: dict[str, Any], side: str, objects: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """PURPOSE: Describe one compared representative Key. INPUT: Identity record, side, Objects by ID.
    OUTPUT: Table, stable table_key_id, ordered key columns and key kind when recorded.
    """
    position = 0 if side == "left" else 1
    table_key_id = record.get(side)
    return {"table": record.get(f"{side}_table"), "table_key_id": table_key_id,
            "columns": [pair[position] for pair in record.get("key_mapping", [])],
            "key_kind": objects.get(table_key_id, {}).get("key_kind")}


def identity_bases(record: dict[str, Any]) -> tuple[list[str] | None, list[str] | None, str]:
    """PURPOSE: Name which recorded conditions produced SEPARATE/UNRESOLVED, without re-deciding.
    INPUT: Identity record written by the current builder in the same run.
    OUTPUT: (rejection_basis, unresolved_basis, basis_source). Bases are read from fields stored in
    the record; when they do not reproduce the recorded decision the bases are withheld (None).
    The identity builder accepts no provided mapping, so a correspondence must be judged YES.
    """
    semantic = record.get("semantic_judgment") or {}
    same_type = semantic.get("same_entity_type", semantic.get("same_object_type"))
    statistics = record.get("statistics") or {}
    validator = record.get("validator") or {}
    triggers = set(record.get("candidate_triggers") or [])
    pair_evidence = set(record.get("pair_specific_evidence") or [])
    rejection = [name for name, present in (
        ("semantic_contradiction", semantic.get("semantic_decision") == "CONTRADICT"),
        ("entity_type_mismatch", same_type == "NO"),
        ("correspondence_denied", semantic.get("identity_correspondence") == "NO")) if present]
    collisions = (statistics.get("collision_check") or {}).get("conflicts")
    equality = statistics.get("equality_mapping_verified")
    authoritative = bool({"dd_explicit_same_instance"} & triggers or
                         {"cited_semantic_review", "validated_global_review"} & pair_evidence or
                         semantic.get("correspondence_evidence_validated") is True)
    shared_pk = "declared_shared_pk_fk" in triggers
    unresolved = [name for name, present in (
        ("entity_type_unconfirmed", same_type != "YES"),
        ("correspondence_unconfirmed", semantic.get("identity_correspondence") != "YES"),
        ("key_type_incompatible", validator.get("type_compatible") is False),
        ("key_values_not_unique_or_null", statistics.get("left_key_valid") is False or
         statistics.get("right_key_valid") is False),
        ("identifier_collision", bool(collisions)),
        ("granularity_unresolved", validator.get("granularity_compatible") != "supported"),
        ("no_shared_key_values", equality is False and statistics.get("intersection_count") == 0),
        ("key_domains_not_nested", equality is False and (statistics.get("intersection_count") or 0) > 0),
        ("no_authoritative_correspondence_evidence", equality is True and not (authoritative or shared_pk)),
    ) if present]
    decision = record.get("final_decision")
    consistent = ((decision == "SEPARATE" and rejection) or
                  (decision == "UNRESOLVED" and not rejection and unresolved) or
                  (decision == "MERGE" and not rejection and not unresolved))
    if not consistent:
        return None, None, "not_reproducible_from_recorded_fields"
    return ((rejection if decision == "SEPARATE" else []),
            (unresolved if decision == "UNRESOLVED" else []), "recorded_judgment_and_statistics")


def identity_mapping_assessment(record: dict[str, Any], objects: dict[str, dict[str, Any]],
                                entity_type_ids: dict[str, list[str]], *,
                                derive_bases: bool) -> dict[str, Any]:
    """PURPOSE: Serialize one key-identity mapping judgment with unchanged decision and evidence.
    INPUT: Identity record, Objects by ID, recorded ET scope by record ID and basis switch.
    OUTPUT: Assessment. ``mapping_rejected`` withholds the mapping; it does not assert disjoint Entity sets.
    """
    result = {key: value for key, value in _rename(record, IDENTITY_RENAMES).items()
              if key not in {"kind", "left", "right", "left_table", "right_table", "final_decision"}}
    result["decision"] = DECISIONS[record["final_decision"]]
    result["left_key"] = _key_side(record, "left", objects)
    result["right_key"] = _key_side(record, "right", objects)
    result["entity_type_ids"] = sorted(entity_type_ids.get(record["id"], []))
    if derive_bases:
        rejection, unresolved, source = identity_bases(record)
    else:
        rejection, unresolved, source = None, None, "not_recorded_in_stored_format"
    result.update(rejection_basis=rejection, unresolved_basis=unresolved, basis_source=source)
    return result


def legacy_identity_relation(assessment: dict[str, Any]) -> dict[str, Any]:
    """PURPOSE: Rebuild the old identity relation record (inverse view). INPUT: Assessment. OUTPUT: Old record."""
    derived = {"decision", "left_key", "right_key", "entity_type_ids", "rejection_basis",
               "unresolved_basis", "basis_source"}
    old = _rename({k: v for k, v in assessment.items() if k not in derived},
                  {new: key for key, new in IDENTITY_RENAMES.items()})
    old.update(kind="identity", final_decision=LEGACY_DECISIONS[assessment["decision"]],
               left=assessment["left_key"]["table_key_id"], right=assessment["right_key"]["table_key_id"],
               left_table=assessment["left_key"]["table"], right_table=assessment["right_key"]["table"])
    return old


def entity_type_separation(record: dict[str, Any], objects: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """PURPOSE: Serialize a legacy-path ET classification constraint between two Tables.
    INPUT: ``type_separation`` record and Objects by ID. OUTPUT: Constraint record (not an identity decision).
    """
    result = {key: value for key, value in _rename(record, IDENTITY_RENAMES).items()
              if key not in {"kind", "left", "right"}}
    for side in ("left", "right"):
        result[side] = _endpoint(record.get(side), objects.get(record.get(side), {}).get("table"))
    return result


def legacy_entity_type_separation(constraint: dict[str, Any]) -> dict[str, Any]:
    """PURPOSE: Rebuild the old ``type_separation`` record. INPUT: Constraint. OUTPUT: Old record."""
    old = _rename({k: v for k, v in constraint.items() if k not in {"left", "right"}},
                  {new: key for key, new in IDENTITY_RENAMES.items()})
    old.update(kind="type_separation", left=(constraint.get("left") or {}).get("table_key_id"),
               right=(constraint.get("right") or {}).get("table_key_id"))
    return old


def split_relations(records: list[dict[str, Any]], objects: list[dict[str, Any]],
                    references: list[dict[str, Any]],
                    identity_decisions: list[dict[str, Any]] | None = None, *,
                    derive_bases: bool = True) -> dict[str, list[dict[str, Any]]]:
    """PURPOSE: Write the three serialized collections from internal relation records.
    INPUT: Internal relation records, Objects, references and recorded ET identity decisions.
    OUTPUT: table_reference_assessments, identity_mapping_assessments, entity_type_separations (ID-sorted).
    """
    objects_by_id = {item["id"]: item for item in objects}
    references_by_id = {item["id"]: item for item in references}
    scope: dict[str, set[str]] = {}
    for decision in identity_decisions or []:
        identifier = decision.get("identity_relation_id", decision.get("identity_mapping_assessment_id"))
        if identifier and decision.get("entity_type_id"):
            scope.setdefault(identifier, set()).add(decision["entity_type_id"])
    result = {"table_reference_assessments": [], "identity_mapping_assessments": [],
              "entity_type_separations": []}
    for record in sorted(records, key=lambda item: item["id"]):
        if record.get("kind") == "identity":
            result["identity_mapping_assessments"].append(identity_mapping_assessment(
                record, objects_by_id, {k: sorted(v) for k, v in scope.items()}, derive_bases=derive_bases))
        elif record.get("kind") == "type_separation":
            result["entity_type_separations"].append(entity_type_separation(record, objects_by_id))
        else:
            result["table_reference_assessments"].append(
                table_reference_assessment(record, references_by_id))
    return result


def legacy_object_relations(graph: dict[str, Any]) -> list[dict[str, Any]]:
    """PURPOSE: Old single-collection view for legacy readers and rename-only verification.
    INPUT: Graph mapping with the new collections. OUTPUT: ID-sorted ``object_relations`` records.
    """
    records = [legacy_table_reference(item) for item in graph.get("table_reference_assessments", [])]
    records += [legacy_identity_relation(item) for item in graph.get("identity_mapping_assessments", [])]
    records += [legacy_entity_type_separation(item) for item in graph.get("entity_type_separations", [])]
    return sorted(records, key=lambda item: item["id"])


def rollup_record(identifier: str, relation: dict[str, Any], reference: dict[str, Any]) -> dict[str, Any]:
    """PURPOSE: Write one rollup candidate with Table names and stable table_key_id endpoints.
    INPUT: Rollup ID, rollup-eligible relation and its verified reference. OUTPUT: Rollup record.
    """
    return {"id": identifier,
            "child_table": reference["child_table"], "child_table_key_id": relation["left"],
            "parent_table": reference["parent_table"], "parent_table_key_id": relation["right"],
            "reference_assessment_id": relation["id"]}


def rollup_parent_table_key_id(rollup: dict[str, Any]) -> Any:
    """PURPOSE: Read a rollup parent endpoint from either form. INPUT: Rollup. OUTPUT: table_key_id."""
    return rollup.get("parent_table_key_id", rollup.get("parent_object_id"))


def _normalize_rollup(rollup: dict[str, Any], assessments: list[dict[str, Any]]) -> dict[str, Any]:
    """PURPOSE: Read an old stored rollup as the new form; links only to an existing assessment.
    INPUT: Rollup and the graph's table reference assessments. OUTPUT: New-form rollup.
    """
    if "child_object_id" not in rollup and "parent_object_id" not in rollup:
        return rollup
    joins = rollup.get("joins") or [{}]
    edge = (rollup.get("edge_ids") or [None])[0]
    linked = next((item["id"] for item in assessments if item.get("reference_id") == edge
                   and item.get("rollup_eligible")), None)
    first = {"id": rollup.get("id"),
             "child_table": joins[0].get("left_table"), "child_table_key_id": rollup.get("child_object_id"),
             "parent_table": joins[-1].get("right_table"), "parent_table_key_id": rollup.get("parent_object_id"),
             "reference_assessment_id": linked}
    rest = {k: v for k, v in rollup.items() if k not in {"id", "child_object_id", "parent_object_id"}}
    return {**first, **rest}


def normalize_graph_record(graph: dict[str, Any], context: dict[str, Any] | None = None) -> dict[str, Any]:
    """PURPOSE: Read boundary: accept stored native/runtime graphs written before relation assessments.
    INPUT: Graph mapping (native data, report or runtime projection; not modified) and optional native
           graph supplying objects/references/ET identity decisions when the mapping itself lacks them.
    OUTPUT: Copy using the new collections, rollup fields and identity references. Stored records keep
    their decisions; bases absent from the stored format stay None. New-form graphs are returned as is.
    """
    if not isinstance(graph, dict):
        return graph
    needs_relations = "object_relations" in graph
    needs_rollups = any("child_object_id" in item or "parent_object_id" in item
                        for item in graph.get("rollups", []) if isinstance(item, dict))
    needs_decisions = any("identity_relation_id" in item
                          for item in graph.get("entity_identity_decisions", []) if isinstance(item, dict))
    legacy_terms = _has_legacy_entity_terms(graph)
    if not (needs_relations or needs_rollups or needs_decisions or legacy_terms):
        return graph
    result = {key: value for key, value in graph.items() if key != "object_relations"}
    source = context or graph
    if needs_relations:
        # Without objects/references the endpoint table names and key kinds stay None (never guessed).
        result.update(split_relations(graph.get("object_relations", []), source.get("objects", []),
                                      source.get("references", []), source.get("entity_identity_decisions", []),
                                      derive_bases=False))
        result["relation_assessment_format"] = {"version": VERSION, "read_from": "object_relations"}
    if needs_rollups:
        result["rollups"] = [_normalize_rollup(item, result.get("table_reference_assessments", []))
                             for item in graph.get("rollups", [])]
    if needs_decisions:
        result["entity_identity_decisions"] = rename_identity_references(graph["entity_identity_decisions"])
    if legacy_terms or needs_relations:
        result = _normalize_entity_terms(result)
    return result


ET_COLLECTIONS = ("entity_types", "concepts", 'entity_types', 'entity_types')


def _legacy_et(record: Any) -> bool:
    """PURPOSE: Detect one stored ET record using pre-Entity terms. INPUT: Record. OUTPUT: bool."""
    if not isinstance(record, dict) or record.get("kind") not in {"entity_type", None}:
        return False
    population = record.get("population") or {}
    return ("business_object" in (record.get("roles") or []) and record.get("kind") == "entity_type" or
            any("identity_relation_id" in item for item in record.get("identity_decisions") or []) or
            any("identity_relation_id" in item for item in population.get("unresolved_identity_pairs") or []))


def _has_legacy_entity_terms(graph: dict[str, Any]) -> bool:
    """PURPOSE: Detect stored ET roles/population references/identity judgments in old terms.
    INPUT: Graph mapping. OUTPUT: True when :func:`_normalize_entity_terms` would change it.
    """
    return (any(_legacy_et(item) for key in ET_COLLECTIONS for item in graph.get(key) or []) or
            any("identity_relation_id" in pair for item in graph.get("entity_case_populations") or []
                if isinstance(item, dict) for pair in item.get("unresolved_identity_pairs") or []) or
            any("same_object_type" in item or "same_object_type" in (item.get("semantic_judgment") or {})
                for item in graph.get("identity_mapping_assessments") or [] if isinstance(item, dict)))


def _normalize_population(population: Any) -> Any:
    """PURPOSE: Point stored unresolved pairs at identity mapping assessments.
    INPUT: Population mapping, or a value that needs no migration.
    OUTPUT: Population with renamed identity references; input is not mutated."""
    if not isinstance(population, dict) or "unresolved_identity_pairs" not in population:
        return population
    return {**population, "unresolved_identity_pairs":
            rename_identity_references(population["unresolved_identity_pairs"])}


def _normalize_entity_terms(graph: dict[str, Any]) -> dict[str, Any]:
    """PURPOSE: Read stored ET roles, population references and identity judgments in current terms.
    INPUT: Graph copy. OUTPUT: Copy with ``business_entity`` ET role, ``identity_mapping_assessment_id``
    references and ``same_entity_type`` judgments. Values (decisions, IDs, statuses) are unchanged.
    """
    result = dict(graph)
    for key in ET_COLLECTIONS:
        if not isinstance(result.get(key), list):
            continue
        records = []
        for item in result[key]:
            if isinstance(item, dict) and item.get("kind") in {"entity_type", None}:
                item = dict(item)
                if item.get("kind") == "entity_type" and isinstance(item.get("roles"), list):
                    item["roles"] = ["business_entity" if role == "business_object" else role
                                     for role in item["roles"]]
                if isinstance(item.get("identity_decisions"), list):
                    item["identity_decisions"] = rename_identity_references(item["identity_decisions"])
                if "population" in item:
                    item["population"] = _normalize_population(item["population"])
            records.append(item)
        result[key] = records
    if isinstance(result.get("entity_case_populations"), list):
        result["entity_case_populations"] = [_normalize_population(item)
                                             for item in result["entity_case_populations"]]
    if isinstance(result.get("identity_mapping_assessments"), list):
        assessments = []
        for item in result["identity_mapping_assessments"]:
            item = _rename(item, {"same_object_type": "same_entity_type"})
            if isinstance(item.get("semantic_judgment"), dict):
                item["semantic_judgment"] = _rename(item["semantic_judgment"],
                                                    {"same_object_type": "same_entity_type"})
            assessments.append(item)
        result["identity_mapping_assessments"] = assessments
    return result


def rename_identity_references(decisions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """PURPOSE: Point ET identity decisions at identity_mapping_assessments.
    INPUT: Decisions with ``identity_relation_id``. OUTPUT: Copies with ``identity_mapping_assessment_id``.
    """
    return [_rename(item, {"identity_relation_id": "identity_mapping_assessment_id"}) for item in decisions]
