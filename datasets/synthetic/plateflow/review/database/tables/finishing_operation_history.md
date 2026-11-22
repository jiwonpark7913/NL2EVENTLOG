# finishing_operation_history

**Rows:** 130 · **Columns:** 7

## Original records (first 10)

| operation_id | plate_id | process_group | operation_code | equipment_id | started_at | finished_at |
| --- | --- | --- | --- | --- | --- | --- |
| 0001 | P007-1 | FINISHING | L | FI1 | 2026-01-25T19:35:00Z | 2026-01-25T19:45:00Z |
| 0002 | P007-1 | FINISHING | A | FI1 | 2026-01-25T19:50:00Z | 2026-01-25T20:10:00Z |
| 0003 | P007-1 | FINISHING | S | FI1 | 2026-01-25T20:15:00Z | 2026-01-25T20:25:00Z |
| 0004 | P007-1 | FINISHING | A | FI1 | 2026-01-25T21:00:00Z | 2026-01-25T21:30:00Z |
| 0005 | P007-1 | FINISHING | S | FI1 | 2026-01-25T21:35:00Z | 2026-01-25T21:45:00Z |
| 0006 | P007-2 | FINISHING | L | FI2 | 2026-01-26T03:55:00Z | 2026-01-26T04:05:00Z |
| 0007 | P007-2 | FINISHING | A | FI2 | 2026-01-26T04:10:00Z | 2026-01-26T04:30:00Z |
| 0008 | P007-2 | FINISHING | S | FI2 | 2026-01-26T04:35:00Z | 2026-01-26T04:45:00Z |
| 0009 | P008-1 | FINISHING | L | FI2 | 2026-01-29T06:55:00Z | 2026-01-29T07:05:00Z |
| 0010 | P008-1 | FINISHING | A | FI2 | 2026-01-29T07:10:00Z | 2026-01-29T07:30:00Z |

## Column definitions

| Column | SQL type | PK | Not null |
|---|---|---|---|
| operation_id | TEXT | True | True |
| plate_id | TEXT | False | True |
| process_group | TEXT | False | True |
| operation_code | TEXT | False | True |
| equipment_id | TEXT | False | True |
| started_at | TEXT | False | True |
| finished_at | TEXT | False | False |
