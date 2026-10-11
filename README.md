# NL2EventLog Synthetic Development Datasets

- Three independent, English-language relational databases support development of natural-language event-log extraction.
- Each dataset includes a populated SQLite database, data definitions, questions, expected answers, extraction SQL and reproducible generation code.
- The examples below are ordered from warehouse operations to university academic activities to plate manufacturing.

| Dataset | Source used | Tables | Cases | Business events | Questions |
|---|---|---:|---|---:|---:|
| [WarehouseFlow](datasets/warehouseflow/README.md) | Actual RSchema requirement and logical schema | 6 | 4 warehouses | 80 | 7 |
| [UniversityFlow](datasets/universityflow/README.md) | Three actual RSchema university requirements and logical schemas, combined through student identity | 11 | 40 students | 148 | 15 |
| [PlateFlow](datasets/plateflow/README.md) | Selected table and column definitions from a Korean manufacturing company | 9 | 36 mother materials, linked to 39 cut pieces | 324 | 8 |

- SQL results match the expected logs for all answerable questions.
- This verifies internal consistency of the datasets; it does not measure NL2EventLog model accuracy or performance on unseen databases.

## Terms used in this repository

- **Case:** the entity whose timeline is requested, such as a student or warehouse.
- **Event:** one recorded business action with a time, such as a course registration.
- **Data dictionary:** a document explaining each table, column, code and business rule.
- **Expected answer (Gold):** the reference answer used to evaluate a question.
- **Process View:** the requested case type and business activities.
- **Extraction Specification (ES):** the tables, columns and rules used to extract those events.
- **Simulated history:** the business events generated before they are written into the database; the corresponding file is `canonical_history.jsonl`.
- **Task scope catalog:** the allowed business activities and a default rule for requests such as “show the full timeline.”
- File names and JSON field names are kept stable so existing scripts can still read them.

## WarehouseFlow — six tables

![WarehouseFlow schema](datasets/warehouseflow/docs/schema.png)

- [Dataset explanation](datasets/warehouseflow/README.md)
- [Tables and relationships](datasets/warehouseflow/docs/schema_overview.md)
- [Data definitions](datasets/warehouseflow/docs/data_dictionary.md)
- [Editable draw.io diagram](datasets/warehouseflow/docs/schema.drawio)

## UniversityFlow — eleven tables

![UniversityFlow schema](datasets/universityflow/docs/schema.png)

- [Dataset explanation](datasets/universityflow/README.md)
- [Tables and relationships](datasets/universityflow/docs/schema_overview.md)
- [Data definitions](datasets/universityflow/docs/data_dictionary.md)
- [Editable draw.io diagram](datasets/universityflow/docs/schema.drawio)

## PlateFlow — nine tables

![PlateFlow schema](datasets/plateflow/docs/schema.png)

- [Dataset explanation](datasets/plateflow/README.md)
- [Tables and relationships](datasets/plateflow/docs/schema_overview.md)
- [Data definitions](datasets/plateflow/docs/data_dictionary.md)
- [Editable draw.io diagram](datasets/plateflow/docs/schema.drawio)

## Rebuild the datasets

- Use Python 3.10 or later.
- Dataset builders use only Python's standard library.
- Run the commands below from the repository root.
- Each command recreates its generated files and runs the dataset's validation checks.

```bash
python datasets/warehouseflow/build.py
python datasets/universityflow/build.py
python datasets/plateflow/build.py
```

- Diagrams and documentation are already included.
- To regenerate them, install PyMuPDF and run the following commands.

```bash
pip install PyMuPDF
python make_docs.py
```

## Folders and evaluation inputs

- `datasets/warehouseflow/`: warehouse receiving and dispatching.
- `datasets/universityflow/`: examinations, course registrations, grading, simulation experiments and thesis submissions.
- `datasets/plateflow/`: plate manufacturing based on selected enterprise table definitions.
- Each `input/`: database, schema, data dictionary, questions and task scope catalog supplied to the model.
- Each `private/`: simulated history and expected process scopes, extraction specifications, SQL and logs used for evaluation.
- Each `design/`: design decisions, source mappings and added assumptions.
- Each `docs/`: table lists, data definitions and schema diagrams.
- Each `validation_report.json`: the checks actually run and their results.
- `private/` is a folder name, not an access-control setting.
- During evaluation, give the model only `input/`; keep generation code, source answers, design files and expected results outside its context.
- The supplied task scope catalog makes this an evaluation with a predefined scope catalog.

## Open the diagrams

- Download a dataset's `schema.drawio` file.
- At [diagrams.net](https://app.diagrams.net), choose **File → Open from → Device** and select the file.
- Table boxes, columns and relationships are editable.
- Solid arrows show declared foreign keys.
- Dashed arrows in PlateFlow show material IDs that can refer to either a mother material or a cut piece.
- PNG files provide previews; the data-definition tables specify the exact keys and relationships.

## Sources and construction method

- WarehouseFlow uses RSchema record `67552f0a13602ec03b41a78e`.
- UniversityFlow combines RSchema records `67552f0b13602ec03b41aaec`, `67552f0b13602ec03b41aa43` and `67552f0b13602ec03b41ab04` through an authored shared student identity.
- Both use [hnuGraph/LLM4DBdesign](https://github.com/hnuGraph/LLM4DBdesign), commit `5eda099db3d9b768e5b532b5abc9f8fe117be85f`.
- Original requirements and schema annotations are included with their source references.
- PlateFlow uses selected metadata from a Korean manufacturing company.
- The full enterprise metadata file and real production records are excluded.
- Original table and column identifiers are retained only to show how the selected definitions map to the synthetic database.
- Data types, keys, process codes and manufacturing rules added for PlateFlow are documented as simulation assumptions.
- SchemaAgent reference: Wang et al., *SchemaAgent: A Multi-Agents Framework for Generating Relational Database Schema*, arXiv:2503.23886v1 (2025).
- [Construction method](DESIGN_METHODOLOGY.md) explains the design stages and validation boundaries.
