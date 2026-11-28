"""Read-only semantic, physical and validation projections of one canonical Evidence Graph."""

from __future__ import annotations
import hashlib
import json
from typing import Any
PROJECTION_VERSION = "eg-projection-v1"
PROMPT_EVIDENCE_VIEWS = ("full", "semantic", "semantic_targeted")


def graph_projection_fingerprint(graph: dict[str, Any], view: str) -> str:
    """PURPOSE: Identify a projection policy without cloning or mutating the canonical graph.
    INPUT: Canonical Evidence Graph and requested view name.
    OUTPUT: Stable SHA-256 fingerprint tied to graph identity and projection version.
    """
    if view not in PROMPT_EVIDENCE_VIEWS:
        raise ValueError(f"prompt_evidence_view must be one of {PROMPT_EVIDENCE_VIEWS}")
    payload = [graph.get("database_fingerprint"), graph.get("schema_graph_version"),
               PROJECTION_VERSION, view]
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def get_physical_bindings(graph: dict[str, Any], event_definition_ids: list[str], *,
                          expected_fingerprint: str | None = None) -> list[dict[str, Any]]:
    """PURPOSE: Hydrate selected IDs from the canonical graph for deterministic ES generation.
    INPUT: Canonical graph and selected stable Binding IDs.
    OUTPUT: Deep-copied bindings in requested order; unknown IDs raise.
    """
    actual = graph_projection_fingerprint(graph, "full")
    if expected_fingerprint is not None and expected_fingerprint != actual:
        raise ValueError("Stale or mismatched Evidence Graph projection fingerprint")
    by_id = {item["id"]: item for item in graph.get('event_definitions', [])}
    missing = [event_definition_id for event_definition_id in event_definition_ids if event_definition_id not in by_id]
    if missing:
        raise KeyError("Unknown Binding IDs: " + ", ".join(missing))
    return [json.loads(json.dumps(by_id[event_definition_id])) for event_definition_id in event_definition_ids]
