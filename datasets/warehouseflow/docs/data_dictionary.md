# WarehouseFlow RSchema v1 — data dictionary

## 1. Dictionary basic information

| Field | Value |
| --- | --- |
| dictionary_id | NL2EVENTLOG:warehouseflow |
| version | 2026-10-12 |
| name | WarehouseFlow RSchema v1 |
| description | English synthetic relational database for query-conditioned process-view and event-log extraction. |
| language | en |
| timezone | UTC |
| dbms | SQLite |
| namespace | warehouseflow |
| timestamp_columns | 6 |
| event_timestamp_columns | 6 |
| maintainer | NL2EVENTLOG project maintainers |
| registration_status | Project-maintained draft; not ISO-registered or certified |
| source_policy | Source definitions are retained and authored lifecycle additions are identified in source/design documents. |
| standards_profile | Project profile informed by ISO/IEC 11179-3 and 11179-4 public abstracts; no full clause-by-clause conformance assessment. |
| layout | 1 Dictionary basic information; 2 Table definitions; 3 Column definitions |

- The three-part layout is a project documentation choice, not a mandated ISO/IEC template.
- ISO/IEC 11179-4 addresses semantic definitions rather than prescribing their formatting. Only public standard scope descriptions were consulted.
- SQL keys and constraints are taken from the executable DB. SQLite TEXT has no declared maximum length unless an explicit constraint says otherwise. Examples are observed synthetic values, not additional allowed-value constraints.
- [ISO/IEC 11179-3:2023](https://www.iso.org/standard/78915.html): Registry identification, administration and definition concepts.
- [ISO/IEC 11179-4:2004](https://www.iso.org/standard/35346.html): Semantic formulation of data definitions.

## 2. Table definitions

| Metadata ID | Logical name | Physical name | Rows | PK | FK | Event encoding | Definition |
| --- | --- | --- | --- | --- | --- | --- | --- |
| warehouseflow.warehouse | Warehouse | warehouse | 4 | warehouse_number | None declared | No event encoding | Warehouse master |
| warehouseflow.goods | Goods | goods | 6 | goods_id | None declared | No event encoding | Goods master |
| warehouseflow.loader | Loader | loader | 5 | loader_id | None declared | No event encoding | Loading/unloading worker master |
| warehouseflow.transaction_record | Transaction Record | transaction_record | 80 | transaction_id | warehouse_number → warehouse.warehouse_number | Mixed (row + column) | Inbound/outbound task header, one business occurrence per row |
| warehouseflow.goods_transaction_detail | Goods Transaction Detail | goods_transaction_detail | 138 | goods_id, transaction_id | transaction_id → transaction_record.transaction_id; goods_id → goods.goods_id | No event encoding | Goods lines per transaction; composite key prevents repeated goods within one task |
| warehouseflow.loader_transaction | Loader Transaction | loader_transaction | 167 | loader_id, transaction_id | transaction_id → transaction_record.transaction_id; loader_id → loader.loader_id | No event encoding | Worker assignment bridge; multiple workers may share one task |
| warehouseflow.transaction_record_activity | Transaction Record Activity | transaction_record_activity | 154 | event_id | transaction_id → transaction_record.transaction_id | Row encoding | Authored actual-action history for transaction_record |
| warehouseflow.lifecycle_case_link | Lifecycle Case Link | lifecycle_case_link | 3022 | event_id, case_table, case_id | None declared | No event encoding | Explicit case attribution across typed action histories; auxiliary extraction index, not a business case |

- Row encoding: an event occurrence is represented by a row.
- Column encoding: an object row stores one or more actual business milestone timestamps in dedicated columns.
- No event encoding: contextual, reference, planned or relationship/index data; this does not mean the related business object lacks an event log.
- **warehouse:** Master, plan, reference or relationship/index data; this table does not directly produce an event in the current ES. Related objects can still have logs from other tables.
- **goods:** Master, plan, reference or relationship/index data; this table does not directly produce an event in the current ES. Related objects can still have logs from other tables.
- **loader:** Master, plan, reference or relationship/index data; this table does not directly produce an event in the current ES. Related objects can still have logs from other tables.
- **transaction_record:** Actual milestone columns on the existing business object; NULL means not yet occurred. Authored added event columns: receiving_requested_at, receiving_scheduled_at, dispatch_requested_at, dispatch_approved_at.
- **goods_transaction_detail:** Master, plan, reference or relationship/index data; this table does not directly produce an event in the current ES. Related objects can still have logs from other tables.
- **loader_transaction:** Master, plan, reference or relationship/index data; this table does not directly produce an event in the current ES. Related objects can still have logs from other tables.
- **transaction_record_activity:** Each action is a separate row; activity selects its meaning and occurred_at is its actual time.
- **lifecycle_case_link:** Master, plan, reference or relationship/index data; this table does not directly produce an event in the current ES. Related objects can still have logs from other tables.

## 3. Column definitions

### warehouse

| Element ID | Logical / physical name | Definition | Representation / SQL type | Length | Required | PK / FK | Default | Value domain / constraints | Unit | Examples |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| warehouseflow.warehouse.warehouse_number | Warehouse Number / warehouse_number | Warehouse identity | Identifier / TEXT | Not bounded by declared SQLite type | yes | 1 /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["W1", "W2", "W3"] |
| warehouseflow.warehouse.address | Address / address | Warehouse postal address | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["Fictional Warehouse Avenue 1", "Fictional Warehouse Avenue 2", "Fictional Warehouse Avenue 3"] |
| warehouseflow.warehouse.capacity | Capacity / capacity | Maximum total stock units; synthetic unit convention | Number / INTEGER | Not applicable | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL CHECK(capacity > 0) | See column definition; no implicit unit | [1000] |

- **Declared table constraints:** `CREATE TABLE warehouse (warehouse_number TEXT NOT NULL, address TEXT NOT NULL, capacity INTEGER NOT NULL CHECK(capacity > 0), PRIMARY KEY (warehouse_number))`

### goods

| Element ID | Logical / physical name | Definition | Representation / SQL type | Length | Required | PK / FK | Default | Value domain / constraints | Unit | Examples |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| warehouseflow.goods.goods_id | Goods Id / goods_id | Goods identity | Identifier / TEXT | Not bounded by declared SQLite type | yes | 1 /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["G1", "G2", "G3"] |
| warehouseflow.goods.goods_name | Goods Name / goods_name | Goods business name | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["Goods 1", "Goods 2", "Goods 3"] |

- **Declared table constraints:** `CREATE TABLE goods (goods_id TEXT NOT NULL, goods_name TEXT NOT NULL, PRIMARY KEY (goods_id))`

### loader

| Element ID | Logical / physical name | Definition | Representation / SQL type | Length | Required | PK / FK | Default | Value domain / constraints | Unit | Examples |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| warehouseflow.loader.name | Name / name | Worker name | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["Worker 1", "Worker 2", "Worker 3"] |
| warehouseflow.loader.phone | Phone / phone | Worker contact phone | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["+1-555-0101", "+1-555-0102", "+1-555-0103"] |
| warehouseflow.loader.loader_id | Loader Id / loader_id | Worker identity | Identifier / TEXT | Not bounded by declared SQLite type | yes | 1 /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["L1", "L2", "L3"] |

- **Declared table constraints:** `CREATE TABLE loader (name TEXT NOT NULL, phone TEXT NOT NULL, loader_id TEXT NOT NULL, PRIMARY KEY (loader_id))`

### transaction_record

| Element ID | Logical / physical name | Definition | Representation / SQL type | Length | Required | PK / FK | Default | Value domain / constraints | Unit | Examples |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| warehouseflow.transaction_record.transaction_id | Transaction Id / transaction_id | Inbound/outbound transaction identity | Identifier / TEXT | Not bounded by declared SQLite type | yes | 1 /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["T001", "T002", "T003"] |
| warehouseflow.transaction_record.occurred_at | Occurred At / occurred_at | Actual UTC completion time of recorded task; instant-event convention | Date/time text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | UTC for actual event timestamps; source birth dates and planned dates retain their documented meaning | ["2026-04-01T01:00:00Z", "2026-04-01T02:00:00Z", "2026-04-01T03:00:00Z"] |
| warehouseflow.transaction_record.warehouse_number | Warehouse Number / warehouse_number | Warehouse identity | Identifier / TEXT | Not bounded by declared SQLite type | yes |  / warehouse.warehouse_number | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["W1", "W2", "W3"] |
| warehouseflow.transaction_record.transaction_type | Transaction Type / transaction_type | IN = Goods Received; OUT = Goods Dispatched | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL CHECK(transaction_type IN ('IN','OUT')) | See column definition; no implicit unit | ["IN", "OUT"] |
| warehouseflow.transaction_record.receiving_requested_at | Receiving Requested At / receiving_requested_at | Actual UTC time of Receiving Requested. NULL means no recorded occurrence. Authored single-occurrence milestone; not a source-provided field. | Date/time text / TEXT | Not bounded by declared SQLite type | no |  /  | No SQL default | SQL type and declared constraints: See table DDL | UTC for actual event timestamps; source birth dates and planned dates retain their documented meaning | ["2026-03-31T21:00:00Z", "2026-03-31T22:00:00Z", "2026-03-31T23:00:00Z"] |
| warehouseflow.transaction_record.receiving_scheduled_at | Receiving Scheduled At / receiving_scheduled_at | Actual UTC time of Receiving Scheduled. NULL means no recorded occurrence. Authored single-occurrence milestone; not a source-provided field. | Date/time text / TEXT | Not bounded by declared SQLite type | no |  /  | No SQL default | SQL type and declared constraints: See table DDL | UTC for actual event timestamps; source birth dates and planned dates retain their documented meaning | ["2026-03-31T22:00:00Z", "2026-03-31T23:00:00Z", "2026-04-01T00:00:00Z"] |
| warehouseflow.transaction_record.dispatch_requested_at | Dispatch Requested At / dispatch_requested_at | Actual UTC time of Dispatch Requested. NULL means no recorded occurrence. Authored single-occurrence milestone; not a source-provided field. | Date/time text / TEXT | Not bounded by declared SQLite type | no |  /  | No SQL default | SQL type and declared constraints: See table DDL | UTC for actual event timestamps; source birth dates and planned dates retain their documented meaning | ["2026-04-01T02:00:00Z", "2026-04-01T03:00:00Z", "2026-04-01T09:00:00Z"] |
| warehouseflow.transaction_record.dispatch_approved_at | Dispatch Approved At / dispatch_approved_at | Actual UTC time of Dispatch Approved. NULL means no recorded occurrence. Authored single-occurrence milestone; not a source-provided field. | Date/time text / TEXT | Not bounded by declared SQLite type | no |  /  | No SQL default | SQL type and declared constraints: See table DDL | UTC for actual event timestamps; source birth dates and planned dates retain their documented meaning | ["2026-04-01T03:00:00Z", "2026-04-01T04:00:00Z", "2026-04-01T10:00:00Z"] |

- **Declared table constraints:** `CREATE TABLE transaction_record (transaction_id TEXT NOT NULL, occurred_at TEXT NOT NULL, warehouse_number TEXT NOT NULL, transaction_type TEXT NOT NULL CHECK(transaction_type IN ('IN','OUT')), receiving_requested_at TEXT, receiving_scheduled_at TEXT, dispatch_requested_at TEXT, dispatch_approved_at TEXT, PRIMARY KEY (transaction_id), FOREIGN KEY (warehouse_number) REFERENCES warehouse(warehouse_number))`

### goods_transaction_detail

| Element ID | Logical / physical name | Definition | Representation / SQL type | Length | Required | PK / FK | Default | Value domain / constraints | Unit | Examples |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| warehouseflow.goods_transaction_detail.goods_id | Goods Id / goods_id | Goods identity | Identifier / TEXT | Not bounded by declared SQLite type | yes | 1 / goods.goods_id | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["G1", "G2", "G3"] |
| warehouseflow.goods_transaction_detail.transaction_id | Transaction Id / transaction_id | Inbound/outbound transaction identity | Identifier / TEXT | Not bounded by declared SQLite type | yes | 2 / transaction_record.transaction_id | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["T004", "T009", "T012"] |
| warehouseflow.goods_transaction_detail.quantity | Quantity / quantity | Positive number of units of this goods type moved by the transaction | Number / INTEGER | Not applicable | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL CHECK(quantity > 0) | See column definition; no implicit unit | [8, 10, 9] |

- **Declared table constraints:** `CREATE TABLE goods_transaction_detail (goods_id TEXT NOT NULL, transaction_id TEXT NOT NULL, quantity INTEGER NOT NULL CHECK(quantity > 0), PRIMARY KEY (goods_id,transaction_id), FOREIGN KEY (goods_id) REFERENCES goods(goods_id), FOREIGN KEY (transaction_id) REFERENCES transaction_record(transaction_id))`

### loader_transaction

| Element ID | Logical / physical name | Definition | Representation / SQL type | Length | Required | PK / FK | Default | Value domain / constraints | Unit | Examples |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| warehouseflow.loader_transaction.loader_id | Loader Id / loader_id | Worker identity | Identifier / TEXT | Not bounded by declared SQLite type | yes | 1 / loader.loader_id | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["L1", "L2", "L3"] |
| warehouseflow.loader_transaction.transaction_id | Transaction Id / transaction_id | Inbound/outbound transaction identity | Identifier / TEXT | Not bounded by declared SQLite type | yes | 2 / transaction_record.transaction_id | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["T001", "T002", "T003"] |

- **Declared table constraints:** `CREATE TABLE loader_transaction (loader_id TEXT NOT NULL, transaction_id TEXT NOT NULL, PRIMARY KEY (loader_id,transaction_id), FOREIGN KEY (loader_id) REFERENCES loader(loader_id), FOREIGN KEY (transaction_id) REFERENCES transaction_record(transaction_id))`

### transaction_record_activity

| Element ID | Logical / physical name | Definition | Representation / SQL type | Length | Required | PK / FK | Default | Value domain / constraints | Unit | Examples |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| warehouseflow.transaction_record_activity.event_id | Event Id / event_id | Stable identity of this actual business action; authored extension | Identifier / TEXT | Not bounded by declared SQLite type | yes | 1 /  | No SQL default | SQL type and declared constraints: PRIMARY KEY | See column definition; no implicit unit | ["LC:transaction_record:T001:3", "LC:transaction_record:T002:3", "LC:transaction_record:T002:4"] |
| warehouseflow.transaction_record_activity.transaction_id | Transaction Id / transaction_id | Explicit parent object key; FK to transaction_record.transaction_id | Identifier / TEXT | Not bounded by declared SQLite type | yes |  / transaction_record.transaction_id | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["T001", "T002", "T003"] |
| warehouseflow.transaction_record_activity.activity | Activity / activity | Controlled business activity label; not a technical database update | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["Receiving Inspection Completed", "Goods Put Away", "Goods Picked"] |
| warehouseflow.transaction_record_activity.occurred_at | Occurred At / occurred_at | Actual occurrence time in UTC, distinct from planned dates | Date/time text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | UTC for actual event timestamps; source birth dates and planned dates retain their documented meaning | ["2026-04-01T01:30:00Z", "2026-04-01T02:30:00Z", "2026-04-01T03:00:00Z"] |
| warehouseflow.transaction_record_activity.outcome | Outcome / outcome | Recorded action outcome: COMPLETED, APPROVED or REVISION_REQUIRED | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["COMPLETED"] |

- **Declared table constraints:** `CREATE TABLE transaction_record_activity (event_id TEXT PRIMARY KEY, transaction_id TEXT NOT NULL, activity TEXT NOT NULL, occurred_at TEXT NOT NULL, outcome TEXT NOT NULL, FOREIGN KEY (transaction_id) REFERENCES transaction_record(transaction_id))`

### lifecycle_case_link

| Element ID | Logical / physical name | Definition | Representation / SQL type | Length | Required | PK / FK | Default | Value domain / constraints | Unit | Examples |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| warehouseflow.lifecycle_case_link.event_id | Event Id / event_id | Validated identity in a typed activity table; polymorphic reference | Identifier / TEXT | Not bounded by declared SQLite type | yes | 1 /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["LC:transaction_record:T001:1", "LC:transaction_record:T001:2", "LC:transaction_record:T001:3"] |
| warehouseflow.lifecycle_case_link.case_table | Case Table / case_table | Controlled existing business table name | Identifier / TEXT | Not bounded by declared SQLite type | yes | 2 /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["transaction_record", "warehouse", "goods"] |
| warehouseflow.lifecycle_case_link.case_id | Case Id / case_id | Serialized primary key of the declared case table; composite parts separated by colon | Identifier / TEXT | Not bounded by declared SQLite type | yes | 3 /  | No SQL default | SQL type and declared constraints: NOT NULL | See column definition; no implicit unit | ["T001", "T002", "T003"] |

- **Declared table constraints:** `CREATE TABLE lifecycle_case_link(event_id TEXT NOT NULL,case_table TEXT NOT NULL,case_id TEXT NOT NULL,PRIMARY KEY(event_id,case_table,case_id))`

### Business meanings and extraction rules

- Original source layer: One transaction header is one warehouse business event, regardless of goods-line or worker counts.
- Original source layer: IN adds quantity; OUT removes quantity. Stock is never negative, and total stock stays within warehouse capacity.
- Original source layer: Transactions have at least one goods line and one worker assignment.
- Original source layer: Goods details and worker assignments enrich events; joining them must not multiply header events.
- Original source layer: A transaction ID does not link an inbound task to a later outbound task as a shipment lifecycle.
- Original source layer: The default warehouse view contains all recorded IN/OUT transactions for that warehouse.
- Original source layer: Only completion instants are recorded. Task start times and durations cannot be inferred.
- Original source layer: Master records and worker assignments are not additional business events.
- Original source rows are preserved. Added typed activity histories are authored synthetic domain extensions, not claimed source fields.
- Only actual occurred_at times generate lifecycle events. Planned dates and technical timestamps remain excluded.
- Lifecycle case links use exact typed object identity. Related cases may share an event; uniqueness is (case_id,event_id).
- Incomplete cases and conditional revision branches are intentional; no final action is inferred for an open case.
- One-time milestone events are stored in named timestamp columns on their business record. They have been removed from generic action rows to prevent duplicate extraction.
- Repeated review/revision/grading/experiment actions remain row encoded; milestone timestamps preserve their original event IDs and actual times.

### Object activity storage

- Actual one-time milestone columns and retained row histories are used together. Events are extracted once, not mirrored in two places.
- Original event IDs and occurrence times are preserved. All added fields are authored synthetic extensions.

| Object | Activities | Storage |
|---|---|---|
| transaction_record | Receiving Requested; Receiving Scheduled; Receiving Inspection Completed; Goods Put Away; Dispatch Requested; Dispatch Approved; Goods Picked; Goods Packed | Actual milestone columns on transaction_record; remaining repeatable actions stay in transaction_record_activity |
