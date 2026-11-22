# goods_receipt

**Rows:** 23 · **Columns:** 5

## Original records (first 10)

| receipt_id | request_id | receiver_id | received_at | condition_code |
| --- | --- | --- | --- | --- |
| 001 | 001 | 1 | 2026-02-01T05:32:00Z | GOOD |
| 002 | 002 | 2 | 2026-02-01T10:32:00Z | GOOD |
| 003 | 003 | 3 | 2026-02-01T15:32:00Z | GOOD |
| 004 | 004 | 4 | 2026-02-01T20:32:00Z | GOOD |
| 005 | 005 | 5 | 2026-02-02T01:32:00Z | GOOD |
| 006 | 006 | 6 | 2026-02-02T06:32:00Z | GOOD |
| 007 | 007 | 1 | 2026-02-02T11:32:00Z | DAMAGED |
| 008 | 008 | 2 | 2026-02-02T16:32:00Z | GOOD |
| 009 | 009 | 3 | 2026-02-02T21:32:00Z | GOOD |
| 010 | 010 | 4 | 2026-02-03T02:32:00Z | GOOD |

## Column definitions

| Column | SQL type | PK | Not null |
|---|---|---|---|
| receipt_id | TEXT | True | True |
| request_id | TEXT | False | True |
| receiver_id | TEXT | False | True |
| received_at | TEXT | False | True |
| condition_code | TEXT | False | True |
