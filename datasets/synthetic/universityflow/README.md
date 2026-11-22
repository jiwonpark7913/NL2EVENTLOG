# UniversityFlow

Follow student, course and assessment histories across registration, examinations, grading, theses and simulation experiments. Use this benchmark to compare a requested case history with its independently stored SQL and event log.

| Tables | Source rows | Requests | Gold event logs |
|---:|---:|---:|---:|
| 11 | 230 | 70 | 66 |

## Origin and construction

The project adapts three RSchema university requirements and generates the academic records, lifecycle events and cross-table identities. [Pinned source records](source/provenance.json) · [Adaptation report](design/adaptation_report.json) · [Generator](build.py)

## Relational schema and inputs

![UniversityFlow tables and declared foreign keys](review/database/schema.svg)

[Editable ERD](docs/schema.drawio) · [Table sizes, columns and sample rows](review/database/README.md#table-inspector) · [Data dictionary](input/data_dictionary.json) · [SQLite database](input/database.sqlite)

## Questions and evaluation

Start with **U01** to inspect degree examinations for each student.

| Task | Open |
|---|---|
| Choose a request and check its scope | [Question list, types and answerability](docs/questions.md) · [Annotated requests](evaluation/questions.jsonl) (supply only the request text to the model) |
| Inspect the expected result for U01 | [Extraction SQL](private/gold_sql/U01.sql) · [Event log CSV](private/gold_logs/U01.csv) |
| Review a trace and its evidence | [Gold review page](review/gold_dfg/README.md) with per-request DFGs and original table rows. Download the linked HTML and open it locally. |
| Inspect how the authors attributed activities | [Source projection diagram](review/database/gold_evidence_graph.svg) · [Source inventory](review/gold_dfg/event_graph.md) |
| Understand the inferred EEG | [EEG specification](../../../docs/system/EEG_ENTITY_MODEL.md). This dataset has no checked-in runtime EEG. The source projection above uses author annotations. |

## Files by role

| Folder | Contents |
|---|---|
| [input/](input/) | SQLite database and business dictionary for the model |
| [evaluation/](evaluation/) | Requests and evaluation metadata |
| [private/](private/) | Reference SQL, event logs and construction evidence for scoring |
| [review/](review/) | Human-readable database and Gold inspection pages |
| [source/](source/) · [design/](design/) · [docs/](docs/) | Source material, modeling decisions and schema or question documentation |

[Domain-generated datasets](../) · [All datasets](../../)
