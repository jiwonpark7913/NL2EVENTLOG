"""Project query-scoped raw event evidence via existing, independently validated physical rules."""

from contextlib import closing

from src.common.activity_identity import activity_identity
from copy import deepcopy
import json
import sqlite3

from src.common.database_io import connect_readonly
from src.common.graph_identifiers import path_id
from src.common.schema_metadata import database_fingerprint, stable_id
from src.step1_understand.entity_representations import validate_entity_attribution
from src.step1_understand.validate_event_attribution_paths import _validate_path
from src.step1_understand.validate_event_review_patches import validate_materialized_time
from src.step1_understand.validate_event_semantics import build_occurrence_identity_rules


def recovered_event_label(record, meaning=""):
    """PURPOSE: Format one query-local event name. INPUT: Raw record and optional explicit meaning. OUTPUT: Activity label."""
    phase = record["raw_clock_phase"]
    if phase:
        suffix = {"start": "started", "complete": "completed"}[phase]
        return f"{meaning or record['value']} {suffix}"
    return meaning or f"{record['value']} {record['raw_clock_action']}"


def _candidate_projection(graph, target, record, decision):
    """PURPOSE: Re-probe a typed raw selector with validated source and role-specific path templates.
    INPUT: Runtime EEG, target ET, preserved metadata and a request-local decision.
    OUTPUT: One binding and fresh Case path records, or None if the proof is incomplete.
    """
    identifier, table = record["candidate_id"], record["table"]
    clock = next((t for t in graph.get("dbu_rewrite", {}).get("timestamps", [])
                  if t["ts_id"] == record["ts_id"]), None)
    if not clock or clock.get("semantic_role") != "business_occurrence" or clock.get("role_status") != "supported":
        return None
    definitions = [*graph.get("event_definitions", []), *graph.get("retired_event_definitions", [])]
    sibling_mode = bool(record.get("raw_clock_action"))
    candidates = {item["id"]: item for item in definitions
                  if item["source_table"] == table and item.get("ts_id") == record["ts_id"]
                  and item.get("extraction_status") == "executable" and item.get("source_row_key")
                  and not item.get("documented_source_conditions")
                  and (item.get("source_kind") == "row_activity" and item.get("activity_column") == record["carrier"]
                       if sibling_mode else item.get("source_kind") == "column_event")}
    templates = {}
    for path in graph.get("attribution_paths", []):
        if (path["event_definition_id"] not in candidates or path["to"] != target["id"]
                or path["validation_status"] != "valid" or path["cardinality"] != "N:1"):
            continue
        signature = json.dumps([path.get(k) for k in (
            "target_table_key_id", "joins", "role_scope", "case_role", "role_validation")], sort_keys=True)
        templates[signature] = path
    if not templates:
        return None
    source = candidates[next(iter(templates.values()))["event_definition_id"]]
    label = recovered_event_label(record, decision.get("asserted_meaning", ""))
    alpha = {"kind": "value", "column": record["carrier"], "value": record["value"], "name": label}
    binding = deepcopy(source)
    for key in ("candidate_tier", "entity_reviews", "semantic_signature", "concept_paths", "paths",
                "conflict_relation_ids", "conflict_group", "entity_event_links", "lifecycle_associations",
                "meaning_card", "object_association_ids", "review_dictionary", "validation_axes",
                "activity_identity", "verified_activity_equivalence_id"):
        binding.pop(key, None)
    basis = {"id": identifier, "kind": "request_carrier_recovery", "record_id": record["candidate_id"],
             "request_quote": decision["request_quote"], "scope": target["id"]}
    binding.update(id=identifier, table=table, alpha=alpha, activity=label, activity_label=label,
                   source_kind="row_activity", activity_column=alpha["column"], raw_values=[alpha["value"]],
                   activity_source={"kind": "value", "table": table, "column": alpha["column"], "value": alpha["value"]},
                   source_key=stable_id("source", [table, alpha["column"], alpha["value"], record["ts_id"]]),
                   row_selection={"kind": "equals", "column": alpha["column"], "value": alpha["value"]},
                   encoding_interpretation="row", provenance="request_carrier_recovery",
                   occurrence_identity_rule_id=stable_id("occurrence_rule", [source["source_row_key"], identifier]),
                   activity_semantics={"status": "supported", "occurrence_status": "supported",
                                       "event_label": label, "code_meaning": decision.get("asserted_meaning") or None,
                                       "method": decision["basis"], "citations": [basis]},
                   timestamp_pairing={"status": "supported", "phase": record["raw_clock_phase"], "selected": record["ts_id"]},
                   documented_source_conditions=([{"kind": "not_null", "column": clock["columns"][0]}]
                                                 if sibling_mode else []),
                   activity_label_source=decision["basis"], evidence=[basis, *record["public_evidence"]])
    binding["activity_identity"] = activity_identity(binding)
    binding["canonical_activity_id"] = binding["activity_identity"]
    keys = {item["id"]: item for item in graph["table_key_records"]}
    paths = []
    try:
        with closing(connect_readonly(graph["database"])) as connection:
            timing, errors = validate_materialized_time(connection, binding, clock)
            if errors or timing.get("status") != "pass":
                return None
            binding.update(validation_status="valid",
                           validation_evidence=[{"kind": "request_source_time_probe", **timing}])
            for original in templates.values():
                target_key = keys[original["target_table_key_id"]]
                joins = original.get("joins", [])
                proof, sql, params = _validate_path(
                    connection, binding, binding["source_row_key"], target_key["anchor_table"], target_key["key_columns"],
                    joins, type_tag=target_key["anchor_table"] if target.get("kind") == "supertype" else None,
                    allow_many=False, role_scope=original.get("role_scope"))
                if not proof["passed"] or proof["matched_source_rows"] != timing["source_rows"]:
                    continue
                path = deepcopy(original)
                pid = path_id(identifier, target["id"], [*path.get("edge_ids", []), target_key["id"]])
                path.update(id=pid, event_definition_id=identifier)
                path["case_map"].update(id="CM:" + pid.split(":", 1)[1], source_event_definition_id=identifier,
                                        map_sql=sql, map_parameters=params, validation=proof)
                path["evidence"] = [{"kind": "case_map_validation", **proof}, {"kind": "path_template", "id": original["id"]}]
                paths.append(path)
        paths = validate_entity_attribution(graph["database"], paths, [target]) if paths else []
    except sqlite3.Error:
        return None
    paths = [p for p in paths if p["validation_status"] == "valid"]
    return (binding, paths) if paths else None


