# WarehouseFlow · RSchema — Schema overview

![Entity relationship diagram](schema.png)

- [Editable draw.io diagram](schema.drawio) · [Column dictionary](data_dictionary.md) · [CSV dictionary](data_dictionary.csv)

| Table | Rows | Columns | Event encoding | Primary key | Role |
|---|---:|---:|---|---|---|
| warehouse | 4 | 3 | No event encoding | warehouse_number | Warehouse master |
| goods | 6 | 2 | No event encoding | goods_id | Goods master |
| loader | 5 | 3 | No event encoding | loader_id | Loading/unloading worker master |
| transaction_record | 80 | 8 | Mixed (row + column) | transaction_id | Inbound/outbound task header, one business occurrence per row |
| goods_transaction_detail | 138 | 3 | No event encoding | goods_id, transaction_id | Goods lines per transaction; composite key prevents repeated goods within one task |
| loader_transaction | 167 | 2 | No event encoding | loader_id, transaction_id | Worker assignment bridge; multiple workers may share one task |
| transaction_record_activity | 154 | 5 | Row encoding | event_id | Authored actual-action history for transaction_record |
| lifecycle_case_link | 3022 | 3 | No event encoding | event_id, case_table, case_id | Explicit case attribution across typed action histories; auxiliary extraction index, not a business case |

- Row encoding: each occurrence is a separate row; its activity comes from a code, label or the table meaning.
- Column encoding: an object row stores actual milestone times in dedicated columns. It can contain one or several milestones.
- No event encoding: the table supplies context, plans, identities or links rather than direct events.
- Planned dates, snapshots and technical timestamps do not automatically become events.


## Relationships

| Parent | Child | Child FK | Parent key | Parent-to-child count | Kind |
|---|---|---|---|---|---|
| warehouse | transaction_record | warehouse_number | warehouse_number | 1 : 0..N | declared |
| transaction_record | goods_transaction_detail | transaction_id | transaction_id | 1 : 0..N | declared |
| goods | goods_transaction_detail | goods_id | goods_id | 1 : 0..N | declared |
| transaction_record | loader_transaction | transaction_id | transaction_id | 1 : 0..N | declared |
| loader | loader_transaction | loader_id | loader_id | 1 : 0..N | declared |
| transaction_record | transaction_record_activity | transaction_id | transaction_id | 1 : 0..N | declared |
