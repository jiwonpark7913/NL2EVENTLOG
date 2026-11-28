"""Data Dictionary normalization and evidence lookup."""

from __future__ import annotations
from typing import Any
import re


def _process_paragraphs(value: Any) -> list[dict[str, str]]:
    """PURPOSE: Normalize heterogeneous business-process descriptions while preserving supplied IDs.
    INPUT: String, list, or nested mapping.
    OUTPUT: Stable process paragraphs with original text only.
    """
    records: list[tuple[str | None, str]] = []
    if isinstance(value, str):
        records = [(None, value)]
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, dict) and item.get("text") is not None:
                records.append((str(item.get("id")) if item.get("id") else None, str(item["text"])))
            else:
                records.append((None, str(item)))
    elif isinstance(value, dict):
        if value.get("text") is not None:
            records.append((str(value.get("id")) if value.get("id") else None, str(value["text"])))
        else:
            for key in sorted(value):
                item = value[key]
                if isinstance(item, list):
                    records.extend((None, str(part)) for part in item)
                elif isinstance(item, dict) and item.get("text") is not None:
                    records.append((str(item.get("id")) if item.get("id") else None, str(item["text"])))
                elif isinstance(item, (str, int, float)):
                    records.append((None, str(item)))
    return [{"id": supplied or f"P:{index}", "text": text}
            for index, (supplied, text) in enumerate(records, 1) if text.strip()]


def _named_records(value: Any, name_field: str) -> list[dict[str, Any]]:
    """PURPOSE: Read list-based or name-keyed public table/column records without losing prose.
    INPUT: Record list or mapping from physical names to record dictionaries, plus name field.
    OUTPUT: Record list with explicit names; supplied dictionaries are never modified.
    """
    if isinstance(value, dict):
        return [{name_field: name, **record} for name, record in value.items()
                if isinstance(record, dict)]
    return value if isinstance(value, list) else []


def _documented_code_meanings(column: dict[str, Any]) -> dict[str, str]:
    """PURPOSE: Expose explicitly written code assignments as citable dictionary entries.
    INPUT: Public column record with code_meanings or semicolon-separated CODE = meaning prose.
    OUTPUT: Verbatim code/meaning pairs; ordinary prose, duplicate codes and partial parses yield no guesses.
    """
    supplied = column.get('code_meanings')
    if supplied:
        return dict(supplied)
    text = str(column.get('definition', column.get('description', ''))).strip()
    meanings = {}
    for part in text.split(';'):
        match = re.fullmatch(r'\s*([A-Za-z0-9_.-]+)\s*=\s*(\S(?:.*\S)?)\s*', part)
        if match is None or match[1] in meanings:
            return {}
        meanings[match[1]] = match[2].rstrip('.')
    return meanings


