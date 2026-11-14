# warehouseflow — 식별자와 대상 참조 목록

실제 SQLite의 전체 PK·UNIQUE·FK를 조사한 구조 목록이다. ET 예측이나 table→ET Gold가 아니다.

[개념 설명](../../../docs/system/ENTITY_IDENTITY_AND_STORAGE.md) · [저장 사례](../../ENTITY_STORAGE_CASES.md)

| Table | Rows | 완전한 PK | UNIQUE 인덱스 | 선언된 참조 |
|---|---:|---|---|---|
| dispatch_order | 20 | dispatch_id | (dispatch_id) | (goods_id) → goods(goods_id); (warehouse_id) → warehouse(warehouse_id) |
| goods | 7 | goods_id | (goods_id) |  |
| goods_movement | 39 | movement_id | (dispatch_id); (receipt_id); (movement_id) | (code_family, movement_code) → work_code(code_family, code); (dispatch_id) → dispatch_order(dispatch_id); (receipt_id) → goods_receipt(receipt_id); (goods_id) → goods(goods_id); (warehouse_id) → warehouse(warehouse_id) |
| goods_receipt | 23 | receipt_id | (request_id); (receipt_id) | (receiver_id) → worker(worker_id); (request_id) → receiving_request(request_id) |
| handling_history | 41 | handling_id | (handling_id) | (code_family, handling_code) → work_code(code_family, code); (worker_id) → worker(worker_id); (dispatch_id) → dispatch_order(dispatch_id); (request_id) → receiving_request(request_id) |
| receiving_request | 26 | request_id | (request_id) | (goods_id) → goods(goods_id); (warehouse_id) → warehouse(warehouse_id) |
| request_action | 56 | action_id | (action_id) | (code_family, action_code) → work_code(code_family, code); (worker_id) → worker(worker_id); (request_id) → receiving_request(request_id) |
| warehouse | 4 | warehouse_id | (warehouse_id) |  |
| warehouse_audit | 9 | audit_id | (audit_id) | (worker_id) → worker(worker_id); (warehouse_id) → warehouse(warehouse_id) |
| warehouse_task_history | 63 | task_id | (task_id) | (code_family, task_code) → work_code(code_family, code); (worker_id) → worker(worker_id); (dispatch_id) → dispatch_order(dispatch_id); (request_id) → receiving_request(request_id) |
| work_code | 10 | code_family, code | (code_family, code) |  |
| worker | 7 | worker_id | (payroll_no); (worker_id) |  |
| worker_contact | 3 | staff_no | (staff_no) | (staff_no) → worker(payroll_no) |

UNIQUE 인덱스에는 PK 인덱스도 포함될 수 있다. NULL 허용 UNIQUE는 전체 행의 완전한 식별을 보장하지 않는다. FK가 없는 동일성은 이 구조 목록만으로 판별할 수 없다.
