# WarehouseFlow · RSchema — table and column dictionary

Generated from the executable SQLite schema and English metadata.

| Table | Rows | Columns | Primary key | Role |
|---|---:|---:|---|---|
| warehouse | 4 | 3 | warehouse_number | Warehouse master |
| goods | 6 | 2 | goods_id | Goods master |
| loader | 5 | 3 | loader_id | Loading/unloading worker master |
| transaction_record | 80 | 4 | transaction_id | Inbound/outbound task header, one business occurrence per row |
| goods_transaction_detail | 138 | 3 | goods_id, transaction_id | Goods lines per transaction; composite key prevents repeated goods within one task |
| loader_transaction | 167 | 2 | loader_id, transaction_id | Worker assignment bridge; multiple workers may share one task |

## Columns

### warehouse

Warehouse master

| Column | Type | Required | Key / relationship | Definition |
|---|---|---|---|---|
| warehouse_number | TEXT | yes | PK | Warehouse identity |
| address | TEXT | yes |  | Warehouse postal address |
| capacity | INTEGER | yes |  | Maximum total stock units; synthetic unit convention |

### goods

Goods master

| Column | Type | Required | Key / relationship | Definition |
|---|---|---|---|---|
| goods_id | TEXT | yes | PK | Goods identity |
| goods_name | TEXT | yes |  | Goods business name |

### loader

Loading/unloading worker master

| Column | Type | Required | Key / relationship | Definition |
|---|---|---|---|---|
| name | TEXT | yes |  | Worker name |
| phone | TEXT | yes |  | Worker contact phone |
| loader_id | TEXT | yes | PK | Worker identity |

### transaction_record

Inbound/outbound task header, one business occurrence per row

| Column | Type | Required | Key / relationship | Definition |
|---|---|---|---|---|
| transaction_id | TEXT | yes | PK | Inbound/outbound transaction identity |
| occurred_at | TEXT | yes |  | Actual UTC completion time of recorded task; instant-event convention |
| warehouse_number | TEXT | yes | FK → warehouse.warehouse_number | Warehouse identity |
| transaction_type | TEXT | yes |  | IN = Goods Received; OUT = Goods Dispatched |

### goods_transaction_detail

Goods lines per transaction; composite key prevents repeated goods within one task

| Column | Type | Required | Key / relationship | Definition |
|---|---|---|---|---|
| goods_id | TEXT | yes | PK; FK → goods.goods_id | Goods identity |
| transaction_id | TEXT | yes | PK; FK → transaction_record.transaction_id | Inbound/outbound transaction identity |
| quantity | INTEGER | yes |  | Positive number of units of this goods type moved by the transaction |

### loader_transaction

Worker assignment bridge; multiple workers may share one task

| Column | Type | Required | Key / relationship | Definition |
|---|---|---|---|---|
| loader_id | TEXT | yes | PK; FK → loader.loader_id | Worker identity |
| transaction_id | TEXT | yes | PK; FK → transaction_record.transaction_id | Inbound/outbound transaction identity |

## Value domains and business rules

- IN: Goods Received
- OUT: Goods Dispatched

- One transaction header is one warehouse business event, regardless of goods-line or worker counts.
- IN adds quantity; OUT removes quantity. Stock is never negative, and total stock stays within warehouse capacity.
- Transactions have at least one goods line and one worker assignment.
- Goods details and worker assignments enrich events; joining them must not multiply header events.
- A transaction ID does not link an inbound task to a later outbound task as a shipment lifecycle.
- The default warehouse view contains all recorded IN/OUT transactions for that warehouse.
- Only completion instants are recorded. Task start times and durations cannot be inferred.
- Master records and worker assignments are not additional business events.
