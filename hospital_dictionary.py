"""HospitalFlow business dictionary renderer; classification and Gold answers are excluded."""
from pathlib import Path
import csv
import json
import re
import sqlite3
import copy

def _json(value):
    return json.dumps(value, indent=2) + "\n"

def _table(headers, rows):
    def esc(value):
        return str(value).replace("|", r"\|").replace("\n", " ")
    return "| " + " | ".join(headers) + " |\n| " + " | ".join("---" for _ in headers) + " |\n" + "".join("| " + " | ".join(esc(v) for v in row) + " |\n" for row in rows)

def _fk(column):
    return "; ".join(f["table"] + "." + f["column"] for f in column["foreign_keys"]) or "None declared"

def _domain(column):
    meanings = column["code_meanings"]
    if meanings:
        return "; ".join(code + " = " + meaning for code, meaning in meanings.items())
    return column["allowed_values"]

def _format(column):
    return column["format"] + ("; timezone " + column["timezone"] if column["timezone"] else "")

def _logical(table):
    return "; ".join(",".join(r["columns"]) + " -> " + r["referenced_table"] + "(" + ",".join(r["referenced_columns"]) + "): " + r["enforcement"] for r in table["logical_relationships"]) or "None additionally documented"

def model_dictionary(profile):
    dictionary = copy.deepcopy(profile)
    dictionary.pop("documentation_basis", None)
    keep = {"dictionary_id", "name", "version", "language", "dbms", "timezone", "datetime_representation"}
    dictionary["dictionary_basic_information"] = {k: v for k, v in dictionary["dictionary_basic_information"].items() if k in keep}
    dictionary["dictionary_basic_information"]["datetime_representation"] = "RFC 3339 UTC text, YYYY-MM-DDTHH:MM:SSZ"
    return dictionary

def artifacts(dictionary):
    basic = dictionary["dictionary_basic_information"]
    table_rows = []
    column_rows = []
    for table in dictionary["tables"]:
        table_rows.append(dict(
            metadata_id=table["metadata_id"], table=table["table"],
            readable_name=table["readable_name"], definition=table["definition"],
            row_grain=table["row_grain"], primary_key=", ".join(table["primary_key"]),
            foreign_keys="; ".join(f["column"] + " -> " + f["parent_table"] + "." + f["parent_column"] for f in table["foreign_keys"]) or "None declared",
            logical_relationships=_logical(table),
            declared_checks="; ".join(table["table_checks"]) or "None at table level",
            sql_definition=table["sql_definition"], constraint_notes="; ".join(table.get("constraint_notes", []))))
        for ordinal, column in enumerate(table["columns"], 1):
            column_rows.append(dict(
                metadata_id=column["metadata_id"], table=table["table"], ordinal=ordinal,
                variable_name=column["name"], readable_name=column["readable_name"],
                definition=column["definition"], sql_type=column["type"],
                representation=column["representation_class"], unit=column["unit"],
                format=column["format"], timezone=column["timezone"] or "Not applicable",
                allowed_values=_domain(column), minimum="Not declared" if column["minimum"] is None else column["minimum"], maximum="Not declared" if column["maximum"] is None else column["maximum"],
                value_domain_basis=column["value_domain_basis"],
                nullable="yes" if column["nullable"] else "no", null_meaning=column["null_meaning"],
                primary_key_position=column["primary_key_position"] or "",
                foreign_key=_fk(column), unique="yes" if column["unique"] else "no",
                default="No SQL default" if column["default_value"] is None else column["default_value"],
                length=column["length"], declared_constraints=column["constraints"],
                synonyms="; ".join(column["synonyms"]) or "None supplied",
                description=column["description"],
                source_references="; ".join(column["source_references"])))
    doc = "# HospitalFlow — business data dictionary\n\n## 1. Dictionary basic information\n\n"
    doc += _table(["Field", "Value"], basic.items())
    doc += "\n## 2. Table definitions\n\n"
    doc += _table(["Table", "Readable name", "One row represents", "Primary key", "Declared SQL foreign keys"],
                  [[t["table"], t["readable_name"], t["row_grain"], ", ".join(t["primary_key"]),
                    "; ".join(f["column"] + " -> " + f["parent_table"] + "." + f["parent_column"] for f in t["foreign_keys"]) or "None declared"] for t in dictionary["tables"]])
    doc += "\n## 3. Column definitions\n"
    for table in dictionary["tables"]:
        doc += "\n### " + table["table"] + " — " + table["readable_name"] + "\n\n"
        doc += "- **Business definition:** " + table["definition"] + "\n"
        doc += "- **One row represents:** " + table["row_grain"] + "\n"
        doc += "- **Additional documented relationships:** " + _logical(table) + "\n\n"
        doc += _table(["Variable name", "Readable name", "Definition", "Measurement unit", "Allowed values / code meanings", "NULL meaning", "Format / timezone"],
                      [[c["name"], c["readable_name"], c["definition"], c["unit"], _domain(c), c["null_meaning"], _format(c)] for c in table["columns"]])
        doc += "\n**Storage and declared constraints**\n\n"
        doc += _table(["Variable", "SQL type", "Required", "PK position", "Declared FK", "Unique", "Default", "Column constraints"],
                      [[c["name"], c["type"], "no" if c["nullable"] else "yes", c["primary_key_position"] or "", _fk(c), "yes" if c["unique"] else "no", "No SQL default" if c["default_value"] is None else c["default_value"], c["constraints"]] for c in table["columns"]])
        for column in table["columns"]:
            if column["description"]:
                doc += "\n- **" + column["name"] + ":** " + column["description"] + "\n"
            if column["synonyms"]:
                doc += "\n- **" + column["name"] + " synonyms:** " + ", ".join(column["synonyms"]) + "\n"
        refs = sorted({r for c in table["columns"] for r in c["source_references"] if r.startswith("https://")})
        if refs:
            doc += "\n- **Definition references:** " + "; ".join("[" + r + "](" + r + ")" for r in refs) + ".\n"
        doc += "".join("\n- **Constraint interpretation:** " + note + "\n" for note in table.get("constraint_notes", []))
        doc += "\n" + chr(96)*3 + "sql\n" + table["sql_definition"] + ";\n" + chr(96)*3 + "\n"
    doc += "\n### Cross-table business conventions\n\n"
    doc += "".join("- " + rule + "\n" for rule in dictionary["business_rules"])
    return doc, table_rows, column_rows, basic

