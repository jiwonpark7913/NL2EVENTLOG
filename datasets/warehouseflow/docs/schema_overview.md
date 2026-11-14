# WarehouseFlow — schema overview

- [Editable draw.io diagram](schema.drawio) · [Data dictionary](data_dictionary.md)

| Table | Rows | Columns | Business role |
| --- | --- | --- | --- |
| warehouse | 4 | 5 | Warehouse identity, capacity and database maintenance times. These maintenance times do not document warehouse work. |
| goods | 7 | 3 | Goods identity and product category; NORMAL/FRAGILE describe the goods. |
| worker | 7 | 5 | Worker identity and job role. role_code identifies a role, not an action performed. |
| work_code | 10 | 3 | Business meanings of codes within the specified code family. |
| receiving_request | 26 | 5 | One submitted request for receipt of one goods type into a warehouse. |
| goods_receipt | 23 | 5 | One actual receipt registration for a receiving request. condition_code describes goods condition, not the receipt action kind. |
| dispatch_order | 20 | 7 | One request to dispatch one goods type, with separate actual request and approval times. Priority describes urgency. |
| warehouse_audit | 9 | 6 | One stock-audit occurrence, its actual start and completion, and its outcome. PASS/RECOUNT describes the result of the same audit kind. |
| goods_movement | 39 | 9 | One completed inbound or outbound stock movement; each row records when the movement actually occurred. |
| request_action | 56 | 6 | One checking, holding or releasing action performed on a receiving request; repeated checking actions retain separate records. |
| warehouse_task_history | 63 | 9 | One putaway, picking or packing work occurrence, with actual start and optional completion. A repeated attempt has a new task_id. |
| handling_history | 41 | 8 | One unloading or loading occurrence, with actual start and optional completion. A repeated attempt has a new handling_id. |
| worker_contact | 3 | 2 | Optional contact attributes of an existing worker, identified by the payroll number. A row describes that worker, not a separate contact entity. Absence of a row means no contact attributes are stored. |

| Parent | Child | FK columns | Referenced columns | Cardinality |
| --- | --- | --- | --- | --- |
| goods | receiving_request | goods_id | goods_id | 1 : 0..N |
| warehouse | receiving_request | warehouse_id | warehouse_id | 1 : 0..N |
| worker | goods_receipt | receiver_id | worker_id | 1 : 0..N |
| receiving_request | goods_receipt | request_id | request_id | 1 : 0..1 |
| goods | dispatch_order | goods_id | goods_id | 1 : 0..N |
| warehouse | dispatch_order | warehouse_id | warehouse_id | 1 : 0..N |
| worker | warehouse_audit | worker_id | worker_id | 1 : 0..N |
| warehouse | warehouse_audit | warehouse_id | warehouse_id | 1 : 0..N |
| work_code | goods_movement | code_family, movement_code | code_family, code | 1 : 0..N |
| dispatch_order | goods_movement | dispatch_id | dispatch_id | 1 : 0..1 |
| goods_receipt | goods_movement | receipt_id | receipt_id | 1 : 0..1 |
| goods | goods_movement | goods_id | goods_id | 1 : 0..N |
| warehouse | goods_movement | warehouse_id | warehouse_id | 1 : 0..N |
| work_code | request_action | code_family, action_code | code_family, code | 1 : 0..N |
| worker | request_action | worker_id | worker_id | 1 : 0..N |
| receiving_request | request_action | request_id | request_id | 1 : 0..N |
| work_code | warehouse_task_history | code_family, task_code | code_family, code | 1 : 0..N |
| worker | warehouse_task_history | worker_id | worker_id | 1 : 0..N |
| dispatch_order | warehouse_task_history | dispatch_id | dispatch_id | 1 : 0..N |
| receiving_request | warehouse_task_history | request_id | request_id | 1 : 0..N |
| work_code | handling_history | code_family, handling_code | code_family, code | 1 : 0..N |
| worker | handling_history | worker_id | worker_id | 1 : 0..N |
| dispatch_order | handling_history | dispatch_id | dispatch_id | 1 : 0..N |
| receiving_request | handling_history | request_id | request_id | 1 : 0..N |
| worker | worker_contact | staff_no | payroll_no | 1 : 0..1 |
