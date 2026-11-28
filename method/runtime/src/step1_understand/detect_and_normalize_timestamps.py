"""Recall-oriented timestamp-unit discovery and normalization metadata."""

from __future__ import annotations
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any
import json
import math
import re
import sqlite3
from src.step1_understand.eeg_configuration import DbuConfig
from src.common.data_dictionary import dictionary_indexes
from src.common.graph_identifiers import timestamp_id
from src.common.database_io import connect_readonly, quote_identifier
from src.eeg.evidence_graph_models import Table
SQL_TIME_TYPES = (
    "DATE", "TIME", "TIMESTAMP", "DATETIME", "DATETIME2", "DATETIMEOFFSET",
    "SMALLDATETIME", "TIMESTAMPTZ", "WITH TIME ZONE", "WITHOUT TIME ZONE")


def name_tokens(value: str) -> list[str]:
    """PURPOSE: Tokenize snake_case and camelCase names for semantic signals.
    INPUT: Physical or JSON field name.
    OUTPUT: Lowercase alphanumeric tokens.
    """
    expanded = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    return [part.casefold() for part in re.split(r"[^A-Za-z0-9]+", expanded) if part]


HEDGED = re.compile(r"\b(?:may|might|could|would|possibly|probably|presumably|approximate(?:ly)?|estimated?|"
                    r"roughly|unclear|unverified|whether)\b")
_IRREGULAR_PAST = {"left", "sent", "made", "took", "began", "paid", "sold", "bought", "gave", "wrote", "held",
                   "met", "built", "won", "lost", "brought", "kept", "found", "became", "drove", "rode", "went", "came"}
_NOT_VERBS = {"need", "seed", "feed", "speed", "bed", "red", "shed", "hundred", "bred"}


def past_action_verbs(text: str) -> set[str]:
    """PURPOSE: Find past-tense action words the time-role and activity rules may cite.
    INPUT: Clause text. OUTPUT: Word tokens; '-ed' words after an article are adjectives, not actions.
    shortcut: word-level, not a parser; irregular verbs outside the list and present tense are not
    detected, so those clocks stay unknown for the model rather than being settled by rule.
    """
    words = re.findall(r"[a-z]+", text.casefold())
    return {word for index, word in enumerate(words)
            if (word in _IRREGULAR_PAST or (len(word) > 4 and word.endswith("ed") and word not in _NOT_VERBS))
            and not (index and words[index - 1] in {"the", "a", "an", "this", "that", "its", "their"})}


def documented_action_clock(definition):
    """PURPOSE: Recognize direct, documented row-action or observation clocks.
    INPUT: Public timestamp definition. OUTPUT: Action noun, or None when the text does not describe one.
    """
    match = re.match(
        r"^\s*(?:the )?(?:date and )?time (?:of (?:the )?(?:actual |physical |on-site )?"
        r"(?P<of>actions?|activities|activity|events?|occurrences?|operations?|observations?|scans?)"
        r"|(?:when |at which )?(?:the )?"
        r"(?P<when>actions?|activity|events?|occurrences?|operations?|observations?|scans?) "
        r"(?:occurred|happened|(?:was|is) (?:made|performed|completed|observed)))\b",
        definition, re.I)
    if match:
        return (match.group('of') or match.group('when')).casefold()
    explicit = re.match(
        r"^\s*(?:the )?actual (action|activity|event|operation|observation|scan)"
        r" (?:occurrence )?(?:date and )?time\b",definition,re.I)
    return explicit.group(1).casefold() if explicit else None


