# WarehouseFlow — warehouse receiving and dispatching

- This English-language synthetic dataset uses an actual SchemaAgent/RSchema requirement and relational schema.
- It records goods arriving at and leaving warehouses.
- All six source tables, 17 columns, primary keys and five foreign-key relationships are retained.
- The dataset adds no tables or columns.

## Source and changes

- Source repository: [hnuGraph/LLM4DBdesign](https://github.com/hnuGraph/LLM4DBdesign).
- Source record: `67552f0a13602ec03b41a78e`, line 3 of `datasets/RSchema/annotation.jsonl`.
- The exact source commit and record hash are listed in `source/provenance.json`.
- `source/rschema_original.json` preserves the original requirement and schema.
- English table and column names are normalized to snake_case.
- Inconsistent capital letters in the original key names are resolved without changing their relationships.
- SQLite types, required values, IN/OUT code meanings, UTC completion times and stock rules are added simulation assumptions.
- The conceptual model is derived locally from the source schema; no original conceptual diagram was provided.
- The SchemaAgent implementation is not run to generate this database.

## Tables and events

- `warehouse`, `goods` and `loader` store basic information about warehouses, goods and workers.
- `transaction_record` stores one receiving or dispatching task per row.
- `goods_transaction_detail` records which goods and quantities belong to each task.
- `loader_transaction` records which workers participate in each task.
- Each task is one event, even when multiple goods and workers are involved.
- The dataset has 4 warehouses and 80 business events: 45 goods-received events and 35 goods-dispatched events.
- A warehouse defines the case: its recorded tasks form one timeline.
- The source does not link receiving and dispatching tasks into individual shipment histories.
- Joining both goods and worker details to a task produces 289 rows for 80 tasks in this example; those rows must not be counted as 289 events.

## Questions and expected results

- Seven English questions are supplied.
- R01/R02 select receiving, R03/R04 select dispatching, and R05/R06 select the complete recorded warehouse timeline.
- Each pair uses direct wording and a paraphrase of the same request.
- R07 asks for task start and completion events; it is unsupported because only completion times are recorded.
- Expected logs are selected from the simulated task history.
- Expected extraction specifications identify the corresponding database tables and columns.
- All six answerable questions produce SQL results identical to the expected logs.
- SQL checks confirm dataset consistency; they do not measure model accuracy.

## Rebuild and evaluation

- Run `python build.py` using Python 3.10 or later; no external package is needed.
- Rebuilding replaces generated DB and expected-result files.
- The included source record is enough to rebuild; downloading the full RSchema dataset is unnecessary.
- Provide only `input/` to the model.
- The task scope catalog supplies warehouse cases, activity names and a default rule for full-timeline requests.
- Keep source answers, design files, generation code, expected answers in `private/`, and the validation report outside the model's context.
- Event logs are ordinary CSV timelines; they are not OCEL files.
- The extraction specification uses a dataset-specific format; compatibility with the existing NL2EventLog implementation has not been tested.

## Limits

- The rows are simulated; they are not real warehouse records.
- Added code meanings apply to this dataset and do not establish meanings for other RSchema examples.
- The data dictionary uses a custom practical format; ISO/IEC 11179 compliance is not claimed.
- Task starts, durations, approvals and purchase orders are not recorded or invented.

## Schema and documentation

![Schema](docs/schema.png)

- [Table inventory and relationships](docs/schema_overview.md)
- [English column dictionary](docs/data_dictionary.md)
- [CSV dictionary](docs/data_dictionary.csv)
- [Editable draw.io diagram](docs/schema.drawio)
