"""Configuration for deterministic DB Understanding."""

from __future__ import annotations
from src.common.attribution_policy import MAX_ATTRIBUTION_HOPS, bounded_hops
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
import hashlib
import json
from src.common.llm_usage import DEFAULT_MODEL

INTEGRATED_POLICY = "integrated"
EVENT_BINDING_VERSION = "v2"


@dataclass(frozen=True)
class DbuConfig:
    """PURPOSE: Hold all thresholds that affect graph construction.
    INPUT: Immutable scalar limits and keyword tuples.
    OUTPUT: A hashable, serializable configuration; no runtime data.
    """
    sample_size: int = 20
    ts_scan_limit: int = 100_000
    ts_parse_ratio_strict: float = 0.95
    ts_parse_ratio_loose: float = 0.5
    json_ratio: float = 0.95
    json_max_depth: int = 3
    max_distinct: int = 50
    activity_semantic_review_budget: int = 50
    review_validation_retries: int = 1
    max_hops: int | None = MAX_ATTRIBUTION_HOPS
    concepts: bool = True
    max_rollup_depth: int = 2
    inferred_inclusion_threshold: float = 0.95
    identity_candidate_overlap_threshold: float = 0.30
    polymorphic_member_share: float = 0.05
    polymorphic_max_members: int = 3
    part_of_child_ref_coverage: float = 0.95
    part_of_multi_parent_ratio: float = 0.01
    part_of_interval_containment: float = 0.95
    part_of_temporal_precedes: float = 0.95
    part_of_tolerance_seconds: int = 3600
    repair: bool = True
    selective_review: bool = True
    model: str = DEFAULT_MODEL
    event_binding_version: str = EVENT_BINDING_VERSION
    carrier_event_policy: str = INTEGRATED_POLICY
    semantic_signatures: bool = True
    global_ot_review: bool = True
    entity_types: bool = True
    pairwise_identity_llm: bool = True
    semantic_signature_batch_size: int = 20
    dd_time_type_keywords: tuple[str, ...] = (
        "date", "datetime", "time", "timestamp", "instant", "yyyy-mm-dd", "yyyymmdd", "epoch")
    dd_time_words: tuple[str, ...] = (
        "time", "date", "timestamp", "when", "moment", "occurred", "recorded", "valid from", "valid to")
    ts_name_tokens: tuple[str, ...] = (
        "at", "on", "ts", "time", "date", "dt", "dttm", "timestamp", "datetime", "stamp", "when",
        "valid", "from", "to", "start", "end", "begin", "finish", "created", "updated", "modified",
        "changed", "recorded", "posted", "udate", "utime")
    activity_keywords: tuple[str, ...] = (
        "activity", "type", "status", "state", "step", "stage", "phase", "action", "event")

    def __post_init__(self) -> None:
        """PURPOSE: Reject unsupported construction contracts, bounds and review budgets early.
        INPUT: Newly constructed immutable configuration.
        OUTPUT: None; raises ValueError for incompatible versions, ratios, budgets or hop bounds.
        """
        object.__setattr__(self, 'max_hops', bounded_hops(self.max_hops))
        if not 0 <= self.identity_candidate_overlap_threshold <= 1:
            raise ValueError("identity candidate overlap must be between zero and one")
        if self.event_binding_version != EVENT_BINDING_VERSION or self.carrier_event_policy != INTEGRATED_POLICY:
            raise ValueError("The runtime supports only integrated v2 EEG construction")
        if not (self.concepts and self.entity_types and self.selective_review):
            raise ValueError("Integrated EEG construction requires Entity Types and selective evidence review")
        if self.activity_semantic_review_budget < 0:
            raise ValueError("activity_semantic_review_budget must be nonnegative")
        if not 0 <= self.review_validation_retries <= 2:
            raise ValueError("review_validation_retries must be between zero and two")
        if self.semantic_signature_batch_size < 1:
            raise ValueError("semantic_signature_batch_size must be positive")
        ratio_fields = (
            "part_of_child_ref_coverage", "part_of_multi_parent_ratio",
            "part_of_interval_containment", "part_of_temporal_precedes")
        if any(not 0 <= getattr(self, field) <= 1 for field in ratio_fields):
            raise ValueError("part_of ratio thresholds must be between zero and one")
        if self.part_of_tolerance_seconds < 0:
            raise ValueError("part_of_tolerance_seconds must be non-negative")

    def digest(self) -> str:
        """PURPOSE: Identify every behavior-affecting setting deterministically.
        INPUT: This configuration.
        OUTPUT: Full SHA-256 hex digest of canonical JSON.
        """
        values = asdict(self)
        values["eeg_contract_version"] = "step1-four-stage-v1"
        values["semantic_policy_version"] = "entity-scoped-event-inventory-v5"
        from src.step1_understand.carrier_event_families import POLICY_VERSION
        values["carrier_event_policy_version"] = POLICY_VERSION
        raw = json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode()).hexdigest()


def load_config(path: Path | None) -> DbuConfig:
    """PURPOSE: Load optional JSON/YAML overrides into the validated configuration.
    INPUT: Optional file path containing a mapping.
    OUTPUT: DbuConfig; raises for unknown keys or invalid formats.
    """
    if path is None:
        return DbuConfig()
    text = Path(path).read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        value: Any = json.loads(text)
    else:
        try:
            import yaml
        except ImportError as error:
            raise RuntimeError("PyYAML is required for YAML DBU configuration") from error
        value = yaml.safe_load(text)
    if not isinstance(value, dict):
        raise ValueError("DBU configuration must be an object")
    known = set(DbuConfig.__dataclass_fields__)
    unknown = sorted(set(value) - known)
    if unknown:
        raise ValueError("Unknown DBU configuration keys: " + ", ".join(unknown))
    for key in ("dd_time_type_keywords", "dd_time_words", "ts_name_tokens", "activity_keywords"):
        if key in value:
            value[key] = tuple(value[key])
    return DbuConfig(**value)
