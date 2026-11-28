"""Direct SQL baseline transport, public context and output checks from the prior evaluator."""


from contextlib import closing
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Any

from src.common.sql_identifiers import quote_identifier


DEFAULT_MODEL = "gpt-5-mini-2025-08-07"


def experiment_settings(model):
    """PURPOSE: Freeze the two poster models' decoding settings.
    INPUT: Requested model identifier. OUTPUT: Effective Chat Completions options.
    """
    if model in {'gpt-5-mini', DEFAULT_MODEL}:
        return {'reasoning_effort': 'medium'}
    if model in {'gpt-4o-mini', 'gpt-4o-mini-2024-07-18'}:
        return {'temperature': 0}
    return {}


def chat_settings(model):
    """PURPOSE: Select decoding options for raw SDK clients used in the pipeline.
    INPUT: Model ID. OUTPUT: Poster model settings or the pipeline's existing temperature default.
    """
    return experiment_settings(model) or {'temperature': 0}


SYSTEM = (
    "Generate one read-only SQLite query that directly extracts the event log requested by "
    "the user. You receive the complete public schema, a bounded sample of public database "
    "rows, the complete Data Dictionary, and the question. Return case_id, activity, "
    "timestamp, source_table, source_record_id, source_timestamp_column, occurrence_key. source_timestamp_column "
    "must be the physical timestamp/carrier column that identifies this occurrence; use an "
    "empty occurrence_key unless one physical record represents repeated independent events. "
    "Use the business object requested by the "
    "question as case_id. Use documented business activity names. Preserve one row per event "
    "occurrence, use UNION ALL for independent event sources, and do not turn a timestamp that "
    "merely timestamps a row event into a second event. Encode composite identifiers with "
    "json_array. Return unsupported only when the requested log cannot be defined from the "
    "supplied evidence. Never modify data."
)


def validate_occurrence_output_rows(rows: list[dict[str, Any]]) -> None:
    """PURPOSE: Enforce the Direct-LLM output contract required by occurrence evaluation.
    INPUT: Executed Direct SQL rows before any evaluator-only normalization.
    OUTPUT: None on success; ValueError triggers Gold-free SQL self-correction.
    """
    validation_rows = []
    for original in rows:
        row = dict(original)
        for field in ("case_id", "source_record_id"):
            value = row.get(field)
            if value is None or isinstance(value, (dict, list)):
                raise ValueError(f"{field} must be a scalar or JSON-array key")
            if not (isinstance(value, str) and value.lstrip().startswith("[")):
                row[field] = json.dumps([value], ensure_ascii=False)
        validation_rows.append(row)
    validate_output_rows(validation_rows)
    for row in rows:
        if not str(row.get("source_timestamp_column") or "").strip():
            raise ValueError("Direct SQL output is missing nonempty source_timestamp_column")
        if "occurrence_key" not in row or row["occurrence_key"] is None:
            raise ValueError("Direct SQL output is missing occurrence_key; use an empty string when absent")


def database_snapshot(database: Path, sample_rows: int = 3) -> dict[str, Any]:
    """PURPOSE: Represent a public SQLite DB for a text-only model without sending the binary.
    INPUT: Public database path and nonnegative bounded rows per table.
    OUTPUT: Complete DDL/counts plus deterministic bounded row samples; database is read-only.
    """
    uri = database.resolve().as_uri() + "?mode=ro"
    with closing(sqlite3.connect(uri, uri=True)) as connection:
        connection.row_factory = sqlite3.Row
        definitions = connection.execute(
            "SELECT name, sql FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall()
        tables = []
        for definition in definitions:
            name = str(definition["name"])
            quoted = quote_identifier(name)
            count = connection.execute(f"SELECT COUNT(*) FROM {quoted}").fetchone()[0]
            rows = [dict(row) for row in connection.execute(
                f"SELECT * FROM {quoted} LIMIT ?", (sample_rows,)).fetchall()]
            tables.append({"name": name, "row_count": count,
                           "create_sql": definition["sql"], "sample_rows": rows})
    return {"dbms": "SQLite", "sample_policy": f"first {sample_rows} rows per table",
            "tables": tables}


def normalized_time(value):
    """PURPOSE: Canonicalize timestamp rendering without changing event meaning.
    INPUT: ISO-like timestamp text, optionally carrying a UTC suffix or offset.
    OUTPUT: UTC-adjusted naive wall-clock text at microsecond precision.
    """
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed.isoformat(timespec='microseconds')


def decode_predicted_key(value):
    """PURPOSE: Decode compiler output keys without interpreting gold identifiers.
    INPUT: JSON-array encoded predicted case or source-record key.
    OUTPUT: Ordered tuple of string key components.
    """
    decoded = json.loads(value)
    if not isinstance(decoded, list):
        raise ValueError('Expected encoded key array')
    return tuple(str(item) for item in decoded)


SCHEMA={'type':'object','additionalProperties':False,'properties':{'status':{'type':'string','enum':['sql','unsupported']},'sql':{'type':['string','null']},'reason':{'type':'string'},'evidence':{'type':'array','items':{'type':'string'}}},'required':['status','sql','reason','evidence']}


def call_direct_sql(client, messages, model):
    """PURPOSE: Request structured SQL/refusal. INPUT: Audited client/messages/model. OUTPUT: Parsed answer."""
    response=client.chat.completions.create(model=model,**chat_settings(model),messages=messages,response_format={'type':'json_schema','json_schema':{'name':'direct_sql_self_correct','strict':True,'schema':SCHEMA}})
    return json.loads(response.choices[0].message.content)


def validate_output_rows(rows: list[dict]) -> None:
    """PURPOSE: Reject executable rows that violate the event-log output contract.
    INPUT: Direct-SQL rows after read-only SQLite execution.
    OUTPUT: None on success; ValueError supplies gold-free self-correction feedback.
    """
    if not rows:
        raise ValueError('Direct SQL returned an empty result; re-check retrieved sources, filters, and joins')
    for row in rows:
        decode_predicted_key(row['case_id'])
        source_id = row['source_record_id']
        if isinstance(source_id, str) and source_id.lstrip().startswith('['):
            decode_predicted_key(source_id)
        elif source_id is None or isinstance(source_id, (dict, list)):
            raise ValueError('source_record_id must be a scalar or JSON-array key')
        normalized_time(str(row['timestamp']))