def normalize_dictionary(raw: dict[str, Any]) -> dict[str, Any]:
    """PURPOSE: Normalize list-based and name-keyed public DDs and bind code domains to columns.
    INPUT: Parsed data_dictionary.json only.
    OUTPUT: Tables, columns, per-column domains, processes, timezone and evidence text indexes.
    """
    from src.common.runtime_input_contract import sanitize_dictionary
    from src.common.timestamp_policy import documented_timezone
    raw, input_audit = sanitize_dictionary(raw)
    tables, columns, relations, semantic_statements = [], [], [], []
    ignored_answer_bearing_metadata = []
    global_domain = raw.get("value_domain", raw.get("code_domain", {}))
    table_records = raw.get("tables")
    if table_records is None:
        table_records = {name: record for name, record in raw.items()
                         if isinstance(record, dict) and isinstance(record.get("columns"), (dict, list))}
    for table in _named_records(table_records, "table"):
        table_name = str(table.get("table", table.get("table_name", table.get("name"))))
        table_id = str(table.get("id") or f"T:{table_name}")
        definition = str(table.get("definition", table.get("description", "")))
        table_record = {"id": table_id, "table": table_name,
                        "definition": definition,
                        "description": str(table.get("description", "")),
                        **({"timezone": zone} if (zone := documented_timezone(table)) else {}),
                        "readable_name": str(table.get("readable_name", "")),
                        "row_grain": str(table.get("row_grain", table.get("row_meaning", "")))}
        for key in ("state_history", "related_occurrence"):
            if isinstance(table.get(key), dict):
                table_record[key] = table[key]
        tables.append(table_record)
        for field in ("definition", "description", "readable_name", "row_grain"):
            text = table_record[field].strip()
            if text:
                semantic_statements.append({"id": f"{table_id}:{field}",
                                            "table": table_name, "field": field,
                                            "text": text})
        for field in ("event_encoding", "encoding_detail", "carrier_column"):
            if table.get(field) not in (None, "", []):
                ignored_answer_bearing_metadata.append({
                    "table": table_name, "field": field,
                    "status": "ignored_by_runtime_discovery"})
        physical_columns = table.get("columns", [c for c in raw.get("columns", []) if c.get("table_name") == table_name])
        for position, column in enumerate(_named_records(physical_columns, "name")):
            name = str(column.get("name", column.get("column_name")))
            column_id = str(column.get("id") or f"C:{table_name}.{name}")
            declaration = str(column.get("declaration", ""))
            constraints = str(column.get("constraints", declaration))
            linked: dict[str, dict[str, str]] = {}
            domain_definitions = []
            code_meanings = _documented_code_meanings(column)
            local_domain = column.get("value_domain", column.get("code_domain", code_meanings))
            if not local_domain and column.get("domain"):
                domain_id = column["domain"]
                domain_names = {domain_id, *[d.get("name") for d in raw.get("domains", []) if d.get("domain_id") == domain_id]}
                local_domain = {str(c["code_value"]): c["code_label"] for c in raw.get("codes", [])
                                if c.get("code_group") in domain_names}
            if isinstance(local_domain, dict):
                for code, meaning in local_domain.items():
                    label = (meaning.get("label", meaning.get("meaning", meaning.get("definition", "")))
                             if isinstance(meaning, dict) else meaning)
                    if not isinstance(label, str) or not label.strip():
                        continue
                    definition_text = str(meaning.get("definition", label)) if isinstance(meaning, dict) else label
                    linked[str(code)] = {"label": label, "definition": definition_text}
                    domain_definitions.append({"code": str(code), "label": label,
                        "definition": definition_text, "origin": "column_domain"})
            constraint_values = set(re.findall(r"['\"]([^'\"]+)['\"]", constraints))
            for code, label in (global_domain.items() if isinstance(global_domain, dict) else []):
                if str(code) in constraint_values:
                    label = (label.get("label", label.get("meaning", label.get("definition", "")))
                             if isinstance(label, dict) else label)
                    if isinstance(label, str) and label.strip():
                        linked.setdefault(str(code), {"label": label, "definition": label})
                        domain_definitions.append({"code": str(code), "label": label,
                            "definition": label, "origin": "global_domain"})
            carrier_tokens = set(re.findall(r"[a-z0-9]+", name.casefold()))
            column_record = {
                "id": column_id, "table": table_name, "column": name,
                "readable_name": str(column.get("readable_name", "")),
                "description": str(column.get("description", "")),
                **({"timezone": zone} if (zone := documented_timezone(column)) else {}),
                "synonyms": list(column.get("synonyms") or []),
                "code_meanings": code_meanings,
                "code_lifecycle": {str(code): phases for code, value in local_domain.items()
                    if isinstance(value, dict) and isinstance(phases := value.get("lifecycle_phases"), list)
                    and all(phase in ("start", "complete") for phase in phases)}
                    if isinstance(local_domain, dict) else {},
                "type": str(column.get("type", column.get("data_type", declaration))),
                "representation_class": str(column.get("representation_class", "")),
                "format": str(column.get("format", "")),
                "definition": str(column.get("definition", column.get("description", ""))),
                "constraints": constraints, "ordinal": position,
                "value_domain": linked,
                "domain_definitions": domain_definitions,
                "event_activity": str(column.get("event_activity", "")),
                **({"reference_role": str(column["reference_role"])} if column.get("reference_role") else {}),
                "source_origin": str(column.get("source_origin", "")),
            }
            columns.append(column_record)
            for code, meaning in linked.items():
                semantic_statements.append({"id": f"{column_id}:value:{code}",
                    "table": table_name, "column": name, "field": "value_domain",
                    "code": code, "text": meaning['definition']})
            for domain in domain_definitions:
                semantic_statements.append({"id": f"{column_id}:domain:{domain['origin']}:{domain['code']}",
                    "table": table_name, "column": name, "field": "value_domain",
                    "code": domain["code"], "text": domain["label"]})
            for field in ("definition", "description", "readable_name"):
                text = column_record[field].strip()
                if text:
                    semantic_statements.append({"id": f"{column_id}:{field}",
                                                "table": table_name, "column": name,
                                                "field": field, "text": text})
            for code, meaning in sorted(column_record["code_meanings"].items()):
                text = str(meaning).strip()
                if text:
                    semantic_statements.append({"id": f"{column_id}:code:{code}",
                                                "table": table_name, "column": name,
                                                "field": "code_meaning", "text": text})
        for index, fk in enumerate(table.get("foreign_keys", []), 1):
            relations.append({
                "id": str(fk.get("id") or f"R:{table_name}:{index}"),
                "child": table_name,
                "child_columns": list(fk.get("columns", [fk.get("column")])) if fk.get("columns") else [fk.get("column")],
                "parent": fk.get("parent_table", fk.get("references_table")),
                "parent_columns": list(fk.get("parent_columns", [fk.get("parent_column")])) if fk.get("parent_columns") else [fk.get("parent_column")],
                "description": str(fk.get("definition", fk.get("role", ""))),
            })
    processes = _process_paragraphs(raw.get("business_process_overview", raw.get("processes", [])))
    semantic_statements.extend(
        {"id": item["id"], "field": "business_process", "text": item["text"]}
        for item in processes)
    for index, rule in enumerate(raw.get("business_rules", []), 1):
        value = rule.get("text", rule.get("definition", "")) if isinstance(rule, dict) else rule
        text = str(value).strip()
        if text:
            semantic_statements.append({"id": f"BR:{index}", "field": "business_rule",
                                        "text": text})
    texts = {item["id"]: item["definition"] for item in tables}
    texts.update({item["id"]: item["definition"] for item in columns})
    texts.update({item["id"]: item["text"] for item in processes})
    return {
        "name": str(raw.get("name", "database")), "timezone": documented_timezone(raw),
        "tables": sorted(tables, key=lambda item: item["id"]),
        "columns": sorted(columns, key=lambda item: item["id"]),
        "relations": sorted(relations, key=lambda item: item["id"]),
        "processes": processes,
        "business_rules": list(raw.get("business_rules", [])),
        "semantic_statements": sorted(semantic_statements, key=lambda item: item["id"]),
        "polymorphic_references": list(raw.get("polymorphic_references", [])),
        "ignored_answer_bearing_metadata": ignored_answer_bearing_metadata,
        "evidence_text": texts,
        "input_contract_audit": input_audit,
    }


def dictionary_indexes(dd: dict[str, Any]) -> dict[str, Any]:
    """PURPOSE: Build table/column lookup maps without changing DD evidence.
    INPUT: Normalized dictionary.
    OUTPUT: Lookup dictionaries used by discovery and repair.
    """
    return {
        "tables": {item["table"]: item for item in dd["tables"]},
        "columns": {(item["table"], item["column"]): item for item in dd["columns"]},
        "evidence_text": dd["evidence_text"],
    }
