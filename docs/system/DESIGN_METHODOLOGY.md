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

- WarehouseFlow starts from one actual RSchema requirement and logical schema; UniversityFlow combines three university examples.
- Both retain each source table role, attribute and declared key relationship. UniversityFlow merges overlapping Student tables and fields; this integration is explicitly documented.
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

- Combine course-registration, course-design and assignment-management examples from RSchema.
- Merge the three Student tables by Student ID, including their overlapping Name and Class fields.
- The 13 original table definitions become 11 combined tables; 60 original attribute definitions become 55 distinct columns.
- All source primary keys and nine distinct foreign-key relationships are retained; no new table, column or foreign key is invented.
- Shared student identity across separate source examples is an integration assumption.
- Five event types are recorded: examinations, registrations, assignment grading, simulation-experiment completion and thesis submission.
- Grading times are linked to student cases through assignment records.
- Composite grading and experiment keys preserve regrading and repeated runs.
- Planned task dates and teaching schedules are excluded from observed-event timelines.
- Student timelines include all linked academic actions without asserting a single course or causal chain.
- Notification, withdrawal and assignment-submission questions are unsupported because their times are absent.
- UTC times, a passing score of 60 and academic action order are simulation assumptions.

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

## Alternative case notions

- Each usable keyed table has a question with an explicit case and event-scope rule.
- Object timelines, association-record timelines and single-event record timelines are identified separately.
- Candidate scope is not all graph-reachable events: it follows the documented business association for that view.
- Expected events come from the simulated history and explicit event-to-case links reconstructed from object identities and declared associations.
- SQL uses an event-source query and an event-to-case mapping, rather than an uncontrolled join across every detail table.
- A shared event can belong to several cases; uniqueness is checked for each `(case_id, event_id)` pair.
- Case-population queries include objects with no selected events.
- Unsupported task-execution and reference-code cases are documented instead of inventing timestamps.
- This expands case selection tests while retaining the existing task catalog and dataset-specific extraction-specification limitation.
