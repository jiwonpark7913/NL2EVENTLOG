# Timestamp inventory — author evaluation material

| Table | Column | Role | Selected as Gold time | Non-null rows |
| --- | --- | --- | --- | --- |
| warehouse | created_at | Technical maintenance instant | False | 4 |
| warehouse | updated_at | Technical maintenance instant | False | 4 |
| worker | updated_at | Technical maintenance instant | False | 7 |
| receiving_request | submitted_at | Selected actual business instant | True | 26 |
| goods_receipt | received_at | Selected actual business instant | True | 23 |
| dispatch_order | requested_at | Selected actual business instant | True | 20 |
| dispatch_order | approved_at | Selected actual business instant | True | 18 |
| warehouse_audit | started_at | Selected actual business instant | True | 9 |
| warehouse_audit | completed_at | Selected actual business instant | True | 8 |
| goods_movement | occurred_at | Selected actual business instant | True | 39 |
| request_action | occurred_at | Selected actual business instant | True | 56 |
| warehouse_task_history | started_at | Selected actual business instant | True | 63 |
| warehouse_task_history | completed_at | Selected actual business instant | True | 60 |
| handling_history | started_at | Selected actual business instant | True | 41 |
| handling_history | completed_at | Selected actual business instant | True | 39 |
