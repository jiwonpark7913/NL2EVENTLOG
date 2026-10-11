# How the datasets are constructed

## Database design stages

- SchemaAgent Section 2.1 distinguishes conceptual modeling from the design of relational tables.
- We use these design stages to document our decisions and validation checks.
- We do not implement the related-work algorithms listed in that section.

| Stage | Main decision | Files |
|---|---|---|
| Requirements | Which entities and actions the system needs to record | requirements.md and original source requirement |
| Conceptual model | Entity roles, relationships and what counts as one event | conceptual_model.json |
| Relational schema | Tables, columns, primary keys and foreign keys | logical_schema.json |
| Executable schema | SQLite types, required values and constraints | schema.sql |
| Data definitions | English meanings of columns, codes and business rules | data_dictionary.json/md and docs/ |
| Simulation | Generate consistent business actions with stable event IDs | canonical_history.jsonl |
| Database generation | Write the simulated information into relational tables | database.sqlite |
| Expected answers | Select the requested events and define their extraction rules | questions and private/ |
| Validation | Execute extraction SQL and compare with expected logs | validation_report.json |

## What is reused and what is added

- WarehouseFlow and UniversityFlow each start from an actual RSchema requirement and logical schema.
- Both retain every original table, column, primary key and foreign-key relationship in the selected record.
- Their conceptual models are documented locally; upstream conceptual diagrams are not assumed to exist.
- PlateFlow starts from selected table and column definitions supplied by a Korean manufacturing company.
- Those manufacturing definitions do not declare SQL types, primary keys, foreign keys, process-code meanings or relationship counts.
- PlateFlow therefore specifies those details as simulation assumptions.
- All datasets document added timestamp meanings, data types, checks, code meanings and process rules.
- No ISO compliance claim is made.

## WarehouseFlow

- Six original tables and 17 columns are retained.
- Warehouses define cases; receiving and dispatching tasks define events.
- Goods details and worker assignments describe a task and are not additional events.
- Joining both detail tables produces 289 rows for 80 tasks in this example.
- Expected extraction keeps one event per task.

## UniversityFlow

- Four original tables, 21 columns and three foreign-key relationships are retained.
- Students define cases; examinations and course registrations define events.
- Examination results use unique result IDs so retakes remain separate records.
- Registrations use the original student-course composite key, which retains one registration per pair.
- Students with no events remain in the case population.
- Notification and withdrawal questions are unsupported because their event times are absent.
- UTC times and a passing score of 60 are documented simulation assumptions.

## PlateFlow

- Planned instructions, released instructions, furnace tracking, mother materials, cutting instructions, cut pieces and operation history remain separate records.
- A new process-code table explains the synthetic operation codes.
- Each mother material can produce several cut pieces.
- A mother's timeline includes its own events and the events of its cut pieces, each once.
- Joining every mother event to every cut piece would duplicate the mother events.
- Rolling completion comes from the rolling-operation history, not from the material's latest-operation time.

## What validation establishes

- Each answerable question has an expected log selected from simulated business history.
- A separate extraction path uses the expected specification to generate and execute SQL.
- Both paths share authored business assumptions; their agreement establishes internal consistency.
- It does not establish independently verified real-world correctness, model accuracy or performance on unseen databases.
- Paraphrase pairs test different wording for the same requested process scope.
- An unsupported question is different from a valid question with no observed events.
- Evaluation inputs include a task scope catalog containing business labels and the default scope rule.
- Extraction specifications currently use dataset-specific formats; integration with the existing NL2EventLog implementation remains to be tested.
