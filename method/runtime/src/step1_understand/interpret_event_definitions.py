"""Activity-column discovery and deterministic binding generation."""

from __future__ import annotations
from pathlib import Path
from typing import Any
import re
import sqlite3
from src.step1_understand.eeg_configuration import DbuConfig
from src.step1_understand.carrier_timestamp_binding import carrier_clock_relationship, documented_phase, documented_work_endpoints
from src.step1_understand.interpret_carrier_evidence import identify_carriers, interpret_values, interpret_relationships
from src.common.data_dictionary import dictionary_indexes
from src.common.graph_identifiers import event_definition_id
from src.common.database_io import quote_identifier
from src.eeg.evidence_graph_models import Table
from src.step1_understand.detect_and_normalize_timestamps import name_tokens, occurrence_time_policy
from src.step1_understand.resolve_activity_meanings import code_table_evidence, deterministic_meanings
from src.common.database_io import connect_readonly
from src.step1_understand.discover_state_history import history_definitions, related_definitions
from src.common.event_clock import documented_represented_clock, scoped_event_clock


def _activity_provenance(table: str, alpha: dict[str, Any], unit: dict[str, Any],
                         label_source: str) -> dict[str, Any]:
    """PURPOSE: Separate a binding's physical selector from its human-facing label.
    INPUT: Source table, legacy alpha selector, timestamp unit and label provenance.
    OUTPUT: Backward-compatible structured activity-source and label fields.
    """
    if alpha["kind"] == "value":
        activity_source = {"kind": "value", "table": table,
                           "column": alpha["column"], "value": alpha["value"]}
    else:
        activity_source = {"kind": "column", "table": table,
                           "timestamp_unit_id": unit["ts_id"],
                           "source_columns": list(unit.get("columns", []))}
        if unit.get("json_path"):
            activity_source["json_path"] = unit["json_path"]
    return {"occurrence_time_source": {"columns": list(unit.get("columns", [])),
                                       "json_path": unit.get("json_path")},
            "activity_source": activity_source,
            "activity_label": str(alpha["name"]),
            "activity_label_source": label_source}


def _activity_name_from_timestamp(unit: dict[str, Any],
                                  dd_column: dict[str, Any] | None = None) -> str:
    """PURPOSE: Reuse an explicit dictionary activity phrase, otherwise retain a readable column hypothesis.
    INPUT: Timestamp unit and temporal name tokens.
    OUTPUT: Title-cased residual name, falling back to the physical field.
    """
    documented = str((dd_column or {}).get("event_activity", "")).strip()
    if documented:
        return documented
    definition = str((dd_column or {}).get("definition", ""))
    explicit_label = re.search(r"\bActual ([A-Z][A-Za-z ]{1,60}?) occurrence time\b", definition)
    if explicit_label:
        return explicit_label.group(1).strip()
    after_time=re.search(r'\bactual (?:UTC )?(?:occurrence )?time (?:of|for) ([^.;]+)',definition,re.I)
    if after_time:
        phrase=after_time.group(1).strip()
        if len(phrase.split())<=8:return phrase
    semantic_label=re.search(r'\bactual\s+([A-Za-z][A-Za-z -]{1,65}?)\s+(?:occurrence\s+)?time\b',definition,re.I)
    if semantic_label:
        suffix=definition[semantic_label.end():]
        scoped=re.match(r'\s+in\s+([A-Za-z_][A-Za-z0-9_]*)',suffix,re.I)
        if not scoped or scoped.group(1).casefold()==str((dd_column or {}).get('table','')).casefold():
            phrase=re.sub(r'\bUTC\b','',semantic_label.group(1),flags=re.I).strip()
            if not re.fullmatch(r'(?:event|activity|occurrence|recorded|system)',phrase,re.I):return phrase.title()
    phase = re.match(r"^actual (start|close|end|completion) of (?:the )?([^.;]+)", definition, re.I)
    created = re.match(r"^time (?:when )?the ([\w -]+) was (created|received)\.?$", definition, re.I)
    if phase:
        verb = {"start":"started","close":"closed","end":"ended","completion":"completed"}[phase[1].casefold()]
        return f"{phase[2].capitalize()} {verb}"
    if created:
        return f"{created[1].capitalize()} {created[2].lower()}"
    if unit.get("json_path"):
        source = unit["json_path"].rsplit(".", 1)[-1]
    else:
        source = unit["columns"][0]
    generic_time_tokens = {"at", "on", "ts", "time", "date", "dt", "dttm",
                           "timestamp", "datetime", "stamp", "when", "udate", "utime"}
    tokens = [token for token in name_tokens(source) if token not in generic_time_tokens]
    return " ".join(tokens or name_tokens(source)).title()


