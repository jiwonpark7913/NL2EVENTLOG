# warehouseflow — Database Inspection

Original SQLite records; **not model input**. Click a table name to inspect its actual first 10 rows.

![Interactive table overview](schema.svg)

| Table | Rows | Columns | Open preview |
|---|---:|---:|---|
| dispatch_order | 20 | 7 | [First 10 rows](tables/dispatch_order.md) |
| goods | 7 | 3 | [First 10 rows](tables/goods.md) |
| goods_movement | 39 | 9 | [First 10 rows](tables/goods_movement.md) |
| goods_receipt | 23 | 5 | [First 10 rows](tables/goods_receipt.md) |
| handling_history | 41 | 8 | [First 10 rows](tables/handling_history.md) |
| receiving_request | 26 | 5 | [First 10 rows](tables/receiving_request.md) |
| request_action | 56 | 6 | [First 10 rows](tables/request_action.md) |
| warehouse | 4 | 5 | [First 10 rows](tables/warehouse.md) |
| warehouse_audit | 9 | 6 | [First 10 rows](tables/warehouse_audit.md) |
| warehouse_task_history | 63 | 9 | [First 10 rows](tables/warehouse_task_history.md) |
| work_code | 10 | 3 | [First 10 rows](tables/work_code.md) |
| worker | 7 | 4 | [First 10 rows](tables/worker.md) |

The table links are the dependable GitHub navigation path; SVG click-through may vary by GitHub's rendering/security restrictions.
FK arrows are based on declared SQLite foreign keys. Informal semantic links are not asserted as physical FKs.