def timestamp_semantic_role(table: str, columns: list[str], dd_column: dict[str, Any],
                            *, json_path: str | None = None) -> dict[str, Any]:
    """PURPOSE: Classify a TimestampUnit's meaning without changing temporal detection.
    INPUT: Physical source and its Data Dictionary record.
    OUTPUT: Controlled semantic role, evidence, status and confidence basis.
    """
    source = " ".join([table, *columns, json_path or ""])
    definition = str(dd_column.get("definition", ""))
    documented_activity = str(dd_column.get("event_activity", "")).strip()
    from src.common.event_clock import documented_message_receipt_clock
    non_occurrence = (("non_event_time", r"\b(?:attribute rather than an event|not an event timestamp|date of birth)\b"),
                      ("estimated_time", r"\b(?:estimated|forecast|predicted)\s+(?:date|time|arrival|departure|completion)\b"),
                      ("ingestion_time", r"\b(ingest(?:ed|ion)?|database load|record load|loaded into|etl|imported)\b"),
                      ("scheduled_time", r"\b(schedule[ds]?|planned|expected|due)\b|\b(?:in|per|from) the (?:\w+ )?(?:plan|schedule)\b"),
                      ("recorded_time", r"\b(database record|database update|transaction time|db record|db update|database logged)\b"
                                        r"|\b(?:row|record|entry) (?:was |is )?(?:last )?(?:written|inserted|saved|stored|updated|modified|created)\b"
                                        r"|\bwritten to the database\b|\blast (?:updated|modified)\b"
                                        r"|\b(?:row|record|entry) (?:was |is )?posted (?:to|in) (?:the|a) (?:\w+ )?(?:system|database)\b"
                                        r"|\b(?:recorded|documented|entered|stored|logged|registered) in (?:the|a) (?:\w+ )?(?:system|database)\b"
                                        r"|\b(?:system|database|server) (?:received|stored|ingested) (?:the |a )?(?:record|row|entry|message)\b"))
    scoped_definition = re.split(r",?\s+(?:distinct from|rather than|not)\b", definition,
                                 maxsplit=1, flags=re.I)[0]
    actual_action = bool(re.search(
        r"\bactual\b[^.!?]*\b(?:occurrence time|time of|time when|time at which)\b",
        scoped_definition, re.I))
    for role, pattern in non_occurrence:
        if role == "scheduled_time" and actual_action and not re.search(
                r"\b(planned|scheduled|expected|due)\s+(?:date|time)\b", scoped_definition, re.I):
            continue
        if re.search(pattern, scoped_definition, re.I):
            return {"semantic_role": role, "role_status": "supported",
                    "role_evidence": [{"source": "dictionary_description", "detail": definition}],
                    "confidence_basis": "explicit_dictionary",
                    "alternatives": (["business_occurrence"] if documented_activity else [])}
    if re.search(r"\b(effective|valid from|valid until|takes effect)\b", definition, re.I):
        return {"semantic_role": "effective_time", "role_status": "supported",
                "role_evidence": [{"source": "dictionary_description", "detail": definition}],
                "confidence_basis": "explicit_dictionary"}
    if documented_activity:
        return {"semantic_role": "business_occurrence",
                "role_evidence": [{"source": "dictionary_event_activity",
                                   "detail": documented_activity},
                                  {"source": "dictionary_description",
                                   "detail": definition}],
                "role_status": "supported",
                "confidence_basis": "explicit_dictionary"}
    text = f"{source} {definition}".casefold()
    definition_text = definition.casefold()
    # Negated, hedged or conditional wording never settles a role by rule; it stays unknown for the model.
    # Sentences explaining NULL/missing values ("NULL if not shipped") describe absence, not the clock's meaning.
    meaning_text = " ".join(s for s in re.split(r"(?<=[.;])\s+", definition_text)
                            if not re.search(r"\b(?:null|empty|blank|missing)\b", s))
    if HEDGED.search(meaning_text):
        return {"semantic_role": "unknown", "role_evidence": [{"source": "dictionary_description", "detail": definition}],
                "role_status": "unknown", "confidence_basis": "hedged_or_negated_wording"}
    # A definition that opens with "Actual <noun>" describes the clock of that actual action.
    explicit_actual = bool(re.match(r"\s*(?:the\s+)?actual\b", definition_text)) or (
                       bool(re.search(r"\bactual\b", definition_text)) and
                       bool(re.search(
                           r"\b(time|occurrence|completion|start|approval|receipt|dispatch|submission)\b",
                           definition_text)))
    # Plain prose "When <subject> <past-tense verb> ..." states a completed real-world action. Planned,
    # recorded/loaded and hedged wording already returned above, so only that reading is left here.
    when_clause = re.match(r"\s*(?:the\s+)?(?:(?:date|time|date and time|moment)\s+)?(?:when|at which)\s+(.+)",
                           definition_text)
    negated_action = bool(when_clause and re.search(r"\b(?:not|never|no longer|failed to)\b", when_clause.group(1)))
    explicit_occurrence = explicit_actual or bool(when_clause and not negated_action and past_action_verbs(when_clause.group(1))) or bool(
        re.search(r"\b(time (?:when|at which) .* (?:occurred|happened)|occurred time)\b", text))
    documented_creation = bool(re.match(
        r"^time (?:when )?the [\w -]+ was created\.?$",scoped_definition,re.I))
    if (explicit_occurrence or documented_creation or documented_action_clock(definition)
            or documented_message_receipt_clock(definition)):
        return {"semantic_role": "business_occurrence",
                "role_evidence": [{"source": "dictionary_description",
                                   "detail": definition}],
                "role_status": "supported",
                "confidence_basis": "explicit_dictionary"}
    rules = (
        ("ingestion_time", r"\b(ingest(?:ed|ion)?|load(?:ed|ing)?|etl|imported)\b"),
        ("scheduled_time", r"\b(schedule[ds]?|planned|expected|appointment|due)\b"),
        ("recorded_time", r"\b(recorded|inserted|audit(?:ed)?|database update|system update)\b"),
        ("effective_time", r"\b(effective|valid from|valid until|takes effect)\b"),
        ("business_occurrence", r"\b(actual|occurred|happened|completed|finished|started|approved|received|shipped|dispatched|issued|submitted|changed)\b"),
    )
    for role, pattern in rules:
        if re.search(pattern, text):
            explicit = bool(definition and re.search(pattern, definition.casefold()))
            return {"semantic_role": role,
                    "role_evidence": [{"source": "dictionary_description" if explicit else "source_name",
                                       "detail": definition if explicit else source}],
                    "role_status": "supported" if explicit else "candidate",
                    "confidence_basis": "explicit_dictionary" if explicit else "weak_lexical_rule"}
    return {"semantic_role": "unknown", "role_evidence": [],
            "role_status": "unknown", "confidence_basis": "insufficient_evidence"}


