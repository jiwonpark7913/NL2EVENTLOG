# goods_movement

**Rows:** 39 · **Columns:** 9

## Original records (first 10)

| movement_id | warehouse_id | goods_id | quantity | receipt_id | dispatch_id | code_family | movement_code | occurred_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0001 | 1 | 1 | 10 | 001 | NULL | MOVEMENT | I | 2026-02-01T05:35:00Z |
| 0002 | 2 | 2 | 10 | 002 | NULL | MOVEMENT | I | 2026-02-01T10:35:00Z |
| 0003 | 3 | 3 | 10 | 003 | NULL | MOVEMENT | I | 2026-02-01T15:35:00Z |
| 0004 | 1 | 4 | 10 | 004 | NULL | MOVEMENT | I | 2026-02-01T20:35:00Z |
| 0005 | 2 | 5 | 10 | 005 | NULL | MOVEMENT | I | 2026-02-02T01:35:00Z |
| 0006 | 3 | 6 | 10 | 006 | NULL | MOVEMENT | I | 2026-02-02T06:35:00Z |
| 0007 | 1 | 1 | 10 | 007 | NULL | MOVEMENT | I | 2026-02-02T11:35:00Z |
| 0008 | 2 | 2 | 10 | 008 | NULL | MOVEMENT | I | 2026-02-02T16:35:00Z |
| 0009 | 3 | 3 | 10 | 009 | NULL | MOVEMENT | I | 2026-02-02T21:35:00Z |
| 0010 | 1 | 4 | 10 | 010 | NULL | MOVEMENT | I | 2026-02-03T02:35:00Z |

## Column definitions

| Column | SQL type | PK | Not null |
|---|---|---|---|
| movement_id | TEXT | True | True |
| warehouse_id | TEXT | False | True |
| goods_id | TEXT | False | True |
| quantity | INTEGER | False | True |
| receipt_id | TEXT | False | False |
| dispatch_id | TEXT | False | False |
| code_family | TEXT | False | True |
| movement_code | TEXT | False | True |
| occurred_at | TEXT | False | True |
