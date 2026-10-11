# NL2EventLog Synthetic Development Benchmarks

Two independent, English-language relational database fixtures for developing
natural-language event-log extraction. Each includes a populated SQLite DB,
data dictionary, questions, Gold Process View/ES/logs, SQL and reproducible code.

| Dataset | Source foundation | Tables | Main cases | Events | Questions |
|---|---|---:|---:|---:|---:|
| [WarehouseFlow](datasets/warehouseflow/README.md) | Actual RSchema requirement and logical schema | 6 | 4 warehouses | 80 | 7 |
| [PlateFlow v2](datasets/plateflow/README.md) | Selected POSCO table/column definitions | 9 | 36 mother materials, 39 descendant pieces | 324 | 8 |

These are development fixtures. Exact SQL/gold consistency is validated;
NL2EventLog model accuracy and held-out generalization have not been evaluated.

## Database schemas

### WarehouseFlow: six tables

![WarehouseFlow ERD](datasets/warehouseflow/docs/schema.png)

[Table inventory](datasets/warehouseflow/docs/schema_overview.md) ·
[English data dictionary](datasets/warehouseflow/docs/data_dictionary.md) ·
[Editable draw.io](datasets/warehouseflow/docs/schema.drawio)

### PlateFlow v2: nine tables

![PlateFlow ERD](datasets/plateflow/docs/schema.png)

[Table inventory](datasets/plateflow/docs/schema_overview.md) ·
[English data dictionary](datasets/plateflow/docs/data_dictionary.md) ·
[Editable draw.io](datasets/plateflow/docs/schema.drawio)

## Reproduce the datasets

Python 3.10 or later; dataset builders use only the standard library:

    python datasets/warehouseflow/build.py
    python datasets/plateflow/build.py

Each builder recreates generated DB/gold artifacts and fails on its validation
checks. The diagram/documentation generator additionally requires PyMuPDF:

    pip install PyMuPDF
    python make_docs.py

Generated diagram files and documentation are already included, so this extra
dependency is unnecessary for reading documentation or rebuilding datasets.

## Design approach

See [DESIGN_METHODOLOGY.md](DESIGN_METHODOLOGY.md) for requirements, conceptual,
logical and physical design, process simulation, adaptation boundaries and
evaluation rules. The staged design approach follows the database-design
distinctions discussed in SchemaAgent Section 2.1; it does not claim a new
schema-generation framework or require a multi-agent implementation.

## Repository layout

- datasets/warehouseflow/: source-preserving RSchema warehouse fixture.
- datasets/plateflow/: POSCO-schema-informed plate manufacturing fixture.
- Each input/: model inputs (DB, dictionary, schema, questions and task catalog).
- Each private/: evaluator-only canonical history, gold ES, SQL and event logs.
- Each design/: modeling and source/adaptation documentation.
- Each docs/: table inventories, Markdown/CSV dictionaries, PNG/SVG/draw.io ERDs.
- Each validation_report.json: actual validation results.

The folder name private denotes evaluator separation, not GitHub access
control. In a public repository these files remain publicly visible. When
evaluating a model, expose only input/ and withhold the generator, source gold
annotation, design and private folders from its context.

## Opening draw.io diagrams

At https://app.diagrams.net choose File → Open from → Device and select
the downloaded schema.drawio file. Table boxes, columns, relationship labels
and edges are editable. Solid edges are declared SQLite foreign keys; dashed
edges are logical multi-domain material references. PNG/SVG diagrams provide
immediate previews; Markdown tables specify exact endpoints and cardinalities.

## Provenance

WarehouseFlow uses record 67552f0a13602ec03b41a78e from
[RSchema](https://github.com/hnuGraph/LLM4DBdesign), pinned to commit
5eda099db3d9b768e5b532b5abc9f8fe117be85f. The original requirement, schema,
identifier mapping and repairs are included.

PlateFlow uses a selected subset of the supplied POSCO metadata. Original
production rows and the complete proprietary metadata CSV are not included.
Its English source mappings retain original identifiers for traceability.
Types, keys, code values, cardinalities and process rules are authored
synthetic assumptions, explicitly documented.

SchemaAgent reference: Wang et al., *SchemaAgent: A Multi-Agents Framework
for Generating Relational Database Schema*, arXiv:2503.23886v1 (2025).
The corresponding source files retain their upstream provenance.