def occurrence_time_policy(unit):
    """PURPOSE: Separate temporal role from permission to use a clock as occurrence time.
    INPUT: Timestamp unit with role status and scoped dictionary evidence.
    OUTPUT: Auditable supported/unresolved decision; planned/recorded units remain in inventory.
    """
    role = unit.get('semantic_role', 'unknown')
    text = ' '.join(str(e.get('detail', '')) for e in unit.get('role_evidence', [])
                    if e.get('source') in {'dictionary_description', 'dictionary_event_activity'})
    transition = bool(re.search(
        r"\b(occurred|happened|changed|became|activated|deactivated)\b|"
        r"\bactual\b[^.!?]*\b(activity|event|occurrence|transition)\b", text, re.I))
    allowed = unit.get('role_status') == 'supported' and (
        role == 'business_occurrence' or role == 'effective_time' and transition)
    return {'status': 'supported' if allowed else 'unresolved',
            'eligible': allowed, 'semantic_role': role,
            'reason': 'documented_occurrence_clock' if allowed else
                      'effective_transition_evidence_required' if role == 'effective_time' else
                      'occurrence_role_not_supported',
            'evidence': list(unit.get('role_evidence', []))}


def _epoch_format(number: float) -> tuple[str, str] | None:
    """PURPOSE: Classify numeric Unix epochs using a bounded 1970–2100 range.
    INPUT: Finite numeric value.
    OUTPUT: Format and precision or None.
    """
    if not math.isfinite(number):
        return None
    for format_id, divisor, precision in (
        ("epoch_ns", 1e9, "ns"), ("epoch_us", 1e6, "us"),
        ("epoch_ms", 1e3, "ms"), ("epoch_s", 1, "second")):
        seconds = number / divisor
        if 0 <= seconds <= 4_102_444_800:
            magnitude = abs(number)
            expected = {"epoch_s": 1e9, "epoch_ms": 1e12, "epoch_us": 1e15, "epoch_ns": 1e18}[format_id]
            if magnitude >= expected * 0.1:
                return format_id, precision
    return None


