# WarehouseFlow · RSchema — Schema overview

![Entity relationship diagram](schema.png)

[Editable draw.io diagram](schema.drawio) · [SVG](schema.svg) · [Column dictionary](data_dictionary.md) · [CSV dictionary](data_dictionary.csv)

| Table | Rows | Columns | Primary key | Role |
|---|---:|---:|---|---|
| warehouse | 4 | 3 | warehouse_number | Warehouse master |
| goods | 6 | 2 | goods_id | Goods master |
| loader | 5 | 3 | loader_id | Loading/unloading worker master |
| transaction_record | 80 | 4 | transaction_id | Inbound/outbound task header, one business occurrence per row |
| goods_transaction_detail | 138 | 3 | goods_id, transaction_id | Goods lines per transaction; composite key prevents repeated goods within one task |
| loader_transaction | 167 | 2 | loader_id, transaction_id | Worker assignment bridge; multiple workers may share one task |


## Relationships

| Parent | Child | Child FK | Parent key | Parent-to-child cardinality | Kind |
|---|---|---|---|---|---|
| warehouse | transaction_record | warehouse_number | warehouse_number | 1 : 0..N | declared |
| transaction_record | goods_transaction_detail | transaction_id | transaction_id | 1 : 0..N | declared |
| goods | goods_transaction_detail | goods_id | goods_id | 1 : 0..N | declared |
| transaction_record | loader_transaction | transaction_id | transaction_id | 1 : 0..N | declared |
| loader | loader_transaction | loader_id | loader_id | 1 : 0..N | declared |
