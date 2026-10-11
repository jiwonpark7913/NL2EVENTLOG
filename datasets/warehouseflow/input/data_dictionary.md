# WarehouseFlow English Data Dictionary

## warehouse

Warehouse master

| Column | Type | Meaning |
|---|---|---|
| warehouse_number | TEXT | Warehouse identity |
| address | TEXT | Warehouse postal address |
| capacity | INTEGER | Maximum total stock units; synthetic unit convention |

Primary key: warehouse_number.

## goods

Goods master

| Column | Type | Meaning |
|---|---|---|
| goods_id | TEXT | Goods identity |
| goods_name | TEXT | Goods business name |

Primary key: goods_id.

## loader

Loading/unloading worker master

| Column | Type | Meaning |
|---|---|---|
| name | TEXT | Worker name |
| phone | TEXT | Worker contact phone |
| loader_id | TEXT | Worker identity |

Primary key: loader_id.

## transaction_record

Inbound/outbound task header, one business occurrence per row

| Column | Type | Meaning |
|---|---|---|
| transaction_id | TEXT | Inbound/outbound transaction identity |
| occurred_at | TEXT | Actual UTC completion time of recorded task; instant-event convention |
| warehouse_number | TEXT | Warehouse identity |
| transaction_type | TEXT | IN = Goods Received; OUT = Goods Dispatched |

Primary key: transaction_id.

Foreign key: warehouse_number → warehouse.warehouse_number.

## goods_transaction_detail

Goods lines per transaction; composite key prevents repeated goods within one task

| Column | Type | Meaning |
|---|---|---|
| goods_id | TEXT | Goods identity |
| transaction_id | TEXT | Inbound/outbound transaction identity |
| quantity | INTEGER | Positive number of units of this goods type moved by the transaction |

Primary key: goods_id, transaction_id.

Foreign key: goods_id → goods.goods_id.

Foreign key: transaction_id → transaction_record.transaction_id.

## loader_transaction

Worker assignment bridge; multiple workers may share one task

| Column | Type | Meaning |
|---|---|---|
| loader_id | TEXT | Worker identity |
| transaction_id | TEXT | Inbound/outbound transaction identity |

Primary key: loader_id, transaction_id.

Foreign key: loader_id → loader.loader_id.

Foreign key: transaction_id → transaction_record.transaction_id.

## Code domain

IN = Goods Received; OUT = Goods Dispatched.

## Business rules

- One transaction header is one warehouse business event, regardless of goods-line or worker counts.
- IN adds quantity; OUT removes quantity. Stock is never negative, and total stock stays within warehouse capacity.
- Transactions have at least one goods line and one worker assignment.
- Goods details and worker assignments enrich events; joining them must not multiply header events.
- A transaction ID does not link an inbound task to a later outbound task as a shipment lifecycle.
- The default warehouse view contains all recorded IN/OUT transactions for that warehouse.
- Only completion instants are recorded. Task start times and durations cannot be inferred.
- Master records and worker assignments are not additional business events.
