# WarehouseFlow New — data dictionary

## 1. Dictionary basic information

| Field | Value |
| --- | --- |
| dictionary_id | NL2EVENTLOG:warehouseflow_new |
| name | WarehouseFlow New |
| version | 2026-10-29 |
| language | en |
| dbms | SQLite |
| timezone | UTC |
| description | Synthetic warehouse receiving, dispatch, stock-audit and handling records. |
| status | Project-maintained synthetic business-data definitions |
| standards_profile | Three-part project profile informed by public ISO/IEC 11179-3 and 11179-4 scope statements; not a certification or full conformance assessment. |
| source_policy | Schema-informed warehouse simulation; authored additions are documented separately. |

- The three-part layout is a project choice. ISO/IEC 11179-3 concerns registry facilities and 11179-4 concerns semantic definitions; the public scope statements do not mandate this template.
- A composite primary key is one key over its full tuple. All SQL constraints below are taken from the executable schema.
- References: [ISO/IEC 11179-3](https://www.iso.org/standard/78915.html), [ISO/IEC 11179-4](https://www.iso.org/standard/35346.html).

## 2. Table definitions

| Table ID | Logical / physical name | PK | FK | Business definition |
| --- | --- | --- | --- | --- |
| warehouseflow_new.warehouse | Warehouse / warehouse | warehouse_id | None declared | Warehouse identity, capacity and database maintenance times. These maintenance times do not document warehouse work. |
| warehouseflow_new.goods | Goods / goods | goods_id | None declared | Goods identity and product category; NORMAL/FRAGILE describe the goods. |
| warehouseflow_new.worker | Worker / worker | worker_id | None declared | Worker identity and job role. role_code identifies a role, not an action performed. |
| warehouseflow_new.work_code | Work Code / work_code | code_family, code | None declared | Business meanings of codes within the specified code family. |
| warehouseflow_new.receiving_request | Receiving Request / receiving_request | request_id | (goods_id) → goods(goods_id); (warehouse_id) → warehouse(warehouse_id) | One submitted request for receipt of one goods type into a warehouse. |
| warehouseflow_new.goods_receipt | Goods Receipt / goods_receipt | receipt_id | (receiver_id) → worker(worker_id); (request_id) → receiving_request(request_id) | One actual receipt registration for a receiving request. condition_code describes goods condition, not the receipt action kind. |
| warehouseflow_new.dispatch_order | Dispatch Order / dispatch_order | dispatch_id | (goods_id) → goods(goods_id); (warehouse_id) → warehouse(warehouse_id) | One request to dispatch one goods type, with separate actual request and approval times. Priority describes urgency. |
| warehouseflow_new.warehouse_audit | Warehouse Audit / warehouse_audit | audit_id | (worker_id) → worker(worker_id); (warehouse_id) → warehouse(warehouse_id) | One stock-audit occurrence, its actual start and completion, and its outcome. PASS/RECOUNT describes the result of the same audit kind. |
| warehouseflow_new.goods_movement | Goods Movement / goods_movement | movement_id | (code_family,movement_code) → work_code(code_family,code); (dispatch_id) → dispatch_order(dispatch_id); (receipt_id) → goods_receipt(receipt_id); (goods_id) → goods(goods_id); (warehouse_id) → warehouse(warehouse_id) | One completed inbound or outbound stock movement; each row records when the movement actually occurred. |
| warehouseflow_new.request_action | Request Action / request_action | action_id | (code_family,action_code) → work_code(code_family,code); (worker_id) → worker(worker_id); (request_id) → receiving_request(request_id) | One checking, holding or releasing action performed on a receiving request; repeated checking actions retain separate records. |
| warehouseflow_new.warehouse_task_history | Warehouse Task History / warehouse_task_history | task_id | (code_family,task_code) → work_code(code_family,code); (worker_id) → worker(worker_id); (dispatch_id) → dispatch_order(dispatch_id); (request_id) → receiving_request(request_id) | One putaway, picking or packing work occurrence, with actual start and optional completion. A repeated attempt has a new task_id. |
| warehouseflow_new.handling_history | Handling History / handling_history | handling_id | (code_family,handling_code) → work_code(code_family,code); (worker_id) → worker(worker_id); (dispatch_id) → dispatch_order(dispatch_id); (request_id) → receiving_request(request_id) | One unloading or loading occurrence, with actual start and optional completion. A repeated attempt has a new handling_id. |

## 3. Column definitions

### warehouse

| Element ID | Column | SQL type | Required | PK position | FK | Default | Length | Unit | Definition |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| warehouseflow_new.warehouse.warehouse_id | warehouse_id | TEXT | True | 1 |  | No SQL default | Unbounded SQLite TEXT | Not applicable | Unique warehouse identity; foreign references identify the warehouse concerned. |
| warehouseflow_new.warehouse.warehouse_name | warehouse_name | TEXT | True |  |  | No SQL default | Unbounded SQLite TEXT | Not applicable | English warehouse name. |
| warehouseflow_new.warehouse.capacity | capacity | INTEGER | True |  |  | No SQL default | Not applicable | stock units | Maximum stored stock units for the simulated warehouse. |
| warehouseflow_new.warehouse.created_at | created_at | TEXT | True |  |  | No SQL default | Unbounded SQLite TEXT | UTC | UTC database record-creation time, not a warehouse business action. |
| warehouseflow_new.warehouse.updated_at | updated_at | TEXT | True |  |  | No SQL default | Unbounded SQLite TEXT | UTC | UTC database maintenance time, not a warehouse business action. |

```sql
CREATE TABLE warehouse(warehouse_id TEXT PRIMARY KEY NOT NULL, warehouse_name TEXT NOT NULL, capacity INTEGER NOT NULL CHECK(capacity>0), created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
```

### goods

| Element ID | Column | SQL type | Required | PK position | FK | Default | Length | Unit | Definition |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| warehouseflow_new.goods.goods_id | goods_id | TEXT | True | 1 |  | No SQL default | Unbounded SQLite TEXT | Not applicable | Unique goods identity; foreign references identify the goods concerned. |
| warehouseflow_new.goods.goods_name | goods_name | TEXT | True |  |  | No SQL default | Unbounded SQLite TEXT | Not applicable | English goods name. |
| warehouseflow_new.goods.category_code | category_code | TEXT | True |  |  | No SQL default | Unbounded SQLite TEXT | Not applicable | NORMAL or FRAGILE product category, not an action. |

```sql
CREATE TABLE goods(goods_id TEXT PRIMARY KEY NOT NULL, goods_name TEXT NOT NULL, category_code TEXT NOT NULL CHECK(category_code IN ('NORMAL','FRAGILE')));
```

### worker

| Element ID | Column | SQL type | Required | PK position | FK | Default | Length | Unit | Definition |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| warehouseflow_new.worker.worker_id | worker_id | TEXT | True | 1 |  | No SQL default | Unbounded SQLite TEXT | Not applicable | Unique worker identity; on a work or audit record, identifies the worker performing it. |
| warehouseflow_new.worker.worker_name | worker_name | TEXT | True |  |  | No SQL default | Unbounded SQLite TEXT | Not applicable | English worker name. |
| warehouseflow_new.worker.role_code | role_code | TEXT | True |  |  | No SQL default | Unbounded SQLite TEXT | Not applicable | HANDLER or SUPERVISOR worker role, not the action performed. |
| warehouseflow_new.worker.updated_at | updated_at | TEXT | True |  |  | No SQL default | Unbounded SQLite TEXT | UTC | UTC database maintenance time, not a warehouse business action. |

```sql
CREATE TABLE worker(worker_id TEXT PRIMARY KEY NOT NULL, worker_name TEXT NOT NULL, role_code TEXT NOT NULL CHECK(role_code IN ('HANDLER','SUPERVISOR')), updated_at TEXT NOT NULL);
```

### work_code

| Element ID | Column | SQL type | Required | PK position | FK | Default | Length | Unit | Definition |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| warehouseflow_new.work_code.code_family | code_family | TEXT | True | 1 |  | No SQL default | Unbounded SQLite TEXT | Not applicable | Business context for the code. Each work table has one fixed family enforced by CHECK. |
| warehouseflow_new.work_code.code | code | TEXT | True | 2 |  | No SQL default | Unbounded SQLite TEXT | Not applicable | Business code within the stated family. |
| warehouseflow_new.work_code.meaning | meaning | TEXT | True |  |  | No SQL default | Unbounded SQLite TEXT | Not applicable | English business meaning of the code in its family. |

```sql
CREATE TABLE work_code(code_family TEXT NOT NULL CHECK(code_family IN ('MOVEMENT','REQUEST','TASK','HANDLING')), code TEXT NOT NULL, meaning TEXT NOT NULL, PRIMARY KEY(code_family,code));
```

### receiving_request

| Element ID | Column | SQL type | Required | PK position | FK | Default | Length | Unit | Definition |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| warehouseflow_new.receiving_request.request_id | request_id | TEXT | True | 1 |  | No SQL default | Unbounded SQLite TEXT | Not applicable | Unique receiving-request identity; foreign references identify the same request. |
| warehouseflow_new.receiving_request.warehouse_id | warehouse_id | TEXT | True |  | warehouse.warehouse_id | No SQL default | Unbounded SQLite TEXT | Not applicable | Unique warehouse identity; foreign references identify the warehouse concerned. |
| warehouseflow_new.receiving_request.goods_id | goods_id | TEXT | True |  | goods.goods_id | No SQL default | Unbounded SQLite TEXT | Not applicable | Unique goods identity; foreign references identify the goods concerned. |
| warehouseflow_new.receiving_request.quantity | quantity | INTEGER | True |  |  | No SQL default | Not applicable | stock units | Positive number of goods units requested or moved. |
| warehouseflow_new.receiving_request.submitted_at | submitted_at | TEXT | True |  |  | No SQL default | Unbounded SQLite TEXT | UTC | Actual UTC receiving-request submission time. |

```sql
CREATE TABLE receiving_request(request_id TEXT PRIMARY KEY NOT NULL, warehouse_id TEXT NOT NULL REFERENCES warehouse(warehouse_id), goods_id TEXT NOT NULL REFERENCES goods(goods_id), quantity INTEGER NOT NULL CHECK(quantity>0), submitted_at TEXT NOT NULL);
```

### goods_receipt

| Element ID | Column | SQL type | Required | PK position | FK | Default | Length | Unit | Definition |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| warehouseflow_new.goods_receipt.receipt_id | receipt_id | TEXT | True | 1 |  | No SQL default | Unbounded SQLite TEXT | Not applicable | Unique receipt-registration identity; on a stock movement, references its receipt registration. |
| warehouseflow_new.goods_receipt.request_id | request_id | TEXT | True |  | receiving_request.request_id | No SQL default | Unbounded SQLite TEXT | Not applicable | Unique receiving-request identity; foreign references identify the same request. |
| warehouseflow_new.goods_receipt.receiver_id | receiver_id | TEXT | True |  | worker.worker_id | No SQL default | Unbounded SQLite TEXT | Not applicable | Worker who registered the actual receipt. |
| warehouseflow_new.goods_receipt.received_at | received_at | TEXT | True |  |  | No SQL default | Unbounded SQLite TEXT | UTC | Actual UTC receipt-registration time. |
| warehouseflow_new.goods_receipt.condition_code | condition_code | TEXT | True |  |  | No SQL default | Unbounded SQLite TEXT | Not applicable | GOOD or DAMAGED condition observed when goods were received. Either value denotes the same kind of receipt registration. |

```sql
CREATE TABLE goods_receipt(receipt_id TEXT PRIMARY KEY NOT NULL, request_id TEXT NOT NULL UNIQUE REFERENCES receiving_request(request_id), receiver_id TEXT NOT NULL REFERENCES worker(worker_id), received_at TEXT NOT NULL, condition_code TEXT NOT NULL CHECK(condition_code IN ('GOOD','DAMAGED')));
```

### dispatch_order

| Element ID | Column | SQL type | Required | PK position | FK | Default | Length | Unit | Definition |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| warehouseflow_new.dispatch_order.dispatch_id | dispatch_id | TEXT | True | 1 |  | No SQL default | Unbounded SQLite TEXT | Not applicable | Unique dispatch-order identity; foreign references identify the same dispatch request. |
| warehouseflow_new.dispatch_order.warehouse_id | warehouse_id | TEXT | True |  | warehouse.warehouse_id | No SQL default | Unbounded SQLite TEXT | Not applicable | Unique warehouse identity; foreign references identify the warehouse concerned. |
| warehouseflow_new.dispatch_order.goods_id | goods_id | TEXT | True |  | goods.goods_id | No SQL default | Unbounded SQLite TEXT | Not applicable | Unique goods identity; foreign references identify the goods concerned. |
| warehouseflow_new.dispatch_order.quantity | quantity | INTEGER | True |  |  | No SQL default | Not applicable | stock units | Positive number of goods units requested or moved. |
| warehouseflow_new.dispatch_order.priority_code | priority_code | TEXT | True |  |  | No SQL default | Unbounded SQLite TEXT | Not applicable | NORMAL or URGENT dispatch urgency; does not identify the action performed. |
| warehouseflow_new.dispatch_order.requested_at | requested_at | TEXT | True |  |  | No SQL default | Unbounded SQLite TEXT | UTC | Actual UTC dispatch-request submission time. |
| warehouseflow_new.dispatch_order.approved_at | approved_at | TEXT | False |  |  | No SQL default | Unbounded SQLite TEXT | UTC | Actual UTC dispatch-approval time; NULL if not yet approved. |

```sql
CREATE TABLE dispatch_order(dispatch_id TEXT PRIMARY KEY NOT NULL, warehouse_id TEXT NOT NULL REFERENCES warehouse(warehouse_id), goods_id TEXT NOT NULL REFERENCES goods(goods_id), quantity INTEGER NOT NULL CHECK(quantity>0), priority_code TEXT NOT NULL CHECK(priority_code IN ('NORMAL','URGENT')), requested_at TEXT NOT NULL, approved_at TEXT, CHECK(approved_at IS NULL OR requested_at<approved_at));
```

### warehouse_audit

| Element ID | Column | SQL type | Required | PK position | FK | Default | Length | Unit | Definition |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| warehouseflow_new.warehouse_audit.audit_id | audit_id | TEXT | True | 1 |  | No SQL default | Unbounded SQLite TEXT | Not applicable | Unique stock-audit occurrence identifier. |
| warehouseflow_new.warehouse_audit.warehouse_id | warehouse_id | TEXT | True |  | warehouse.warehouse_id | No SQL default | Unbounded SQLite TEXT | Not applicable | Unique warehouse identity; foreign references identify the warehouse concerned. |
| warehouseflow_new.warehouse_audit.worker_id | worker_id | TEXT | True |  | worker.worker_id | No SQL default | Unbounded SQLite TEXT | Not applicable | Unique worker identity; on a work or audit record, identifies the worker performing it. |
| warehouseflow_new.warehouse_audit.started_at | started_at | TEXT | True |  |  | No SQL default | Unbounded SQLite TEXT | UTC | Actual UTC start time of this audit or work occurrence. |
| warehouseflow_new.warehouse_audit.completed_at | completed_at | TEXT | False |  |  | No SQL default | Unbounded SQLite TEXT | UTC | Actual UTC completion time of this audit or work occurrence; NULL if unfinished. |
| warehouseflow_new.warehouse_audit.result_code | result_code | TEXT | True |  |  | No SQL default | Unbounded SQLite TEXT | Not applicable | PASS or RECOUNT outcome of a completed stock audit, or PENDING for an unfinished audit. |

```sql
CREATE TABLE warehouse_audit(audit_id TEXT PRIMARY KEY NOT NULL, warehouse_id TEXT NOT NULL REFERENCES warehouse(warehouse_id), worker_id TEXT NOT NULL REFERENCES worker(worker_id), started_at TEXT NOT NULL, completed_at TEXT, result_code TEXT NOT NULL CHECK(result_code IN ('PASS','RECOUNT','PENDING')), CHECK((completed_at IS NULL AND result_code='PENDING') OR (completed_at IS NOT NULL AND started_at<completed_at AND result_code IN ('PASS','RECOUNT'))));
```

### goods_movement

| Element ID | Column | SQL type | Required | PK position | FK | Default | Length | Unit | Definition |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| warehouseflow_new.goods_movement.movement_id | movement_id | TEXT | True | 1 |  | No SQL default | Unbounded SQLite TEXT | Not applicable | Unique stock-movement occurrence identifier. |
| warehouseflow_new.goods_movement.warehouse_id | warehouse_id | TEXT | True |  | warehouse.warehouse_id | No SQL default | Unbounded SQLite TEXT | Not applicable | Unique warehouse identity; foreign references identify the warehouse concerned. |
| warehouseflow_new.goods_movement.goods_id | goods_id | TEXT | True |  | goods.goods_id | No SQL default | Unbounded SQLite TEXT | Not applicable | Unique goods identity; foreign references identify the goods concerned. |
| warehouseflow_new.goods_movement.quantity | quantity | INTEGER | True |  |  | No SQL default | Not applicable | stock units | Positive number of goods units requested or moved. |
| warehouseflow_new.goods_movement.receipt_id | receipt_id | TEXT | False |  | goods_receipt.receipt_id | No SQL default | Unbounded SQLite TEXT | Not applicable | Unique receipt-registration identity; on a stock movement, references its receipt registration. |
| warehouseflow_new.goods_movement.dispatch_id | dispatch_id | TEXT | False |  | dispatch_order.dispatch_id | No SQL default | Unbounded SQLite TEXT | Not applicable | Unique dispatch-order identity; foreign references identify the same dispatch request. |
| warehouseflow_new.goods_movement.code_family | code_family | TEXT | True |  | work_code.code_family | 'MOVEMENT' | Unbounded SQLite TEXT | Not applicable | Business context for the code. Each work table has one fixed family enforced by CHECK. |
| warehouseflow_new.goods_movement.movement_code | movement_code | TEXT | True |  | work_code.code | No SQL default | Unbounded SQLite TEXT | Not applicable | IN means actual receipt into warehouse stock; OUT means actual dispatch from warehouse stock. |
| warehouseflow_new.goods_movement.occurred_at | occurred_at | TEXT | True |  |  | No SQL default | Unbounded SQLite TEXT | UTC | Actual UTC time of this completed stock movement or request action. |

```sql
CREATE TABLE goods_movement(movement_id TEXT PRIMARY KEY NOT NULL, warehouse_id TEXT NOT NULL REFERENCES warehouse(warehouse_id), goods_id TEXT NOT NULL REFERENCES goods(goods_id), quantity INTEGER NOT NULL CHECK(quantity>0), receipt_id TEXT UNIQUE REFERENCES goods_receipt(receipt_id), dispatch_id TEXT UNIQUE REFERENCES dispatch_order(dispatch_id), code_family TEXT NOT NULL DEFAULT 'MOVEMENT' CHECK(code_family='MOVEMENT'), movement_code TEXT NOT NULL, occurred_at TEXT NOT NULL, FOREIGN KEY(code_family,movement_code) REFERENCES work_code(code_family,code), CHECK((movement_code='IN' AND receipt_id IS NOT NULL AND dispatch_id IS NULL) OR (movement_code='OUT' AND receipt_id IS NULL AND dispatch_id IS NOT NULL)));
```

### request_action

| Element ID | Column | SQL type | Required | PK position | FK | Default | Length | Unit | Definition |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| warehouseflow_new.request_action.action_id | action_id | TEXT | True | 1 |  | No SQL default | Unbounded SQLite TEXT | Not applicable | Unique receiving-request action occurrence identifier. |
| warehouseflow_new.request_action.request_id | request_id | TEXT | True |  | receiving_request.request_id | No SQL default | Unbounded SQLite TEXT | Not applicable | Unique receiving-request identity; foreign references identify the same request. |
| warehouseflow_new.request_action.worker_id | worker_id | TEXT | True |  | worker.worker_id | No SQL default | Unbounded SQLite TEXT | Not applicable | Unique worker identity; on a work or audit record, identifies the worker performing it. |
| warehouseflow_new.request_action.code_family | code_family | TEXT | True |  | work_code.code_family | 'REQUEST' | Unbounded SQLite TEXT | Not applicable | Business context for the code. Each work table has one fixed family enforced by CHECK. |
| warehouseflow_new.request_action.action_code | action_code | TEXT | True |  | work_code.code | No SQL default | Unbounded SQLite TEXT | Not applicable | CHECK, HOLD or RELEASE action actually performed on the referenced request, as defined in work_code. |
| warehouseflow_new.request_action.occurred_at | occurred_at | TEXT | True |  |  | No SQL default | Unbounded SQLite TEXT | UTC | Actual UTC time of this completed stock movement or request action. |

```sql
CREATE TABLE request_action(action_id TEXT PRIMARY KEY NOT NULL, request_id TEXT NOT NULL REFERENCES receiving_request(request_id), worker_id TEXT NOT NULL REFERENCES worker(worker_id), code_family TEXT NOT NULL DEFAULT 'REQUEST' CHECK(code_family='REQUEST'), action_code TEXT NOT NULL, occurred_at TEXT NOT NULL, FOREIGN KEY(code_family,action_code) REFERENCES work_code(code_family,code));
```

### warehouse_task_history

| Element ID | Column | SQL type | Required | PK position | FK | Default | Length | Unit | Definition |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| warehouseflow_new.warehouse_task_history.task_id | task_id | TEXT | True | 1 |  | No SQL default | Unbounded SQLite TEXT | Not applicable | Unique task-attempt identifier; repeat work has a new identifier. |
| warehouseflow_new.warehouse_task_history.request_id | request_id | TEXT | False |  | receiving_request.request_id | No SQL default | Unbounded SQLite TEXT | Not applicable | Unique receiving-request identity; foreign references identify the same request. |
| warehouseflow_new.warehouse_task_history.dispatch_id | dispatch_id | TEXT | False |  | dispatch_order.dispatch_id | No SQL default | Unbounded SQLite TEXT | Not applicable | Unique dispatch-order identity; foreign references identify the same dispatch request. |
| warehouseflow_new.warehouse_task_history.worker_id | worker_id | TEXT | True |  | worker.worker_id | No SQL default | Unbounded SQLite TEXT | Not applicable | Unique worker identity; on a work or audit record, identifies the worker performing it. |
| warehouseflow_new.warehouse_task_history.code_family | code_family | TEXT | True |  | work_code.code_family | 'TASK' | Unbounded SQLite TEXT | Not applicable | Business context for the code. Each work table has one fixed family enforced by CHECK. |
| warehouseflow_new.warehouse_task_history.task_code | task_code | TEXT | True |  | work_code.code | No SQL default | Unbounded SQLite TEXT | Not applicable | PUTAWAY, PICK or PACK work actually performed, as defined in work_code. |
| warehouseflow_new.warehouse_task_history.started_at | started_at | TEXT | True |  |  | No SQL default | Unbounded SQLite TEXT | UTC | Actual UTC start time of this audit or work occurrence. |
| warehouseflow_new.warehouse_task_history.completed_at | completed_at | TEXT | False |  |  | No SQL default | Unbounded SQLite TEXT | UTC | Actual UTC completion time of this audit or work occurrence; NULL if unfinished. |
| warehouseflow_new.warehouse_task_history.outcome_code | outcome_code | TEXT | True |  |  | No SQL default | Unbounded SQLite TEXT | Not applicable | OK or RETRY result of a completed task attempt, or PENDING while unfinished; the outcome does not change the kind of work. |

```sql
CREATE TABLE warehouse_task_history(task_id TEXT PRIMARY KEY NOT NULL, request_id TEXT REFERENCES receiving_request(request_id), dispatch_id TEXT REFERENCES dispatch_order(dispatch_id), worker_id TEXT NOT NULL REFERENCES worker(worker_id), code_family TEXT NOT NULL DEFAULT 'TASK' CHECK(code_family='TASK'), task_code TEXT NOT NULL, started_at TEXT NOT NULL, completed_at TEXT, outcome_code TEXT NOT NULL CHECK(outcome_code IN ('OK','RETRY','PENDING')), FOREIGN KEY(code_family,task_code) REFERENCES work_code(code_family,code), CHECK((task_code='PUTAWAY' AND request_id IS NOT NULL AND dispatch_id IS NULL) OR (task_code IN ('PICK','PACK') AND dispatch_id IS NOT NULL AND request_id IS NULL)), CHECK((completed_at IS NULL AND outcome_code='PENDING') OR (completed_at IS NOT NULL AND started_at<completed_at AND outcome_code IN ('OK','RETRY'))));
```

### handling_history

| Element ID | Column | SQL type | Required | PK position | FK | Default | Length | Unit | Definition |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| warehouseflow_new.handling_history.handling_id | handling_id | TEXT | True | 1 |  | No SQL default | Unbounded SQLite TEXT | Not applicable | Unique handling-attempt identifier. |
| warehouseflow_new.handling_history.request_id | request_id | TEXT | False |  | receiving_request.request_id | No SQL default | Unbounded SQLite TEXT | Not applicable | Unique receiving-request identity; foreign references identify the same request. |
| warehouseflow_new.handling_history.dispatch_id | dispatch_id | TEXT | False |  | dispatch_order.dispatch_id | No SQL default | Unbounded SQLite TEXT | Not applicable | Unique dispatch-order identity; foreign references identify the same dispatch request. |
| warehouseflow_new.handling_history.worker_id | worker_id | TEXT | True |  | worker.worker_id | No SQL default | Unbounded SQLite TEXT | Not applicable | Unique worker identity; on a work or audit record, identifies the worker performing it. |
| warehouseflow_new.handling_history.code_family | code_family | TEXT | True |  | work_code.code_family | 'HANDLING' | Unbounded SQLite TEXT | Not applicable | Business context for the code. Each work table has one fixed family enforced by CHECK. |
| warehouseflow_new.handling_history.handling_code | handling_code | TEXT | True |  | work_code.code | No SQL default | Unbounded SQLite TEXT | Not applicable | UNLOAD or LOAD work actually performed, as defined in work_code. |
| warehouseflow_new.handling_history.started_at | started_at | TEXT | True |  |  | No SQL default | Unbounded SQLite TEXT | UTC | Actual UTC start time of this audit or work occurrence. |
| warehouseflow_new.handling_history.completed_at | completed_at | TEXT | False |  |  | No SQL default | Unbounded SQLite TEXT | UTC | Actual UTC completion time of this audit or work occurrence; NULL if unfinished. |

```sql
CREATE TABLE handling_history(handling_id TEXT PRIMARY KEY NOT NULL, request_id TEXT REFERENCES receiving_request(request_id), dispatch_id TEXT REFERENCES dispatch_order(dispatch_id), worker_id TEXT NOT NULL REFERENCES worker(worker_id), code_family TEXT NOT NULL DEFAULT 'HANDLING' CHECK(code_family='HANDLING'), handling_code TEXT NOT NULL, started_at TEXT NOT NULL, completed_at TEXT, FOREIGN KEY(code_family,handling_code) REFERENCES work_code(code_family,code), CHECK((handling_code='UNLOAD' AND request_id IS NOT NULL AND dispatch_id IS NULL) OR (handling_code='LOAD' AND dispatch_id IS NOT NULL AND request_id IS NULL)), CHECK(completed_at IS NULL OR started_at<completed_at));
```

### Business codes

| Code family | Code | Business meaning |
| --- | --- | --- |
| MOVEMENT | IN | Receipt into warehouse stock |
| MOVEMENT | OUT | Dispatch from warehouse stock |
| REQUEST | CHECK | Check receiving request |
| REQUEST | HOLD | Hold receiving request |
| REQUEST | RELEASE | Release receiving request |
| TASK | PUTAWAY | Putaway work |
| TASK | PICK | Picking work |
| TASK | PACK | Packing work |
| HANDLING | UNLOAD | Unloading work |
| HANDLING | LOAD | Loading work |

### Business rules

- Each receiving request and dispatch order concerns one goods type in one warehouse; quantities are positive. This sample does not model multi-line orders.
- One actual receipt registration can exist for each receiving request. Actual stock posting is recorded separately.
- Each movement refers either to an inbound receipt or an outbound dispatch, with the same warehouse and goods context.
- Every work attempt and audit retains its own start and optional completion times. Unfinished work has no completion time.
- Repeated task attempts and request checks retain separate occurrence identifiers.
- Goods category, dispatch urgency, goods condition, worker role, audit result and task outcome describe their respective business contexts rather than different kinds of action.
- A handling/task occurrence refers either to a receiving request or to a dispatch order as constrained by its work kind.
- All rows, code conventions, times and quantities are synthetic.