def parse_temporal(value: Any, dd_format: str = "") -> tuple[str, str, datetime | None] | None:
    """PURPOSE: Recognize supported timestamp representations without assigning event meaning.
    INPUT: SQLite scalar and optional documented format.
    OUTPUT: (format ID, precision, parsed datetime when available) or None.
    """
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        text = str(value)
        integer = str(int(value)) if float(value).is_integer() else ""
        if integer and len(integer) in (8, 12, 14):
            try:
                fmt = {8: "%Y%m%d", 12: "%Y%m%d%H%M", 14: "%Y%m%d%H%M%S"}[len(integer)]
                return "compact", {8: "day", 12: "minute", 14: "second"}[len(integer)], datetime.strptime(integer, fmt)
            except ValueError:
                pass
        epoch = _epoch_format(float(value))
        if epoch:
            return epoch[0], epoch[1], datetime.fromtimestamp(float(value) / {
                "epoch_s": 1, "epoch_ms": 1e3, "epoch_us": 1e6, "epoch_ns": 1e9}[epoch[0]], tz=timezone.utc)
        if 2_440_588 <= float(value) <= 2_488_070:
            return "julianday", "ms", datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(days=float(value)-2440587.5)
        if 25_569 <= float(value) <= 73_051:
            return "excel_serial", "day", datetime(1899, 12, 30) + timedelta(days=float(value))
        return None
    text = str(value).strip()
    if not text:
        return None
    if re.fullmatch(r"\d{4}", text):
        return "year_only", "year", datetime(int(text), 1, 1)
    if re.fullmatch(r"\d{4}-\d{2}", text) or re.fullmatch(r"\d{6}", text):
        try:
            return "year_month", "month", datetime.strptime(text, "%Y-%m" if "-" in text else "%Y%m")
        except ValueError:
            return None
    if re.fullmatch(r"\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?", text) or re.fullmatch(r"\d{6}", text):
        for fmt, precision in (("%H:%M", "minute"), ("%H:%M:%S", "second"), ("%H:%M:%S.%f", "us"), ("%H%M%S", "second")):
            try:
                return "time_only", precision, datetime.strptime(text, fmt)
            except ValueError:
                continue
    if re.fullmatch(r"\d{8}(?:T?\d{6}Z?)?", text):
        clean = text.replace("T", "").rstrip("Z")
        try:
            parsed = datetime.strptime(clean, "%Y%m%d" if len(clean) == 8 else "%Y%m%d%H%M%S")
            return ("iso_basic" if "T" in text or text.endswith("Z") else "compact",
                    "day" if len(clean) == 8 else "second", parsed)
        except ValueError:
            pass
    iso = text.replace("Z", "+00:00")
    iso = re.sub(r" ([+-]\d{2})(\d{2})$", r"\1:\2", iso)
    try:
        parsed = datetime.fromisoformat(iso)
        offset = parsed.tzinfo is not None or text.endswith("Z") or bool(re.search(r"[+-]\d{2}:?\d{2}$", text))
        precision = "us" if "." in text else "second" if re.search(r":\d{2}(?:[.+-]|$|Z)", text) else "minute" if "T" in text or " " in text else "day"
        return ("iso_offset" if offset else "iso_datetime" if ":" in text else "iso_date", precision, parsed)
    except ValueError:
        pass
    ambiguous = bool(re.fullmatch(r"\d{1,2}[/.]\d{1,2}[/.]\d{4}(?:\s+.*)?", text))
    dd_day_first = not bool(re.search(r"MM[/.-]DD", dd_format, re.I))
    formats = ["%d/%m/%Y", "%m/%d/%Y", "%d.%m.%Y", "%Y/%m/%d", "%Y.%m.%d"]
    if not dd_day_first:
        formats[:2] = formats[1::-1]
    for fmt in formats:
        for suffix, precision in (("", "day"), (" %H:%M", "minute"), (" %H:%M:%S", "second")):
            try:
                return "slash_dot", precision, datetime.strptime(text, fmt + suffix)
            except ValueError:
                continue
    for fmt in ("%d-%b-%Y", "%b %d, %Y", "%d %B %Y", "%d %B %Y %H:%M"):
        try:
            parsed = datetime.strptime(text, fmt)
            return "month_name", "minute" if "%H" in fmt else "day", parsed
        except ValueError:
            continue
    if re.fullmatch(r"[+-]?\d+(?:\.\d+)?", text):
        try:
            return parse_temporal(float(text), dd_format)
        except ValueError:
            return None
    return None