def project_recovered_events(graph, et, decisions):
    """PURPOSE: Reconstruct selected fallback definitions and paths from the trusted EEG, without changing it.
    INPUT: EEG, verified ET ID and decisions referencing the preserved metadata. OUTPUT: Transient graph projection.
    """
    if not decisions or not graph.get("database") or database_fingerprint(graph["database"]) != graph.get("database_fingerprint"):
        return graph
    target = next((e for e in graph.get("entity_types", []) if e["id"] == et
                   and e.get("population", {}).get("status") == "valid"), None)
    if target is None:
        return graph
    records = {r["candidate_id"]: r for r in graph.get("unresolved_event_evidence", {}).get("pairs", [])
               if r["raw_clock_validated"] and r["value_semantics_status"] == "unresolved"}
    existing = {item["id"] for item in graph.get("event_definitions", [])}
    bindings, paths = [], []
    for identifier, decision in decisions.items():
        if (identifier in records and identifier not in existing and decision.get("request_quote")
                and (decision.get("basis") == "explicit_raw_code" and not decision.get("asserted_meaning")
                     or decision.get("basis") == "user_asserted_code_meaning" and bool(decision.get("asserted_meaning"))
                     and decision["asserted_meaning"] in decision.get("meaning_quote", ""))):
            projection = _candidate_projection(graph, target, records[identifier], decision)
            if projection:
                binding, validated = projection
                bindings.append(binding)
                paths.extend(validated)
    if not bindings:
        return graph
    keys = [{'table': item['source_table'], 'pk': item['source_row_key']} for item in bindings]
    identities = build_occurrence_identity_rules(bindings, keys)
    return {**graph, "occurrence_identity_rules": [*graph.get("occurrence_identity_rules", []), *identities],
            "event_definitions": [*graph.get("event_definitions", []), *bindings],
            "attribution_paths": [*graph.get("attribution_paths", []), *paths]}
