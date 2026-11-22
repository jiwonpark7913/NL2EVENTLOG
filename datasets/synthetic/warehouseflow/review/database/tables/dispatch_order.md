# dispatch_order

**Rows:** 20 · **Columns:** 7

## Original records (first 10)

| dispatch_id | warehouse_id | goods_id | quantity | priority_code | requested_at | approved_at |
| --- | --- | --- | --- | --- | --- | --- |
| 001 | 1 | 1 | 4 | NORMAL | 2026-04-11T15:40:00Z | 2026-04-11T15:50:00Z |
| 002 | 2 | 2 | 4 | NORMAL | 2026-04-11T20:40:00Z | 2026-04-11T20:50:00Z |
| 003 | 3 | 3 | 4 | URGENT | 2026-04-12T01:40:00Z | 2026-04-12T01:50:00Z |
| 004 | 1 | 4 | 4 | NORMAL | 2026-04-12T06:40:00Z | 2026-04-12T06:50:00Z |
| 005 | 2 | 5 | 4 | NORMAL | 2026-04-12T11:40:00Z | 2026-04-12T11:50:00Z |
| 006 | 3 | 6 | 4 | URGENT | 2026-04-12T16:40:00Z | 2026-04-12T16:50:00Z |
| 007 | 1 | 1 | 4 | NORMAL | 2026-04-12T21:40:00Z | 2026-04-12T21:50:00Z |
| 008 | 2 | 2 | 4 | NORMAL | 2026-04-13T02:40:00Z | 2026-04-13T02:50:00Z |
| 009 | 3 | 3 | 4 | URGENT | 2026-04-13T07:40:00Z | 2026-04-13T07:50:00Z |
| 010 | 1 | 4 | 4 | NORMAL | 2026-04-13T12:40:00Z | 2026-04-13T12:50:00Z |

## Column definitions

| Column | SQL type | PK | Not null |
|---|---|---|---|
| dispatch_id | TEXT | True | True |
| warehouse_id | TEXT | False | True |
| goods_id | TEXT | False | True |
| quantity | INTEGER | False | True |
| priority_code | TEXT | False | True |
| requested_at | TEXT | False | True |
| approved_at | TEXT | False | False |
