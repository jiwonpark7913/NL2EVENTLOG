"""Shared entity naming metadata for graph assembly and entity identification."""
from __future__ import annotations
from typing import Any


NAMING_VERSION = "object-naming-v1"


def naming_metadata(name: str, candidates: list[dict[str, Any]],
                    evidence: list[dict[str, Any]], *, unresolved: bool = False) -> dict[str, Any]:
    """PURPOSE: Attach auditable display naming without changing Object identity or membership.
    INPUT: Chosen noun phrase, enumerated candidates, existing evidence and uncertainty flag.
    OUTPUT: Stable naming metadata; scores are transparent heuristics, not probabilities.
    """
    unique = {}
    for candidate in candidates:
        value = str(candidate.get("name", "")).strip()
        if value:
            unique.setdefault(value.casefold(), {**candidate, "name": value})
    if name.casefold() not in unique:
        unique[name.casefold()] = {"name": name, "score": 0,
                                   "basis": "neutral_stable_fallback"}
    return {
        "canonical_name": name,
        "display_name": name,
        "naming_status": "unresolved" if unresolved else "resolved_deterministic",
        "name_source": ("neutral_stable_fallback" if unresolved else
                        "deterministic_member_and_dictionary_evidence"),
        "candidate_names": sorted(unique.values(), key=lambda item: (
            -float(item.get("score", 0)), item["name"].casefold())),
        "naming_evidence": list(evidence),
        "naming_warnings": (["No single noun phrase covered all validated members."]
                            if unresolved else []),
        "naming_version": NAMING_VERSION,
    }
