"""Check business dictionary completeness, actual schema and input-answer boundaries."""
from pathlib import Path
import csv
from datetime import datetime
import hashlib
import json
import re
import sys

P = Path(__file__).resolve().parent
sys.path.insert(0, str(P.parents[1]))
from hospital_dictionary import artifacts, validate_schema

def main():
    dictionary = json.loads((P / "input/data_dictionary.json").read_text())
    profile = json.loads((P / "source/dictionary_profile.json").read_text())
    assert dictionary == profile
    assert len(dictionary["tables"]) == 11
    assert sum(len(t["columns"]) for t in dictionary["tables"]) == 50
    validate_schema(P / "input/database.sqlite", dictionary)
    forbidden = {"event_encoding", "encoding_detail", "carrier_column", "is_event_table",
                 "event_timestamp_columns", "activity_sources", "event_bindings",
                 "compiled_sql", "timestamp_summary", "object_activity_design",
                 "requested_activity_count", "extractable_activity_count"}
    def inspect(value):
        if isinstance(value, dict):
            assert not forbidden.intersection(value)
            for child in value.values():
                inspect(child)
        elif isinstance(value, list):
            for child in value:
                inspect(child)
    inspect(dictionary)
    doc, table_rows, column_rows, basic = artifacts(dictionary)
    for path in ["input/data_dictionary.md", "docs/data_dictionary.md"]:
        assert (P / path).read_text() == doc, path
    assert json.loads((P / "docs/dictionary_basic_information.json").read_text()) == basic
    for filename, rows in [("table_definitions.csv", table_rows), ("data_dictionary.csv", column_rows)]:
        with (P / "docs" / filename).open(newline="") as stream:
            actual = list(csv.DictReader(stream))
        expected = [{key: str(value) for key, value in row.items()} for row in rows]
        assert actual == expected, filename
    assert len(column_rows) == 50
    banned = re.compile(r"row[ _-]+encoding|column[ _-]+encoding|mixed[ _-]+encoding|carrier_column|event_bindings|used_as_event_time|compiled_sql", re.I)
    files = ["input/data_dictionary.json", "input/data_dictionary.md",
             "docs/data_dictionary.md", "docs/data_dictionary.csv",
             "docs/table_definitions.csv", "docs/dictionary_basic_information.json"]
    for path in files:
        assert not banned.search((P / path).read_text()), path
    manifest = json.loads((P / "input/model_input_manifest.json").read_text())
    assert set(manifest["paths"]) == {"input/database.sqlite", "input/schema.sql",
                                     "input/data_dictionary.json", "input/model_questions.jsonl"}
    import sqlite3
    con = sqlite3.connect("file:" + str((P / "input/database.sqlite").resolve()) + "?mode=ro", uri=True)
    assert not list(con.execute("PRAGMA foreign_key_check"))
    datetime_count = 0
    enum_count = 0
    for table in dictionary["tables"]:
        for col in table["columns"]:
            for field in ["name", "readable_name", "definition", "unit", "allowed_values",
                          "nullable", "null_meaning", "format", "source_references", "synonyms"]:
                assert field in col
            assert col["readable_name"] and col["definition"] and col["allowed_values"]
            if col["allowed_codes"]:
                values = {row[0] for row in con.execute("SELECT DISTINCT " + col["name"] + " FROM " + table["table"] + " WHERE " + col["name"] + " IS NOT NULL")}
                assert values.issubset(set(col["allowed_codes"]))
                assert set(col["allowed_codes"]) == set(col["code_meanings"])
                enum_count += 1
            if col["representation_class"] == "Date-time":
                assert col["timezone"] == "UTC"
                for row in con.execute("SELECT " + col["name"] + " FROM " + table["table"] + " WHERE " + col["name"] + " IS NOT NULL"):
                    value = row[0]
                    assert value.endswith("Z")
                    instant = datetime.fromisoformat(value.replace("Z", "+00:00"))
                    assert instant.microsecond == 0
                datetime_count += 1
    assert datetime_count == 19 and enum_count == 4
    assert not list(con.execute("PRAGMA foreign_key_list(patient_profile)"))
    profile_table = next(t for t in dictionary["tables"] if t["table"] == "patient_profile")
    assert profile_table["foreign_keys"] == [] and len(profile_table["logical_relationships"]) == 1
    con.close()
    before = {path: (P / path).read_bytes() for path in files}
    db_hash = hashlib.sha256((P / "input/database.sqlite").read_bytes()).hexdigest()
    from event_encoding import annotate
    from dictionary_standard import render
    annotate(P)
    render(P)
    assert before == {path: (P / path).read_bytes() for path in files}
    assert db_hash == hashlib.sha256((P / "input/database.sqlite").read_bytes()).hexdigest()
    print("HospitalFlow dictionary: 11 tables, 50 variables, 19 datetime variables and 4 coded variables; schema/artifacts/input boundaries verified.")

if __name__ == "__main__":
    main()