def _scan_values(connection: sqlite3.Connection, table: str, column: str, limit: int,
                 key_columns: list[str] | None = None) -> list[Any]:
    """PURPOSE: Read a bounded deterministic non-null scan for temporal parsing.
    INPUT: Connection, physical table/column and maximum rows.
    OUTPUT: Non-null prefix ordered by declared PK, otherwise rowid; no occurrence IDs are invented.
    """
    order = ", ".join(quote_identifier(key) for key in (key_columns or [])) or "rowid"
    return [row[0] for row in connection.execute(
        f"SELECT {quote_identifier(column)} FROM {quote_identifier(table)} "
        f"WHERE {quote_identifier(column)} IS NOT NULL ORDER BY {order} LIMIT ?", (limit,))]


def _signals(table: Table, column: Any, dd_column: dict[str, Any], values: list[Any], config: DbuConfig) -> dict[str, Any]:
    """PURPOSE: Compute S1–S5 and format distribution for one physical column.
    INPUT: Schema, DD record, bounded values and configuration.
    OUTPUT: Complete acceptance/rejection trace.
    """
    declared = column.declared_type.upper()
    dd_type_text = " ".join(str(dd_column.get(key, "")) for key in ("type", "representation_class", "format")).casefold()
    definition = str(dd_column.get("definition", "")).casefold()
    tokens = set(name_tokens(column.name))
    s1 = any(keyword in declared for keyword in SQL_TIME_TYPES)
    s2 = any(keyword.casefold() in dd_type_text for keyword in config.dd_time_type_keywords)
    s3 = any(re.search(r"\b" + re.escape(word.casefold()) + r"\b", definition) for word in config.dd_time_words)
    s4 = bool(tokens.intersection(config.ts_name_tokens))
    parsed = [parse_temporal(value, str(dd_column.get("format", ""))) for value in values]
    counts = Counter(item[0] for item in parsed if item)
    ratio = sum(item is not None for item in parsed) / len(values) if values else 0.0
    detected = sorted(counts, key=lambda item: (-counts[item], item))[0] if counts else None
    format_mix = {key: counts[key] / len(values) for key in sorted(counts)} if values else {}
    numeric_only = bool(values) and all(isinstance(value, (int, float)) or re.fullmatch(r"[+-]?\d+(?:\.\d+)?", str(value).strip()) for value in values)
    numeric_formats = bool(counts) and set(counts) <= {"compact", "epoch_s", "epoch_ms", "epoch_us", "epoch_ns", "julianday", "excel_serial", "year_only", "year_month"}
    accepted_by = None
    if s1: accepted_by = "S1"
    elif s2: accepted_by = "S2"
    elif ratio >= config.ts_parse_ratio_strict: accepted_by = "strict_parse"
    elif ratio >= config.ts_parse_ratio_loose and s3: accepted_by = "loose_parse+S3"
    elif ratio >= config.ts_parse_ratio_loose and s4: accepted_by = "loose_parse+S4"
    rejection = None
    if detected == "year_only":
        accepted_by, rejection = None, "year_only"
    elif numeric_only and numeric_formats and not (s2 or s3 or s4):
        accepted_by, rejection = None, "numeric_without_support"
    key_columns = set(table.primary_key)
    for fk in table.foreign_keys:
        key_columns.update(left for left, _ in fk["columns"])
    is_key = column.name in key_columns
    if is_key and not (s1 or s2):
        accepted_by, rejection = None, "key_without_type_support"
    precision = next((item[1] for item in parsed if item and item[0] == detected), None)
    return {"S1": s1, "S2": s2, "S3": s3, "S4": s4, "parse_ratio": ratio,
            "detected_format": detected, "format_mix": format_mix, "precision": precision,
            "accepted_by": accepted_by, "rejection_reason": rejection, "is_key": is_key,
            "sample_count": len(values)}


def _json_paths(value: Any, prefix: str, depth: int) -> list[tuple[str, Any]]:
    """PURPOSE: Enumerate scalar JSON object leaves to a fixed depth.
    INPUT: Parsed value, JSONPath prefix and remaining depth.
    OUTPUT: Stable path/value pairs; arrays are not expanded.
    """
    if depth < 0 or not isinstance(value, dict):
        return []
    result = []
    for key in sorted(value):
        child, path = value[key], prefix + "." + str(key)
        if isinstance(child, dict):
            result.extend(_json_paths(child, path, depth - 1))
        elif not isinstance(child, (list, dict)):
            result.append((path, child))
    return result


