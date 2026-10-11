# WarehouseFlow

- **Situation:** Goods enter a warehouse and complete inspection and putaway, or leave through approval, picking, packing and dispatch. Goods and workers are linked to each transaction.
- **Source:** One preserved RSchema warehouse requirement and logical schema. Original source columns and keys are preserved.
- **Extension:** New activity histories, timestamps and cross-object attribution rules are authored synthetic domain design. They are not copied from the source or observed production data.
- **Database:** 8 tables; 394 distinct recorded business events.
- **Gold:** 12 answerable question-specific CSV logs out of 13 questions. Paraphrase pairs can share the same expected content.
- **Execution:** Run `python datasets/warehouseflow/build.py` from the repository root, then `python make_docs.py`. Only the Python standard library is needed for DB/log generation; diagrams use PyMuPDF.

## Objects, activities and situations

| Object / case | Activity types in its log | Situation / scope | Gold CSV |
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

## Schema and documentation

![Schema](docs/schema.png)

- [Table inventory and relationships](docs/schema_overview.md)
- [English column dictionary](docs/data_dictionary.md)
- [CSV dictionary](docs/data_dictionary.csv)
- [Editable draw.io diagram](docs/schema.drawio)
- [Object-based Gold logs and coverage](docs/object_event_logs.md)
