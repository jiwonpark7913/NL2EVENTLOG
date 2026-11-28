"""Assemble native and compatibility Evidence Graph views."""

from __future__ import annotations
from typing import Any
from src.common.graph_identifiers import table_key_id
from src.eeg.evidence_graph_models import EvidenceGraph, Table, representative_key
from src.step1_understand.validate_table_relationships import attach_paths
from src.step1_understand.entity_naming_metadata import naming_metadata


def build_table_key_records(tables: list[Table], dd: dict[str, Any], key_profiles=None) -> list[dict[str, Any]]:
    """PURPOSE: Retain keyed source representations using PK or validated declared UNIQUE evidence.
    INPUT: Physical schema, normalized DD and optional exact declared-key profiles.
    OUTPUT: ID-sorted Object records.
    """
    definitions = {item["table"]:item for item in dd["tables"]}
    result = []
    for table in tables:
        selected = representative_key(table, key_profiles)
        if selected is None:
            continue
        key, key_kind = selected
        documented = definitions.get(table.name, {})
        evidence = [{"kind":"rule","id":"R0.keyed_object","outcome":"accepted",
                     "key_kind": key_kind}]
        if documented:
            evidence.insert(0,{"kind":"dd","ref":documented["id"],"quote":documented.get("definition","")})
        display_name = table.name.replace("_", " ").title()
        naming = naming_metadata(display_name, [
            {"name": display_name, "score": 3, "basis": "physical_table_name"}],
            evidence)
        result.append({"id":table_key_id(table.name),"table":table.name,"pk":key,
                       "key_kind":key_kind,"evidence":evidence,
                       **naming, "name": display_name})
    return sorted(result,key=lambda item:item["id"])


def assemble_graph(dataset: str, config_hash: str, tables: list[Table], dd: dict[str, Any],
                   timestamps: list[dict[str, Any]], classifications: dict[str, dict[str, Any]],
                   bindings: list[dict[str, Any]], relations: list[dict[str, Any]], max_hops: int,
                   *, extension: dict[str, Any] | None = None, key_profiles=None) -> EvidenceGraph:
    """PURPOSE: Join observations, bindings, relations and paths into deterministic G=(O,B,R,evidence).
    INPUT: Completed stage outputs and immutable configuration identity.
    OUTPUT: Native EvidenceGraph with query-time lookup inventories.
    """
    objects = build_table_key_records(tables,dd,key_profiles)
    attach_paths(bindings,relations,objects,max_hops)
    candidates=[]
    for binding in bindings:
        descriptions=[item.get("quote","") for item in binding.get("evidence",[]) if item.get("kind")=="dd"]
        candidates.append({'event_definition_id':binding["id"],"name":binding["alpha"]["name"],
                           "description":" ".join(dict.fromkeys(item for item in descriptions if item))})
    binding_by_timestamp: dict[str, list[dict[str, str]]] = {
        item["ts_id"]: [] for item in timestamps}
    for binding in sorted(bindings, key=lambda item: item["id"]):
        if binding.get("ts_id") in binding_by_timestamp:
            binding_by_timestamp[binding["ts_id"]].append({
                "event_id": binding["id"],
                "event_name": str(binding.get("activity_label") or
                                  binding.get("alpha", {}).get("name", "")),
                "interpretation": str(binding.get("encoding_interpretation", "unknown")),
            })
    timestamp_event_links = [{
        "timestamp_id": item["ts_id"], "table": item["table"],
        "event_count": len(binding_by_timestamp[item["ts_id"]]),
        "events": binding_by_timestamp[item["ts_id"]],
        "coverage_status": ("covered" if binding_by_timestamp[item["ts_id"]]
                            else "uncovered"),
    } for item in sorted(timestamps, key=lambda value: value["ts_id"])]
    graph={"version":"dbu-rewrite-1","dataset":dataset,"config_hash":config_hash,
           "objects":objects,"relations":sorted(relations,key=lambda item:item["id"]),
           "timestamps":sorted(timestamps,key=lambda item:item["ts_id"]),
           "tables":sorted(classifications.values(),key=lambda item:item["table"]),
           "bindings":sorted(bindings,key=lambda item:item["id"]),
           "timestamp_event_links":timestamp_event_links,
           "activity_candidates":sorted(candidates,key=lambda item:(item['event_definition_id'],item["name"])),
           "input_contract":{"used":["database.sqlite","data_dictionary.json"],
                             "forbidden":["questions.jsonl","private/","data_dictionary.md","schema.sql"]}}
    if extension is not None:
        graph["version"] = "dbu-rewrite-2"
        graph.update(extension)
    return EvidenceGraph(graph)
