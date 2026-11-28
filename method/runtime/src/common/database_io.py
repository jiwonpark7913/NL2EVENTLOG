"""Read the two permitted DBU inputs."""

from __future__ import annotations
from pathlib import Path
from typing import Any
import json
from contextvars import ContextVar
import sqlite3
SQL_COUNTER = ContextVar("readonly_sql_counter", default=None)
from src.common.data_dictionary import normalize_dictionary
from src.eeg.evidence_graph_models import Column, Table
from src.common.runtime_input_contract import require_public_path
from src.common.attribution_policy import declared_foreign_key_groups, quote_identifier


def connect_readonly(db_path: str | Path) -> sqlite3.Connection:
    """PURPOSE: Open one SQLite file strictly read-only.
    INPUT: Relative or absolute path; '#', '?', '%' or spaces in it are URL-encoded by as_uri().
    OUTPUT: Read-only connection; the caller closes it.
    """
    connection = sqlite3.connect(Path(db_path).resolve().as_uri() + "?mode=ro", uri=True)
    counter = SQL_COUNTER.get()
    if counter is not None:
        connection.set_trace_callback(lambda statement: counter.update(["sql_statements"]))
    return connection


def _unique_keys(connection: sqlite3.Connection, table: str) -> list[list[str]]:
    """PURPOSE: Read unique indexes in deterministic ordinal order.
    INPUT: Open read-only connection and table.
    OUTPUT: Ordered unique column groups.
    """
    groups = []
    for row in connection.execute(f"PRAGMA index_list({quote_identifier(table)})"):
        if not row[2] or row[4]:
            continue
        columns = [item[2] for item in connection.execute(
            f"PRAGMA index_info({quote_identifier(row[1])})")]
        if columns and all(isinstance(column, str) for column in columns):
            groups.append(columns)
    return sorted(groups)


def _ddl_parts(ddl: str) -> list[str]:
    """PURPOSE: Split a CREATE TABLE body at top-level commas without losing composite constraints.
    INPUT: Original sqlite_master DDL.
    OUTPUT: Ordered column/constraint clauses for cross-checking only.
    """
    start=ddl.find("("); end=ddl.rfind(")")
    if start < 0 or end <= start:
        return []
    body=ddl[start+1:end]; parts=[]; current=[]; depth=0; quote_char=None
    for char in body:
        if quote_char:
            current.append(char)
            if char==quote_char: quote_char=None
        elif char in "'\"`":
            quote_char=char; current.append(char)
        elif char=="(": depth+=1; current.append(char)
        elif char==")": depth=max(0,depth-1); current.append(char)
        elif char=="," and depth==0:
            parts.append("".join(current).strip()); current=[]
        else: current.append(char)
    if current: parts.append("".join(current).strip())
    return parts


def _ddl_summary(ddl: str) -> dict[str, Any]:
    """PURPOSE: Parse enough original DDL to cross-check PRAGMA names, types and PK declarations.
    INPUT: sqlite_master CREATE TABLE statement.
    OUTPUT: Column declared types and table/inline primary-key columns; not used as authority.
    """
    columns={}; inline_pk=[]; table_pk=[]
    constraints={"PRIMARY","FOREIGN","UNIQUE","CHECK","CONSTRAINT"}
    for part in _ddl_parts(ddl):
        tokens=part.replace("\n"," ").split()
        if not tokens: continue
        head=tokens[0].strip('"`[]').upper()
        if head in constraints:
            match=__import__('re').search(r"PRIMARY\s+KEY\s*\(([^)]+)\)",part,__import__('re').I)
            if match: table_pk=[item.strip().strip('"`[]') for item in match.group(1).split(',')]
            continue
        name=tokens[0].strip('"`[]'); type_tokens=[]
        for token in tokens[1:]:
            if token.upper() in {"PRIMARY","NOT","NULL","UNIQUE","CHECK","REFERENCES","DEFAULT","COLLATE","GENERATED"}: break
            type_tokens.append(token)
        columns[name]=" ".join(type_tokens).strip('"')
        if __import__('re').search(r"\bPRIMARY\s+KEY\b",part,__import__('re').I): inline_pk.append(name)
    return {"columns":columns,"primary_key":table_pk or inline_pk}


