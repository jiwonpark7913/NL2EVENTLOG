"""Stable identifiers and canonical output helpers."""

from __future__ import annotations
from urllib.parse import quote
import hashlib
import json
EVENT_DEFINITION_PREFIX = "E:"
LEGACY_EVENT_DEFINITION_PREFIX = "B:"


def encoded(value: object) -> str:
    """PURPOSE: Encode arbitrary activity values inside stable binding IDs.
    INPUT: Scalar database value.
    OUTPUT: Percent-encoded UTF-8 string.
    """
    return quote(str(value), safe="-._~")


def table_key_id(table: str) -> str:
    """PURPOSE: Stable ID of one Table + representative Key record.
    INPUT: Physical table name.
    OUTPUT: ``O:<table>`` (prefix kept for ID stability).
    """
    return f"O:{table}"


def timestamp_id(table: str, columns: list[str], json_path: str | None = None) -> str:
    """PURPOSE: Identify a column, composite, or JSON timestamp unit.
    INPUT: Table, ordered source columns, optional JSON path.
    OUTPUT: TS-prefixed stable ID.
    """
    source = "+".join(columns)
    if json_path:
        source += json_path
    return f"TS:{table}.{source}"


def event_definition_id(table: str, alpha: dict, ts_id: str) -> str:
    """PURPOSE: Identify one executable Event Definition independently of occurrences.
    INPUT: Source table, activity-source mapping and timestamp ID.
    OUTPUT: Deterministic E-prefixed canonical ID.
    """
    kind = alpha["kind"]
    if kind == "value":
        middle = f"value:{alpha['column']}={encoded(alpha['value'])}"
    elif kind == "column":
        middle = f"column:{ts_id}"
    else:
        middle = "table"
    return f"{EVENT_DEFINITION_PREFIX}{table}:{middle}@{ts_id}"


def normalize_event_definition_id(identifier: str) -> str:
    """PURPOSE: Normalize a legacy B-prefixed Event Definition at an input boundary.
    INPUT: Canonical E: or legacy B: identifier string.
    OUTPUT: Canonical E: identifier; unrelated/malformed identifiers raise ValueError.
    """
    value = str(identifier)
    if value.startswith(EVENT_DEFINITION_PREFIX):
        return value
    if value.startswith(LEGACY_EVENT_DEFINITION_PREFIX):
        return EVENT_DEFINITION_PREFIX + value[len(LEGACY_EVENT_DEFINITION_PREFIX):]
    raise ValueError(f"Not an Event Definition ID: {identifier!r}")


def normalize_event_definition_references(value: object) -> object:
    """PURPOSE: Upgrade known Event Definition references in one legacy JSON artifact.
    INPUT: Nested JSON value whose schema retains legacy binding field names.
    OUTPUT: Deep normalized JSON value; non-Event IDs and field names are unchanged.
    """
    scalar_keys = {'event_definition_id', 'source_event_definition_id', "event_definition_id"}
    list_keys = {'event_definition_ids', 'event_definition_ids', 'legacy_event_definition_ids',
                 "event_ids", "add_event_ids", "remove_event_ids", "binding_pair"}

    def visit(item: object, parent_key: str | None = None) -> object:
        """PURPOSE: Recursively normalize only schema-declared Event reference positions.
        INPUT: Current JSON item and its containing key.
        OUTPUT: Independent normalized lists/dictionaries/scalars.
        """
        if isinstance(item, dict):
            result = {}
            for key, child in item.items():
                normalized_key = (normalize_event_definition_id(key)
                                  if isinstance(key, str) and key.startswith(("B:", "E:"))
                                  else key)
                if normalized_key in result:
                    raise ValueError(
                        f"Event Definition ID collision after normalization: {key!r}"
                    )
                if key == "id" and isinstance(child, str) and child.startswith(("B:", "E:")):
                    result[normalized_key] = normalize_event_definition_id(child)
                elif key in scalar_keys and isinstance(child, str) and child.startswith(("B:", "E:")):
                    result[normalized_key] = normalize_event_definition_id(child)
                else:
                    result[normalized_key] = visit(child, key)
            return result
        if isinstance(item, list):
            if parent_key in list_keys:
                return [normalize_event_definition_id(child)
                        if isinstance(child, str) and child.startswith(("B:", "E:"))
                        else visit(child) for child in item]
            return [visit(child) for child in item]
        return item

    return visit(value)


def relation_id(child: str, columns: list[tuple[str, str]], parent: str) -> str:
    """PURPOSE: Identify a declared composite or scalar FK.
    INPUT: Child table, ordered child-parent column pairs and parent table.
    OUTPUT: R-prefixed stable ID.
    """
    return f"R:{child}.{'+'.join(left for left, _ in columns)}->{parent}"


def path_id(binding: str, concept: str, edge_ids: list[str]) -> str:
    """PURPOSE: Identify an event-to-case attribution path.
    INPUT: Binding ID, target concept ID and ordered relation-edge IDs.
    OUTPUT: AP-prefixed content-derived ID.
    """
    digest = hashlib.sha256(json.dumps([binding, concept, edge_ids]).encode()).hexdigest()[:16]
    return f"AP:{digest}"


def rollup_id(child: str, parent: str, edge_ids: list[str]) -> str:
    """PURPOSE: Identify one executable child-to-parent rollup candidate.
    INPUT: Child/parent Object IDs and ordered relation IDs.
    OUTPUT: RU-prefixed content-derived ID.
    """
    digest = hashlib.sha256(json.dumps([child, parent, edge_ids]).encode()).hexdigest()[:16]
    return f"RU:{digest}"


def content_hash(value: object) -> str:
    """PURPOSE: Hash a JSON-compatible payload independently of key insertion order.
    INPUT: JSON-compatible payload.
    OUTPUT: SHA-256 hexadecimal digest.
    """
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()