def validate_schema(path, dictionary):
    con = sqlite3.connect("file:" + str(Path(path).resolve()) + "?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        names = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
        if names != {t["table"] for t in dictionary["tables"]}:
            raise ValueError("Dictionary table inventory differs from DB; review the source dictionary profile")
        for table in dictionary["tables"]:
            name = table["table"]
            actual = list(con.execute("PRAGMA table_info(" + name + ")"))
            if [r["name"] for r in actual] != [c["name"] for c in table["columns"]]:
                raise ValueError("Column inventory differs: " + name)
            primary = [r["name"] for r in sorted(actual, key=lambda r: r["pk"]) if r["pk"]]
            if primary != table["primary_key"]:
                raise ValueError("Primary key differs: " + name)
            actual_fk = sorted((r["from"], r["table"], r["to"]) for r in con.execute("PRAGMA foreign_key_list(" + name + ")"))
            expected_fk = sorted((r["column"], r["parent_table"], r["parent_column"]) for r in table["foreign_keys"])
            if actual_fk != expected_fk:
                raise ValueError("Foreign keys differ: " + name)
            for row, col in zip(actual, table["columns"]):
                if row["type"] != col["type"] or bool(row["notnull"] or row["pk"]) == col["nullable"] or row["pk"] != col["primary_key_position"] or row["dflt_value"] != col["default_value"]:
                    raise ValueError("Storage metadata differs: " + name + "." + col["name"])
            ddl = con.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone()[0]
            if ddl.strip().rstrip(";") != table["sql_definition"].strip().rstrip(";"):
                raise ValueError("Declared constraints differ: " + name)
    finally:
        con.close()

def render(p):
    p = Path(p)
    dictionary = model_dictionary(json.loads((p / "source/dictionary_profile.json").read_text()))
    validate_schema(p / "input/database.sqlite", dictionary)
    doc, tables, columns, basic = artifacts(dictionary)
    (p / "input/data_dictionary.json").write_text(_json(dictionary))
    for name in ["input/data_dictionary.md", "docs/data_dictionary.md"]:
        (p / name).write_text(doc)
    for name, rows in [("table_definitions.csv", tables), ("data_dictionary.csv", columns)]:
        with (p / "docs" / name).open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    (p / "docs/dictionary_basic_information.json").write_text(_json(basic))
    from hospital_ablation import render as render_ablation
    render_ablation(p, dictionary)
    return dictionary

if __name__ == "__main__":
    import sys
    render(Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent / "datasets/hospitalflow")