def detect_timestamps(db_path: Path, tables: list[Table], profiles: dict[str, Any], dd: dict[str, Any], config: DbuConfig) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """PURPOSE: Discover column, composite and JSON timestamp units with full rule traces.
    INPUT: Allowed DB/DD inputs, physical schema, profiles and thresholds.
    OUTPUT: Accepted TimestampUnits and per-table column/JSON/rejection traces.
    """
    indexes = dictionary_indexes(dd)
    connection = connect_readonly(db_path)
    units: list[dict[str, Any]] = []
    traces: dict[str, Any] = {}
    try:
        for table in tables:
            column_traces, accepted, time_only = {}, [], []
            table_zone = indexes["tables"].get(table.name, {}).get("timezone") or dd.get("timezone")
            for column in table.columns:
                dd_column = indexes["columns"].get((table.name, column.name), {})
                column_zone = dd_column.get("timezone") or table_zone
                values = _scan_values(connection, table.name, column.name, config.ts_scan_limit, table.primary_key)
                trace = _signals(table, column, dd_column, values, config)
                column_traces[column.name] = trace
                if trace["accepted_by"]:
                    unit = {"ts_id": timestamp_id(table.name, [column.name]), "table": table.name,
                            "source": "column", "columns": [column.name], "json_path": None,
                            "detected_format": trace["detected_format"], "format_mix": trace["format_mix"],
                            "precision": trace["precision"], "timezone": column_zone,
                            "parse_ratio": trace["parse_ratio"], "null_ratio": profiles[table.name]["columns"][column.name]["null_count"] / max(1, profiles[table.name]["row_count"]),
                            "is_key": trace["is_key"], "ambiguous_format": False,
                            "accepted_by": trace["accepted_by"], "dd_definition_id": dd_column.get("id"),
                            "documented_event_activity": dd_column.get("event_activity") or None,
                            "source_origin": dd_column.get("source_origin") or None,
                            "evidence": _timestamp_evidence(trace, dd_column)}
                    if re.search(r"MM[/.-]DD", str(dd_column.get("format", "")), re.I):
                        unit["month_first"] = True  # same day/month rule parse_temporal applied
                    unit.update(timestamp_semantic_role(table.name, [column.name], dd_column))
                    if trace["detected_format"] == "time_only":
                        time_only.append(unit)
                    else:
                        accepted.append(unit)
                json_values = []
                parsed_json = []
                for value in values:
                    if not isinstance(value, str): continue
                    try: parsed_json.append(json.loads(value))
                    except (ValueError, TypeError): pass
                if values and len(parsed_json) / len(values) >= config.json_ratio and all(isinstance(item, dict) for item in parsed_json):
                    by_path: dict[str, list[Any]] = {}
                    for item in parsed_json:
                        for path, scalar in _json_paths(item, "$", config.json_max_depth):
                            by_path.setdefault(path, []).append(scalar)
                    for path, path_values in sorted(by_path.items()):
                        pseudo = type("JsonColumn", (), {"name": path.rsplit(".", 1)[-1], "declared_type": "TEXT"})()
                        jtrace = _signals(table, pseudo, {"definition": "", "format": ""}, path_values, config)
                        column_traces[f"{column.name}{path}"] = jtrace
                        if jtrace["accepted_by"] and jtrace["detected_format"] != "time_only":
                            json_unit = {"ts_id": timestamp_id(table.name, [column.name], path), "table": table.name,
                                "source": "json_path", "columns": [column.name], "json_path": path,
                                "detected_format": jtrace["detected_format"], "format_mix": jtrace["format_mix"],
                                "precision": jtrace["precision"], "timezone": column_zone,
                                "parse_ratio": jtrace["parse_ratio"], "null_ratio": 0.0, "is_key": False,
                                "ambiguous_format": False, "accepted_by": jtrace["accepted_by"],
                                "dd_definition_id": dd_column.get("id"), "evidence": _timestamp_evidence(jtrace, dd_column)}
                            json_unit.update(timestamp_semantic_role(
                                table.name, [column.name], dd_column, json_path=path))
                            accepted.append(json_unit)
            used = set()
            for clock in time_only:
                clock_name = clock["columns"][0]
                clock_stem = _time_stem(clock_name)
                dates = [item for item in accepted if item["source"] == "column" and item["precision"] == "day" and _time_stem(item["columns"][0]) == clock_stem]
                if dates:
                    date = sorted(dates, key=lambda item: item["ts_id"])[0]
                    accepted.remove(date); used.add(clock_name)
                    composite = dict(date)
                    composite.update({"ts_id": timestamp_id(table.name, [date["columns"][0], clock_name]),
                                      "source": "composite", "columns": [date["columns"][0], clock_name],
                                      "precision": clock["precision"], "accepted_by": "date_time_composite",
                                      "timezone": clock.get("timezone") or date.get("timezone"),
                                      "evidence": date["evidence"] + clock["evidence"] + [{"kind":"rule","id":"R1.date_time_composite","outcome":"accepted"}]})
                    composite.update(timestamp_semantic_role(
                        table.name, composite["columns"],
                        indexes["columns"].get((table.name, date["columns"][0]), {})))
                    accepted.append(composite)
                else:
                    column_traces[clock_name]["rejection_reason"] = "time_only_unpaired"
            units.extend(accepted)
            traces[table.name] = {"columns": column_traces, "ts_ids": sorted(item["ts_id"] for item in accepted)}
        return sorted(units, key=lambda item: item["ts_id"]), traces
    finally:
        connection.close()


