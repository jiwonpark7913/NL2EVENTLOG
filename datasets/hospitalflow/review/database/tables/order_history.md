# order_history

**Rows:** 203 · **Columns:** 6

## Original records (first 10)

| history_id | lab_order_id | medication_order_id | procedure_order_id | action | occurred_at |
| --- | --- | --- | --- | --- | --- |
| 1 | NULL | 32064975 | NULL | E | 2026-01-17T17:00:00Z |
| 2 | NULL | 32064975 | NULL | R | 2026-01-17T17:22:00Z |
| 3 | NULL | 32064975 | NULL | R | 2026-01-17T17:39:00Z |
| 4 | NULL | 32028896 | NULL | E | 2026-01-17T18:25:00Z |
| 5 | NULL | 32028896 | NULL | R | 2026-01-17T18:44:00Z |
| 6 | 31070762 | NULL | NULL | E | 2026-01-27T14:03:00Z |
| 7 | 31070762 | NULL | NULL | R | 2026-01-27T15:14:00Z |
| 8 | 31070762 | NULL | NULL | R | 2026-01-27T15:23:00Z |
| 9 | NULL | NULL | 33032683 | E | 2026-01-27T13:55:00Z |
| 10 | NULL | NULL | 33032683 | R | 2026-01-27T15:11:00Z |

## Column definitions

| Column | SQL type | PK | Not null |
|---|---|---|---|
| history_id | INTEGER | True | True |
| lab_order_id | INTEGER | False | False |
| medication_order_id | INTEGER | False | False |
| procedure_order_id | INTEGER | False | False |
| action | TEXT | False | True |
| occurred_at | TEXT | False | True |
