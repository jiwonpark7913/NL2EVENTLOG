# warehouse_audit

**Rows:** 9 · **Columns:** 6

## Original records (first 10)

| audit_id | warehouse_id | worker_id | started_at | completed_at | result_code |
| --- | --- | --- | --- | --- | --- |
| 001 | 1 | 1 | 2026-05-16T05:40:00Z | 2026-05-16T06:20:00Z | PASS |
| 002 | 2 | 2 | 2026-05-16T07:20:00Z | 2026-05-16T08:00:00Z | PASS |
| 003 | 3 | 3 | 2026-05-16T09:00:00Z | 2026-05-16T09:40:00Z | RECOUNT |
| 004 | 1 | 4 | 2026-05-16T10:40:00Z | 2026-05-16T11:20:00Z | PASS |
| 005 | 2 | 5 | 2026-05-16T12:20:00Z | 2026-05-16T13:00:00Z | PASS |
| 006 | 3 | 6 | 2026-05-16T14:00:00Z | 2026-05-16T14:40:00Z | RECOUNT |
| 007 | 1 | 1 | 2026-05-16T15:40:00Z | 2026-05-16T16:20:00Z | PASS |
| 008 | 2 | 2 | 2026-05-16T17:20:00Z | 2026-05-16T18:00:00Z | PASS |
| 009 | 3 | 3 | 2026-05-16T19:00:00Z | NULL | PENDING |

## Column definitions

| Column | SQL type | PK | Not null |
|---|---|---|---|
| audit_id | TEXT | True | True |
| warehouse_id | TEXT | False | True |
| worker_id | TEXT | False | True |
| started_at | TEXT | False | True |
| completed_at | TEXT | False | False |
| result_code | TEXT | False | True |
