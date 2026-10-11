# WarehouseFlow · RSchema — table and column dictionary

- Generated from the executable SQLite schema and English metadata.

| Table | Rows | Columns | Primary key | Role |
|---|---:|---:|---|---|
| warehouse | 4 | 3 | warehouse_number | Warehouse master |
| goods | 6 | 2 | goods_id | Goods master |
| loader | 5 | 3 | loader_id | Loading/unloading worker master |
| transaction_record | 80 | 4 | transaction_id | Inbound/outbound task header, one business occurrence per row |
| goods_transaction_detail | 138 | 3 | goods_id, transaction_id | Goods lines per transaction; composite key prevents repeated goods within one task |
| loader_transaction | 167 | 2 | loader_id, transaction_id | Worker assignment bridge; multiple workers may share one task |
| transaction_record_activity | 314 | 5 | event_id | Authored actual-action history for transaction_record |
| lifecycle_case_link | 3022 | 3 | event_id, case_table, case_id | Explicit case attribution across typed action histories; auxiliary extraction index, not a business case |

## Columns

### warehouse

- Warehouse master

| Column | Type | Required | Key / relationship | Definition |
|---|---|---|---|---|
| warehouse_number | TEXT | yes | PK | Warehouse identity |
| address | TEXT | yes |  | Warehouse postal address |
| capacity | INTEGER | yes |  | Maximum total stock units; synthetic unit convention |

### goods

- Goods master

| Column | Type | Required | Key / relationship | Definition |
|---|---|---|---|---|
| goods_id | TEXT | yes | PK | Goods identity |
| goods_name | TEXT | yes |  | Goods business name |

### loader

- Loading/unloading worker master

| Column | Type | Required | Key / relationship | Definition |
|---|---|---|---|---|
| name | TEXT | yes |  | Worker name |
| phone | TEXT | yes |  | Worker contact phone |
| loader_id | TEXT | yes | PK | Worker identity |

### transaction_record

- Inbound/outbound task header, one business occurrence per row

| Column | Type | Required | Key / relationship | Definition |
|---|---|---|---|---|
| transaction_id | TEXT | yes | PK | Inbound/outbound transaction identity |
| occurred_at | TEXT | yes |  | Actual UTC completion time of recorded task; instant-event convention |
| warehouse_number | TEXT | yes | FK → warehouse.warehouse_number | Warehouse identity |
| transaction_type | TEXT | yes |  | IN = Goods Received; OUT = Goods Dispatched |

### goods_transaction_detail

- Goods lines per transaction; composite key prevents repeated goods within one task

| Column | Type | Required | Key / relationship | Definition |
|---|---|---|---|---|
| goods_id | TEXT | yes | PK; FK → goods.goods_id | Goods identity |
| transaction_id | TEXT | yes | PK; FK → transaction_record.transaction_id | Inbound/outbound transaction identity |
| quantity | INTEGER | yes |  | Positive number of units of this goods type moved by the transaction |

### loader_transaction

- Worker assignment bridge; multiple workers may share one task

| Column | Type | Required | Key / relationship | Definition |
|---|---|---|---|---|
| loader_id | TEXT | yes | PK; FK → loader.loader_id | Worker identity |
| transaction_id | TEXT | yes | PK; FK → transaction_record.transaction_id | Inbound/outbound transaction identity |

### transaction_record_activity

- Authored actual-action history for transaction_record

| Column | Type | Required | Key / relationship | Definition |
|---|---|---|---|---|
| event_id | TEXT | yes | PK | Stable identity of this actual business action; authored extension |
| transaction_id | TEXT | yes | FK → transaction_record.transaction_id | Explicit parent object key; FK to transaction_record.transaction_id |
| activity | TEXT | yes |  | Controlled business activity label; not a technical database update |
| occurred_at | TEXT | yes |  | Actual occurrence time in UTC, distinct from planned dates |
| outcome | TEXT | yes |  | Recorded action outcome: COMPLETED, APPROVED or REVISION_REQUIRED |

### lifecycle_case_link

- Explicit case attribution across typed action histories; auxiliary extraction index, not a business case

| Column | Type | Required | Key / relationship | Definition |
|---|---|---|---|---|
| event_id | TEXT | yes | PK | Validated identity in a typed activity table; polymorphic reference |
| case_table | TEXT | yes | PK | Controlled existing business table name |
| case_id | TEXT | yes | PK | Serialized primary key of the declared case table; composite parts separated by colon |

## Value domains and business rules

- IN: Goods Received
- OUT: Goods Dispatched

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

# Warehouseflow object activities and scenarios

- Original source requirements, columns and keys remain preserved.
- Every action below is an explicitly authored domain extension; these stages were not present in the source schemas.
- Each added history row records an actual activity, occurrence time, outcome and a declared FK to its object.
- Conditional revision branches and incomplete cases are intentional. Atomic grading/operation records remain auxiliary logs.
- Master-object views aggregate linked work; they do not assert one chronological causal process across unrelated jobs.

| Object | Added activities | Situation | Storage |
|---|---|---|---|
| transaction_record | Receiving Requested → Receiving Scheduled → Receiving Inspection Completed → Goods Put Away → Dispatch Requested → Dispatch Approved → Goods Picked → Goods Packed | Actual ordered actions; every seventh object stops before closure. Assignment/thesis revision branches occur in one third of objects. | transaction_record_activity |

- The full ES unions the original milestone sources and the new typed activity histories, then applies explicit event-to-case links.
- Related goods/workers, students/instructors and parent materials receive an event only through a documented business relationship.
- `lifecycle_case_link` is a generated extraction index with validated object identities; it is not an additional business object.