def _time_stem(name: str) -> str:
    """PURPOSE: Remove common date/time suffix tokens for composite pairing.
    INPUT: Column name.
    OUTPUT: Normalized stem.
    """
    return re.sub(r"(?:_|^)(?:date|time|dt|tm|udate|utime)$", "", name.casefold()).strip("_")


def _timestamp_evidence(trace: dict[str, Any], dd_column: dict[str, Any]) -> list[dict[str, Any]]:
    """PURPOSE: Materialize DD, statistical and rule evidence for a timestamp decision.
    INPUT: Signal trace and optional DD column.
    OUTPUT: Ordered evidence records.
    """
    evidence: list[dict[str, Any]] = []
    if dd_column.get("id"):
        evidence.append({"kind": "dd", "ref": dd_column["id"], "quote": dd_column.get("definition", "")})
    evidence.append({"kind": "stat", "name": "parse_ratio", "value": trace["parse_ratio"],
                     "sample_count": trace["sample_count"],
                     "denominator": "scanned_non_null_values_for_columns; present_leaves_for_json",
                     "scope": "bounded_prefix_by_pk_else_rowid"})
    evidence.append({"kind": "rule", "id": "R1." + str(trace["accepted_by"]), "outcome": "accepted"})
    return evidence


def normalization_sql(unit: dict[str, Any]) -> str:
    """PURPOSE: Compile a TimestampUnit to a deterministic UTC-oriented SQLite expression.
    INPUT: Validated TimestampUnit with real columns/path and detected format.
    OUTPUT: SQL expression returning ISO-like text or NULL on SQLite conversion failure.
    """
    from src.common.sql_identifiers import quote_identifier as q
    def clock(text: str) -> str:
        # 'H:MM[:SS]' -> zero-padded hour; colon-free 'HHMMSS' (time_only %H%M%S) -> 'HH:MM:SS'.
        """PURPOSE: Compile zero-padded hour, minute, and second text.
        INPUT: SQLite expression for H:MM[:SS] or compact HHMMSS.
        OUTPUT: SQL expression preserving the supplied clock components."""
        digits = f"printf('%06d', {text})"
        return (f"CASE WHEN instr({text},':')=0 THEN substr({digits},1,2)||':'||substr({digits},3,2)||':'||substr({digits},5,2) "
                f"ELSE printf('%02d', substr({text},1,instr({text},':')-1))||substr({text},instr({text},':')) END")
    def token(text: str, n: int) -> str:
        # Fixed-width split: each space becomes 64 spaces, so token n sits alone in window n (values < 64 chars).
        """PURPOSE: Select one whitespace-delimited component in a timestamp expression.
        INPUT: SQLite text expression and a one-based token index; tokens are under 64 characters.
        OUTPUT: SQL expression yielding the trimmed component."""
        return f"trim(substr(replace({text},' ',printf('%64s','')),{(n-1)*64+1},64))"
    def instant(year: str, month: str, day: str, time: str = "'00:00'") -> str:
        # NULL unless SQLite keeps the date as written (it silently rolls 31-Feb into March).
        """PURPOSE: Compose an ISO timestamp while rejecting calendar rollover.
        INPUT: SQL expressions for year, month, day, and an optional clock.
        OUTPUT: SQL timestamp expression, or NULL for an invalid calendar date."""
        date = f"{year}||'-'||printf('%02d',{month})||'-'||printf('%02d',{day})"
        return f"CASE WHEN date({date})=({date}) THEN strftime('%Y-%m-%dT%H:%M:%fZ', {date}||' '||{time}) END"
    if unit["source"] == "composite":
        day = normalization_sql({**unit, "source": "column", "columns": unit["columns"][:1]})
        return f"strftime('%Y-%m-%dT%H:%M:%fZ', substr({day},1,10)||' '||{clock('CAST(' + q(unit['columns'][1]) + ' AS TEXT)')})"
    if unit["source"] == "json_path":
        value = f"json_extract({q(unit['columns'][0])}, '{unit['json_path']}')"
    else:
        value = q(unit["columns"][0])
    fmt = unit.get("detected_format")
    text = f"trim(CAST({value} AS TEXT))"
    if fmt == "year_month":
        return f"strftime('%Y-%m-%dT%H:%M:%fZ', CASE WHEN length({text})=6 THEN substr({text},1,4)||'-'||substr({text},5,2) ELSE {text} END||'-01')"
    if fmt in {"slash_dot", "month_name"}:
        parts = f"replace(replace(replace(replace({text},'/',' '),'.',' '),'-',' '),',','')"
        t1, t2, t3, t4 = (token(parts, n) for n in range(1, 5))
        time = f"CASE {t4} WHEN '' THEN '00:00' ELSE {clock(t4)} END"
        if fmt == "slash_dot":
            if unit.get("month_first"):
                dmy = instant(t3, t1, t2, time)
            else:
                dmy = instant(t3, t2, t1, time)
            return f"CASE WHEN length({t1})=4 THEN {instant(t1, t2, t3, time)} ELSE {dmy} END"
        def month(name: str) -> str:
            """PURPOSE: Convert a documented English month token to its ordinal.
            INPUT: SQL expression containing the month name.
            OUTPUT: SQL expression for a month number from one to twelve."""
            return f"(instr('JANFEBMARAPRMAYJUNJULAUGSEPOCTNOVDEC', upper(substr({name},1,3)))+2)/3"
        # '02-Mar-2024' / '02 March 2024 10:00' are day-first; 'Mar 02, 2024' starts with the month.
        return (f"CASE WHEN {t1} GLOB '[0-9]*' THEN {instant(t3, month(t2), t1, time)} "
                f"ELSE {instant(t3, month(t1), t2)} END")
    if fmt in {"epoch_s","epoch_ms","epoch_us","epoch_ns"}:
        divisor={"epoch_s":1,"epoch_ms":1000,"epoch_us":1000000,"epoch_ns":1000000000}[fmt]
        return f"strftime('%Y-%m-%dT%H:%M:%fZ', ({value}) / {divisor}.0, 'unixepoch')"
    if fmt == "julianday":
        return f"strftime('%Y-%m-%dT%H:%M:%fZ', {value})"
    if fmt == "excel_serial":
        return f"strftime('%Y-%m-%dT%H:%M:%fZ', (({value}) - 25569) * 86400, 'unixepoch')"
    if fmt in {"compact","iso_basic"}:
        text=f"CAST({value} AS TEXT)"
        return ("CASE length("+text+") WHEN 8 THEN substr("+text+",1,4)||'-'||substr("+text+",5,2)||'-'||substr("+text+",7,2)||'T00:00:00Z' "
                "WHEN 12 THEN substr("+text+",1,4)||'-'||substr("+text+",5,2)||'-'||substr("+text+",7,2)||'T'||substr("+text+",9,2)||':'||substr("+text+",11,2)||':00Z' "
                "WHEN 14 THEN substr("+text+",1,4)||'-'||substr("+text+",5,2)||'-'||substr("+text+",7,2)||'T'||substr("+text+",9,2)||':'||substr("+text+",11,2)||':'||substr("+text+",13,2)||'Z' END")
    return f"strftime('%Y-%m-%dT%H:%M:%fZ', {value})"