def _binding_evidence(dd_column: dict[str, Any], rule: str, extras: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """PURPOSE: Attach source definition and applied rule to one binding.
    INPUT: DD column, rule ID and optional value-domain evidence.
    OUTPUT: Ordered evidence records.
    """
    result = []
    if dd_column.get("id"):
        result.append({"kind": "dd", "ref": dd_column["id"], "quote": dd_column.get("definition", "")})
    result.append({"kind": "rule", "id": rule, "outcome": "accepted"})
    return result + list(extras or [])


def _null_meaning(table_name: str, unit: dict[str, Any], indexes: dict[str, Any]) -> str:
    """PURPOSE: Classify documented timestamp NULL semantics without guessing from NULL frequency.
    INPUT: Table, one TimestampUnit and normalized Data Dictionary indexes.
    OUTPUT: not_occurred, not_recorded or unknown.
    """
    text = " ".join(str(indexes["columns"].get((table_name, column), {}).get(
        "definition", "")) for column in unit.get("columns", [])).casefold()
    if re.search(r"\b(not yet|has not occurred|not occurred|pending until|absent until)\b", text):
        return "not_occurred"
    if re.search(r"\b(not recorded|missing record|unknown time|unavailable time)\b", text):
        return "not_recorded"
    return "unknown"


def _timestamp_null_predicate(unit: dict[str, Any]) -> str:
    """PURPOSE: Compile the physical condition under which one TimestampUnit has no usable time.
    INPUT: Column, composite or JSON TimestampUnit.
    OUTPUT: SQLite predicate using only enumerated physical identifiers and a fixed JSON path.
    """
    if unit.get("source") == "json_path":
        path = str(unit.get("json_path", "$")).replace("'", "''")
        return f"json_extract({quote_identifier(unit['columns'][0])}, '{path}') IS NULL"
    return " OR ".join(f"{quote_identifier(column)} IS NULL"
                       for column in unit.get("columns", [])) or "1=1"


def _null_evidence(connection: sqlite3.Connection, table_name: str, unit: dict[str, Any],
                   indexes: dict[str, Any], *, carrier_column: str | None = None,
                   carrier_value: Any = None) -> dict[str, Any]:
    """PURPOSE: Measure excluded untimed rows for one concrete binding.
    INPUT: Read-only DB, source table/unit and optional row carrier predicate.
    OUTPUT: Exact NULL count/ratio, documented meaning and exclusion policy.
    """
    where, parameters = _timestamp_null_predicate(unit), []
    population = "1=1"
    if carrier_column is not None:
        population = f"{quote_identifier(carrier_column)} = ?"
        parameters.append(carrier_value)
        where = f"({population}) AND ({where})"
    qt = quote_identifier(table_name)
    null_count = int(connection.execute(
        f"SELECT COUNT(*) FROM {qt} WHERE {where}", parameters).fetchone()[0])
    population_count = int(connection.execute(
        f"SELECT COUNT(*) FROM {qt} WHERE {population}", parameters).fetchone()[0])
    return {"null_count": null_count,
            "null_ratio": null_count / population_count if population_count else 0.0,
            "null_meaning": _null_meaning(table_name, unit, indexes),
            "null_policy": "exclude_and_report",
            "untimed_excluded_count": null_count}


def measure_value_clocks(connection, table, column, value, units):
    """PURPOSE: Count physical support independently for every timestamp under one typed carrier value.
    INPUT: Read-only SQLite connection, physical identifiers/value, ordered TimestampUnits.
    OUTPUT: One population and non-NULL support receipt per unit; values remain bound parameters.
    """
    source = f"{quote_identifier(table)} WHERE {quote_identifier(column)} = ?"
    population = connection.execute(f"SELECT COUNT(*) FROM {source}", (value,)).fetchone()[0]
    return [{
        'ts_id':unit['ts_id'], 'population_count':population,
        'support_count':population - connection.execute(
            f"SELECT COUNT(*) FROM {source} AND ({_timestamp_null_predicate(unit)})", (value,)
        ).fetchone()[0],
    } for unit in units]



def profile_carrier_family(connection, table, column, units, documentation, lookup):
    """PURPOSE: Collect one carrier's occurrence evidence across every shared clock.
    INPUT: Source table/column, TimestampUnits, normalized code documentation and FK codebook evidence.
    OUTPUT: Typed observed and documented values with exact population and per-clock support counts.
    """
    carrier = quote_identifier(column)
    clock_counts = [
        f"SUM(CASE WHEN {_timestamp_null_predicate(unit)} THEN 0 ELSE 1 END)" for unit in units
    ]
    projection = ", ".join([carrier, "COUNT(*)", *clock_counts])
    rows = connection.execute(
        f"SELECT {projection} FROM {quote_identifier(table.name)} "
        f"WHERE {carrier} IS NOT NULL GROUP BY {carrier} ORDER BY CAST({carrier} AS TEXT)"
    )
    counts = {(type(value), value): (population, *support) for value, population, *support in rows}
    observed = list(counts)
    declared = next(c.declared_type.upper() for c in table.columns if c.name == column)
    documented = {e["evidence"]["lookup_code"] for entries in lookup.values() for e in entries}
    if any(token in declared for token in ("TEXT", "CHAR", "CLOB")) and "INT" not in declared:
        documented.update(documentation.get("value_domain", {}))
        documented.update(documentation.get("code_meanings", {}))
    if "INT" in declared:
        for code in {*documentation.get("value_domain", {}), *documentation.get("code_meanings", {})}:
            if re.fullmatch(r"-?(?:0|[1-9][0-9]*)", code) and -(2**63) <= int(code) < 2**63:
                documented.add(int(code))
    for value in sorted(documented, key=lambda item: (type(item).__name__, str(item))):
        counts.setdefault((type(value), value), (0, *([0] * len(units))))
    return observed, {
        key: [dict(ts_id=unit["ts_id"], population_count=population, support_count=count)
              for unit, count in zip(units, support, strict=True)]
        for key, (population, *support) in counts.items()
    }

def extract_activities(db_path: Path, tables: list[Table], profiles: dict[str, Any], dd: dict[str, Any],
                       timestamps: list[dict[str, Any]], classifications: dict[str, dict[str, Any]],
                       config: DbuConfig, *, llm=None, cache=None, audits=None, source_proved_carriers=None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """PURPOSE: Discover row carriers and create row/column bindings according to §4.5.
    INPUT: DB schema/profiles/DD, timestamps, initial table states and thresholds.
    OUTPUT: Bindings plus C1–C4 activity decision traces.
    """
    indexes = dictionary_indexes(dd)
    ts_by_id = {item["ts_id"]: item for item in timestamps}
    table_by_name = {item.name: item for item in tables}
    bindings, traces = [], {}
    audits = [] if audits is None else audits
    connection = connect_readonly(db_path)
    try:
        for table_name in sorted(classifications):
            state, table = classifications[table_name], table_by_name[table_name]
            evaluations, observed_carrier_values, matrix = [], {}, []
            binding_start = len(bindings)
            if not state["ts_ids"]:
                traces[table_name] = {"activity_evaluations": [],
                                      "selected_activity_columns": []}
                continue
            excluded = set(table.primary_key)
            for ts_id in state["ts_ids"]:
                excluded.update(ts_by_id[ts_id]["columns"])
            local_units = [ts_by_id[ts_id] for ts_id in state["ts_ids"]]
            table_doc = indexes["tables"].get(table_name, {})
            clock_docs = {unit["ts_id"]: indexes["columns"].get((table_name, unit["columns"][0]), {})
                          for unit in local_units}
            work_endpoints = documented_work_endpoints(table_doc.get("definition", ""), (
                (unit, clock_docs[unit["ts_id"]].get("definition", "")) for unit in local_units
            ))
            repeated = any(profiles[table_name]["fk_repeat"].values())
            for column in table.columns:
                if column.name in excluded:
                    continue
                dd_column = indexes["columns"].get((table_name, column.name), {})
                definition = str(dd_column.get("definition", "")).casefold()
                carrier_words = {"event", "activity", "status", "state", "step", "stage",
                                 "phase", "transition", "action", "operation"}
                semantic_carrier = bool(set(name_tokens(
                    f"{column.name} {definition}")).intersection(carrier_words))
                c1_name = bool(set(name_tokens(column.name)).intersection(config.activity_keywords))
                has_domain = bool(dd_column.get("value_domain") or dd_column.get("code_meanings"))
                # A code domain alone (e.g. a loyalty tier) is a category, not activity evidence.
                activity_signal = c1_name or semantic_carrier or any(
                    re.search(r"\b" + re.escape(word) + r"\b", definition)
                    for word in config.activity_keywords)
                carrier_subject = set(name_tokens(column.name)) - {"type", "code", "kind", "category"}
                documented_endpoint = bool(carrier_subject) and any(
                    documented_phase(unit, text) and carrier_subject <= set(name_tokens(text))
                    for unit in local_units
                    if (text := clock_docs[unit["ts_id"]].get("definition")))
                c1 = activity_signal or has_domain
                c2 = "TEXT" in column.declared_type.upper() or has_domain
                has_lookup = any(len(fk.get("columns", [])) == 1 and fk["columns"][0][0] == column.name
                                 and any(c.name != fk["columns"][0][1] and (
                                     set(name_tokens(c.name)) & {"meaning", "label", "description"}
                                     or activity_signal and "name" in name_tokens(c.name))
                                     for c in table_by_name[fk["parent_table"]].columns)
                                 for fk in table.foreign_keys if fk["parent_table"] in table_by_name)
                distinct = profiles[table_name]["columns"][column.name]["distinct_count"]
                c3 = 1 <= distinct <= config.max_distinct
                negative = bool(re.search(
                    r"\b(actor|resource|operator|owner|category|classification|technical flag|static attribute|ingestion|current tier|test type|test kind)\b",
                    f"{column.name} {definition}"))
                # Names and domain size prioritize review; occurrence semantics authorize a carrier.
                semantic_evidence = bool(re.search(
                    r"\b(activity|event|transition|action|operation)\b", definition))
                table_definition = str(indexes["tables"].get(table_name, {}).get("definition", ""))
                explicitly_non_event = bool(re.search(
                    r"\bnot (?:an? )?(?:activity|event|occurrence)\b|\bstatic attribute\b", definition))
                semantic_evidence = semantic_evidence and not explicitly_non_event
                semantic_evidence = semantic_evidence or bool(semantic_carrier and re.search(
                    r"\b(event|activity|transition|operation)\b.*\b(history|record|log|storage)\b|"
                    r"\b(history|log)\b.*\b(event|activity|transition)\b", table_definition, re.I))
                plausible = bool(c1 or semantic_carrier or has_domain or has_lookup or documented_endpoint or
                                 ((c2 or has_lookup) and distinct >= 1 and repeated and not negative))
                # A declared FK/UNIQUE member identifies a business object. It is an activity carrier only with
                # activity-code evidence (documented code domain or a verified lookup-label table), never because
                # its prose mentions an event or because a textual reference repeats.
                identifier_role = (column.name in {pair[0] for fk in table.foreign_keys for pair in fk.get("columns", [])}
                                   or any(column.name in key for key in table.unique_keys))
                identifier_without_code = identifier_role and not (has_domain or has_lookup)
                if identifier_without_code:
                    c1 = semantic_carrier = semantic_evidence = plausible = False
                metadata_lookup = has_lookup and not (activity_signal or has_domain)
                rejection_reasons = (["identifier_key_without_activity_code_evidence"]
                                     if identifier_without_code else [])
                if metadata_lookup:
                    rejection_reasons.append('lookup_identifies_an_attribute_without_activity_evidence')
                if explicitly_non_event:
                    rejection_reasons.append("documented_not_activity")
                if not c1:
                    rejection_reasons.append("no_activity_semantic_evidence")
                if not c2:
                    rejection_reasons.append("carrier_type_review_signal")
                if not c3:
                    rejection_reasons.append("cardinality_review_signal")
                if negative:
                    rejection_reasons.append("negative_resource_or_technical_semantics")
                evaluations.append({"column_id": column.id, "column": column.name,
                                    "C1": c1, "C1_name": c1_name, "C2": c2, "C3": c3,
                                    "C4": repeated, "negative_semantics": negative,
                                    "semantic_carrier": semantic_carrier,
                                    "evidence_status": ("supported" if semantic_evidence and not negative
                                                        else "unresolved" if plausible else "rejected"),
                                    "acceptance_reasons": (["carrier_semantics", "categorical_domain",
                                                            "timestamp_cooccurrence"]
                                                           if c1 and c2 and c3 and not negative else []),
                                    "rejection_reasons": rejection_reasons,
                                    "distinct_count": distinct,
                                    "plausible_carrier": plausible,
                                    "documented_value_domain": has_domain,
                                    "lookup_evidence": has_lookup,
                                    "identifier_role": identifier_role,
                                    "review_reasons": (["cardinality_boundary"] if plausible and not c3 else []) +
                                                      (["semantic_evidence_missing"] if plausible and not c1 else []) +
                                                      (["negative_semantic_conflict"] if plausible and negative else []),
                                    "accepted": ((distinct >= 1 or has_domain or has_lookup) and plausible and not explicitly_non_event
                                                 and not metadata_lookup and (not negative or semantic_evidence)
                                                 and (semantic_evidence or activity_signal and (has_domain or has_lookup)
                                                      or has_domain and (semantic_carrier or documented_endpoint))),
                                    "ordinal": column.ordinal})
            independently_proved = (source_proved_carriers or {}).get(table_name, ())
            for item in evaluations:
                if item["column"] in independently_proved and "documented_not_activity" not in item["rejection_reasons"]:
                    item.update(accepted=True, evidence_status="supported", admission="independent_source_audit")
            identify_carriers(table, evaluations, profiles[table_name]["columns"], indexes["columns"],
                              table_doc, [doc["definition"] for doc in clock_docs.values() if doc.get("definition")],
                              llm=llm, model=config.model, cache=cache, audits=audits)
            selected = [item for item in evaluations if item["accepted"]]
            selected.sort(key=lambda item: (-int(item["C4"]), -int(item["C1_name"]),
                                             item["distinct_count"], item["ordinal"]))
            state["activity_columns"] = [item["column"] for item in selected]
            if selected and len(state["ts_ids"]) >= 2:
                state["status"], state["encoding"] = "mixed", "mixed"
                state["primary_encoding"], state["row_overlay"] = "event_level_mixed", True
            elif selected:
                state["status"], state["encoding"] = "row_encoded", "row_encoded"
                state["primary_encoding"], state["row_overlay"] = "row_encoded", False
            else:
                state["status"], state["encoding"] = "column_encoded", "column_encoded"
                state["primary_encoding"], state["row_overlay"] = "column_encoded", False
            state["encoding_rule"] = {
                "source": "timestamp_first_then_carrier", "timestamp_unit_count": len(state["ts_ids"]),
                "carrier_count": len(selected),
                "primary_rule": "event_definitions_classified_independently",
                "rule": ("carrier_and_multiple_timestamps" if state["encoding"] == "mixed" else
                         "carrier_present" if state["encoding"] == "row_encoded" else
                         "carrier_absent")}
            conflict_group = f"CG:{table_name}:encoding" if state["encoding"] == "mixed" else None
            if state["encoding"] in {"column_encoded", "mixed"}:
                for ts_id in state["ts_ids"]:
                    unit = ts_by_id[ts_id]
                    dd_column = indexes["columns"].get((table_name, unit["columns"][0]), {})
                    if (not occurrence_time_policy(unit)["eligible"]
                            and not dd_column.get("event_activity")
                            and documented_represented_clock(dd_column.get("definition", ""))):
                        continue
                    name = _activity_name_from_timestamp(unit, dd_column)
                    alpha = {"kind": "column", "column": None, "value": None, "name": name}
                    bindings.append({"id": event_definition_id(table_name, alpha, ts_id),
                                     "table": table_name, "alpha": alpha, "ts_id": ts_id,
                                     "interpretation_status": (
                                         "supported" if (dd_column.get("event_activity") or
                                             occurrence_time_policy(unit)["eligible"]
                                             and unit.get("confidence_basis") == "explicit_dictionary")
                                         and unit.get("role_status") == "supported" else "unresolved"),
                                     **({'documented_column_clock': dd_column.get("id")}
                                         if unit.get("confidence_basis") == "explicit_dictionary" else {}),
                                     **_activity_provenance(
                                         table_name, alpha, unit, "timestamp_column_name"),
                                     "paths": [], "encoding_interpretation": "column",
                                     "conflict_group": conflict_group, "provenance": "rule",
                                     **_null_evidence(connection, table_name, unit, indexes),
                                     "evidence": _binding_evidence(dd_column, "R3.column_encoded")})
            if state["encoding"] in {"row_encoded", "mixed"}:
                selected[0]["primary"] = True
                for item in selected:
                    column = item["column"]
                    dd_column = indexes["columns"].get((table_name, column), {})
                    lookup = code_table_evidence(connection, table, column, table_by_name, dd)
                    observed, value_support = profile_carrier_family(
                        connection, table, column, local_units, dd_column, lookup)
                    values = [value for _, value in value_support]
                    observed_carrier_values[column] = [value for _, value in observed]
                    table_context = table_doc if table_doc and (len(selected) == 1 or
                        column in table_doc.get("definition", "")) else None
                    resolutions = [(value, deterministic_meanings(dd_column, value, lookup, table_context))
                                   for value in values]
                    interpret_values(table_name, dd_column, resolutions, llm=llm, model=config.model,
                                     cache=cache, audits=audits)
                    pairs, pending = [], []
                    for value, resolution in resolutions:
                        label = resolution["code_meaning"] or str(value)
                        alpha = {"kind": "value", "column": column, "value": value, "name": label}
                        for statistic in value_support[(type(value), value)]:
                            unit = ts_by_id[statistic["ts_id"]]
                            clock_doc = clock_docs[unit["ts_id"]]
                            probe = {"table": table_name, "alpha": alpha}
                            scoped = scoped_event_clock(probe, unit, dd_column, clock_doc, resolution=resolution)
                            relationship = carrier_clock_relationship(
                                scoped, clock_doc, dd_column, alpha, resolution, statistic,
                                work_endpoints=work_endpoints)
                            identifier = event_definition_id(table_name, alpha, unit["ts_id"])
                            pair = (identifier, alpha, scoped, statistic, relationship, probe)
                            pairs.append((resolution, pair))
                            if (relationship["status"] == "unresolved" and resolution["status"] == "supported"
                                    and clock_doc.get("definition") and occurrence_time_policy(scoped)["eligible"]
                                    and scoped.get("role_status") == "supported"):
                                pending.append((identifier, {"value": value, "resolution": resolution,
                                    "unit": scoped, "clock": clock_doc, "relationship": relationship}))
                    interpret_relationships(table_name, column, pending, llm=llm, model=config.model,
                                            cache=cache, audits=audits)
                    for resolution, (identifier, alpha, unit, statistic, relationship, probe) in pairs:
                        value = alpha["value"]
                        matrix.append({"table": table_name, "carrier": column, "value": value,
                            "ts_id": unit["ts_id"], "clock": unit["columns"], "population": statistic["population_count"],
                            "timed_rows": statistic["support_count"], "candidate_id": identifier,
                            "value_semantics_status": resolution["status"], "value_meaning": resolution["code_meaning"],
                            "value_citations": resolution.get("citations", []), **relationship})
                        if relationship["status"] not in {"supported", "non_occurrence"}:
                            continue
                        canonical = {**alpha, "name": relationship.get("label", alpha["name"])}
                        binding = {"id": identifier, "table": table_name, "alpha": canonical, "ts_id": unit["ts_id"],
                            "interpretation_status": ("supported" if relationship["status"] == "supported"
                                                      else "unresolved"),
                            "timestamp_pairing": {"status": relationship["status"], "selected": unit["ts_id"],
                                "phase": relationship["phase"], "reason": relationship["reason"],
                                "timed_rows": statistic["support_count"], "clock_evidence_id": relationship["clock_evidence_id"],
                                "occurrence_discriminator": unit["ts_id"]},
                            "carrier_clock_relationship": relationship,
                            "carrier_value_semantics": resolution,
                            "paths": [], "encoding_interpretation": "row", "conflict_group": conflict_group,
                            "carrier_role": "primary" if item.get("primary") else "alternative",
                            "provenance": "rule",
                            **_activity_provenance(table_name, canonical, unit, "documented_carrier_clock"),
                            "null_count": statistic["population_count"] - statistic["support_count"],
                            "null_ratio": (1 - statistic["support_count"] / statistic["population_count"]
                                           if statistic["population_count"] else 0.0),
                            "null_meaning": _null_meaning(table_name, unit, indexes),
                            "null_policy": "exclude_and_report",
                            "untimed_excluded_count": statistic["population_count"] - statistic["support_count"],
                            "evidence": _binding_evidence(dd_column, "R2.carrier_clock_relationship", [
                                {"kind": e["kind"], "ref": e["id"], "quote": e["text"]} for e in resolution["evidence"]])}
                        if proof := probe.get("scoped_clock_evidence"):
                            binding["scoped_clock_evidence"] = proof
                        bindings.append(binding)
            history_status = None
            if history := table_doc.get("state_history"):
                specialized, history_status = history_definitions(
                    connection, table, history, bindings[binding_start:], local_units, dd, table_by_name, indexes)
                state_column = history.get("state_column")
                clock = history.get("occurrence_column")
                bindings[binding_start:] = [item for item in bindings[binding_start:]
                    if not (item["alpha"]["kind"] == "value" and item["alpha"].get("column") == state_column
                        or item["alpha"]["kind"] == "column" and ts_by_id[item["ts_id"]]["columns"] == [clock])]
                bindings.extend(specialized)
            elif related := table_doc.get("related_occurrence"):
                specialized, history_status = related_definitions(
                    connection, table, related, bindings[binding_start:], dd, table_by_name, indexes)
                clock = related.get("occurrence_column")
                bindings[binding_start:] = [item for item in bindings[binding_start:]
                    if item["alpha"]["kind"] != "column" or ts_by_id[item["ts_id"]]["columns"] != [clock]]
                bindings.extend(specialized)
            traces[table_name] = {"observed_carrier_values": observed_carrier_values,
                                  "state_history_status": history_status,
                                  "activity_evaluations": evaluations,
                                  "selected_activity_columns": list(state["activity_columns"]),
                                  "encoding_rule": dict(state["encoding_rule"]),
                                  'carrier_timestamp_matrix':matrix}
        return sorted(bindings, key=lambda item: item["id"]), traces
    finally:
        connection.close()