def _sqlite_affinity(declared_type: str) -> str:
    """PURPOSE: Compare DB and DD types using SQLite's declared-type affinity rules.
    INPUT: Physical or Data Dictionary type declaration.
    OUTPUT: INTEGER, TEXT, BLOB, REAL or NUMERIC affinity.
    """
    value = str(declared_type or "").upper()
    if "INT" in value:
        return "INTEGER"
    if any(token in value for token in ("CHAR", "CLOB", "TEXT")):
        return "TEXT"
    if not value or "BLOB" in value:
        return "BLOB"
    if any(token in value for token in ("REAL", "FLOA", "DOUB")):
        return "REAL"
    return "NUMERIC"


def load_inputs(db_path: Path, dd_path: Path) -> tuple[list[Table], dict[str, Any], list[dict[str, Any]]]:
    """PURPOSE: Read schema from SQLite itself and normalize the JSON Data Dictionary.
    INPUT: Paths to database.sqlite and data_dictionary.json; no sibling files are inspected.
    OUTPUT: Physical tables, normalized DD and DDL/PRAGMA warnings.
    """
    db_path, dd_path = require_public_path(db_path), require_public_path(dd_path)
    if not db_path.is_file() or not dd_path.is_file():
        raise FileNotFoundError("DBU requires database.sqlite and data_dictionary.json")
    raw_dd = json.loads(dd_path.read_text(encoding="utf-8"))
    normalized_dd = normalize_dictionary(raw_dd)
    tables, warnings = read_physical_schema(db_path, normalized_dd)
    return tables, normalized_dd, warnings


def read_physical_schema(db_path, normalized_dd, *, table_names=None):
    """PURPOSE: Inspect SQLite schema for discovery or bounded source recovery.
    INPUT: Public SQLite path, normalized DD, and optional specific physical table names.
    OUTPUT: Physical tables and DDL/SQLite metadata discrepancies; no row reads.
    """
    dd_columns = {(item["table"], item["column"]): item
                  for item in normalized_dd.get("columns", [])}
    warnings: list[dict[str, Any]] = []
    connection = connect_readonly(db_path)
    try:
        restriction = "" if table_names is None else " AND name IN (SELECT value FROM json_each(?))"
        query = "SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        args = () if table_names is None else (json.dumps(sorted(table_names)),)
        rows = connection.execute(query + restriction + " ORDER BY name", args).fetchall()
        tables = []
        for name, ddl in rows:
            pragma = list(connection.execute(f"PRAGMA table_info({quote_identifier(name)})"))
            parsed = _ddl_summary(ddl or "")
            pragma_names = [row[1] for row in pragma]
            if list(parsed["columns"]) != pragma_names:
                warnings.append({"table":name,"kind":"ddl_pragma_columns_mismatch",
                                 "ddl":list(parsed["columns"]),"pragma":pragma_names,"authority":"pragma"})
            for row in pragma:
                parsed_type = parsed["columns"].get(row[1], "")
                if parsed_type.casefold() != str(row[2] or "").casefold():
                    warnings.append({"table":name,"column":row[1],"kind":"ddl_pragma_type_mismatch",
                                     "ddl":parsed_type,"pragma":row[2] or "","authority":"pragma",
                                     "declared_type_source":"sqlite_master"})
                documented = dd_columns.get((name, row[1]))
                if documented is None or not str(documented.get("type", "")).strip():
                    warnings.append({"table": name, "column": row[1],
                                     "kind": "dd_type_missing", "authority": "database_schema",
                                     "database_type": row[2] or ""})
                elif _sqlite_affinity(documented["type"]) != _sqlite_affinity(row[2] or ""):
                    warnings.append({"table": name, "column": row[1],
                                     "kind": "dd_database_type_affinity_mismatch",
                                     "data_dictionary_type": documented["type"],
                                     "database_type": row[2] or "",
                                     "authority": "database_schema"})
            unique_keys = _unique_keys(connection, name)
            columns = [Column(
                id=f"C:{name}.{row[1]}", name=row[1],
                declared_type=parsed["columns"].get(row[1]) or row[2] or "",
                not_null=bool(row[3]), pk_position=int(row[5]), ordinal=int(row[0]),
                unique=any([row[1]] == key for key in unique_keys)) for row in pragma]
            primary_key = [row[1] for row in sorted(pragma, key=lambda item: item[5]) if row[5]]
            if parsed["primary_key"] != primary_key:
                warnings.append({"table":name,"kind":"ddl_pragma_pk_mismatch",
                                 "ddl":parsed["primary_key"],"pragma":primary_key,"authority":"pragma"})
            tables.append(Table(
                id=f"T:{name}", name=name, ddl=ddl or "", columns=columns,
                primary_key=primary_key, unique_keys=unique_keys,
                foreign_keys=declared_foreign_key_groups(connection, name)))
        return tables, warnings
    finally:
        connection.close()
