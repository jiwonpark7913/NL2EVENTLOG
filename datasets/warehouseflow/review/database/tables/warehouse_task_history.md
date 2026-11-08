# warehouse_task_history

**Rows:** 63 · **Columns:** 9

## Original records (first 10)

| task_id | request_id | dispatch_id | worker_id | code_family | task_code | started_at | completed_at | outcome_code |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0001 | 001 | NULL | 1 | TASK | A | 2026-02-01T05:40:00Z | 2026-02-01T05:50:00Z | OK |
| 0002 | 002 | NULL | 2 | TASK | A | 2026-02-01T10:40:00Z | 2026-02-01T10:50:00Z | OK |
| 0003 | 003 | NULL | 3 | TASK | A | 2026-02-01T15:40:00Z | 2026-02-01T15:50:00Z | OK |
| 0004 | 004 | NULL | 4 | TASK | A | 2026-02-01T20:40:00Z | 2026-02-01T20:50:00Z | OK |
| 0005 | 005 | NULL | 5 | TASK | A | 2026-02-02T01:40:00Z | 2026-02-02T01:50:00Z | OK |
| 0006 | 006 | NULL | 6 | TASK | A | 2026-02-02T06:40:00Z | 2026-02-02T06:50:00Z | OK |
| 0007 | 007 | NULL | 1 | TASK | A | 2026-02-02T11:40:00Z | 2026-02-02T11:50:00Z | OK |
| 0008 | 008 | NULL | 2 | TASK | A | 2026-02-02T16:40:00Z | 2026-02-02T16:50:00Z | OK |
| 0009 | 009 | NULL | 3 | TASK | A | 2026-02-02T21:40:00Z | 2026-02-02T21:50:00Z | OK |
| 0010 | 010 | NULL | 4 | TASK | A | 2026-02-03T02:40:00Z | 2026-02-03T02:50:00Z | OK |

## Column definitions

| Column | SQL type | PK | Not null |
|---|---|---|---|
| task_id | TEXT | True | True |
| request_id | TEXT | False | False |
| dispatch_id | TEXT | False | False |
| worker_id | TEXT | False | True |
| code_family | TEXT | False | True |
| task_code | TEXT | False | True |
| started_at | TEXT | False | True |
| completed_at | TEXT | False | False |
| outcome_code | TEXT | False | True |
