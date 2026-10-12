# WarehouseFlow

- **Situation:** Goods enter a warehouse and complete inspection and putaway, or leave through approval, picking, packing and dispatch. Goods and workers are linked to each transaction.
- **Source:** One preserved RSchema warehouse requirement and logical schema. Original source columns and keys are preserved.
- **Extension:** New activity histories, timestamps and cross-object attribution rules are authored synthetic domain design. They are not copied from the source or observed production data.
- **Database:** 8 tables; 10 activity types; 6 object / case types; 394 distinct recorded business events.
- **Gold:** 30 answerable question-specific CSV logs out of 32 questions. Paired requests share the same expected content.
- **Execution:** Run `python datasets/warehouseflow/build.py` from the repository root, then `python make_docs.py`. Only the Python standard library is needed for DB/log generation; diagrams use PyMuPDF.

## Dataset counts

| Dataset | Tables | Object / case types | Activity types | Distinct events | Questions | Gold CSVs |
|---|---:|---:|---:|---:|---:|---:|
| WarehouseFlow | 8 | 6 | 10 | 394 | 32 | 30 |

- **Activity types:** distinct business labels across all recorded events in this database, counted once even when shared by several objects.
- **Object / case types:** distinct keyed tables with an answerable object-specific event log, including auxiliary event/association-record cases. This is a type count, not a count of individual object instances.
- Activity-history tables, the case-link index and code reference tables do not add object types.
- Individual cases may contain fewer activities because of incomplete work or conditional branches.

## Objects, activities and situations

| Object / case | Activity types observed across all instances of this case type | Situation / scope | Gold CSV |
|---|---|---|---|
| warehouse | Dispatch Approved; Dispatch Requested; Goods Dispatched; Goods Packed; Goods Picked; Goods Put Away; Goods Received; Receiving Inspection Completed; Receiving Requested; Receiving Scheduled | Original recorded actions and authored lifecycle actions explicitly linked to this warehouse. | [CSV](private/gold_logs/OW01.csv) |
| goods | Dispatch Approved; Dispatch Requested; Goods Dispatched; Goods Packed; Goods Picked; Goods Put Away; Goods Received; Receiving Inspection Completed; Receiving Requested; Receiving Scheduled | Original recorded actions and authored lifecycle actions explicitly linked to this goods. | [CSV](private/gold_logs/OW02.csv) |
| loader | Dispatch Approved; Dispatch Requested; Goods Dispatched; Goods Packed; Goods Picked; Goods Put Away; Goods Received; Receiving Inspection Completed; Receiving Requested; Receiving Scheduled | Original recorded actions and authored lifecycle actions explicitly linked to this worker. | [CSV](private/gold_logs/OW03.csv) |
| transaction_record | Dispatch Approved; Dispatch Requested; Goods Dispatched; Goods Packed; Goods Picked; Goods Put Away; Goods Received; Receiving Inspection Completed; Receiving Requested; Receiving Scheduled | Original recorded actions and authored lifecycle actions explicitly linked to this warehouse transaction. | [CSV](private/gold_logs/OW04.csv) |
| goods_transaction_detail | Dispatch Approved; Dispatch Requested; Goods Dispatched; Goods Packed; Goods Picked; Goods Put Away; Goods Received; Receiving Inspection Completed; Receiving Requested; Receiving Scheduled | Original recorded actions and authored lifecycle actions explicitly linked to this goods transaction line. | [CSV](private/gold_logs/OW05.csv) |
| loader_transaction | Dispatch Approved; Dispatch Requested; Goods Dispatched; Goods Packed; Goods Picked; Goods Put Away; Goods Received; Receiving Inspection Completed; Receiving Requested; Receiving Scheduled | Original recorded actions and authored lifecycle actions explicitly linked to this worker transaction assignment. | [CSV](private/gold_logs/OW06.csv) |

- Transaction/detail cases group the same warehouse job through its receiving or dispatch stages.
- Atomic grading and operation records are auxiliary cases; a single occurrence is not expanded into an invented lifecycle.
- Master cases can aggregate unrelated jobs. Multiple activity types do not imply one causal process across all rows.
- Conditional revision branches and incomplete histories are intentional. Repeated activity occurrences keep distinct event IDs.
- Actual activity times are separate from plans, schedules and technical creation/update times.
- Case population includes objects with no selected events; those cases have no CSV rows.
- These are case-based CSV logs, not OCEL.

## Database, extraction and validation

- Typed `<object>_activity` tables store `event_id`, parent PK/FK, `activity`, actual `occurred_at` and `outcome`.
- `lifecycle_case_link` is an explicitly validated auxiliary index relating a recorded event to each permitted case. It is not a business object.
- Full ES queries union original milestone sources and new action histories. Object-specific ES queries apply explicit case links and sort by case, time and event ID.
- Gold logs are generated from simulated history and compared against executable SQL on the populated DB. This checks internal consistency, not model accuracy.
- [Detailed activity design](docs/object_activity_design.md)
- [Event-log case scopes and counts](docs/object_event_logs.md)
- [Data dictionary](docs/data_dictionary.md)
- [Schema overview](docs/schema_overview.md)
- [Editable draw.io](docs/schema.drawio)
- [Validation report](validation_report.json)

![Schema](docs/schema.png)

## Question types and pairs

- **Q1 Explicit:** case concept and exact activities.
- **Q2 Paraphrased:** alternate wording of Q1, with identical Gold scope.
- **Q3 Full Lifecycle:** case concept only, using the declared default recorded scope.
- **Q4 Full Lifecycle Paraphrased:** alternate wording of Q3, with identical Gold scope.
- `question_type`, `question_type_name`, `pair_of` and `answerability` are included in every question and Gold answer.
- Type and answerability are separate: unavailable actions remain unsupported; empty observed logs are not automatically unsupported.

| Type | Questions | Answerable | Non-answerable | Avg. requested activity types |
|---|---:|---:|---:|---:|
| Q1 | 9 | 8 | 1 | 2.33 |
| Q2 | 9 | 8 | 1 | 2.33 |
| Q3 | 7 | 7 | 0 | 10.00 |
| Q4 | 7 | 7 | 0 | 10.00 |

- Avg. requested activity types = sum of requested activity-type counts / all questions in that row, including non-answerable questions. Q3/Q4 counts use the Gold catalog scope. This counts distinct activity types, not event occurrences.

- [All question texts, types, pairs and answerability](docs/questions.md)

## Event encoding and data definitions

- [Table-by-table row/column encoding](docs/schema_overview.md)
- [Three-part data dictionary: basic information, table definitions, column definitions](docs/data_dictionary.md)
- [Table definitions CSV](docs/table_definitions.csv)
- Process View includes the case concept and activity scope. Q1/Q2 state the scope explicitly; Q3/Q4 infer it from the declared catalog.
- [Question activity counts and pairs](docs/questions.md): requested and extractable activity counts are shown separately.

- [Verified warehouse links and activity counts per individual case](docs/object_activity_verification.md)
- The object–activity table lists the union across all instances; an individual receiving/dispatch job has only its applicable branch.

## Schema and documentation

- [Table inventory and relationships](docs/schema_overview.md)
- [English column dictionary](docs/data_dictionary.md)
- [CSV dictionary](docs/data_dictionary.csv)
- [Editable draw.io diagram](docs/schema.drawio)
- [Object-based Gold logs and coverage](docs/object_event_logs.md)
