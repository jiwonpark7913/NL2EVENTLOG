# transfers

**Rows:** 38 · **Columns:** 7

## Original records (first 10)

| subject_id | hadm_id | transfer_id | eventtype | careunit | intime | outtime |
| --- | --- | --- | --- | --- | --- | --- |
| 10000001 | 20000001 | 80000001 | admit | Medical Ward | 2026-01-17T16:12:00Z | 2026-01-18T13:16:03Z |
| 10000001 | 20000001 | 80000002 | transfer | Surgical Ward | 2026-01-18T13:16:03Z | 2026-01-19T15:01:00Z |
| 10000001 | 20000001 | 80000003 | discharge | NULL | 2026-01-19T15:01:00Z | NULL |
| 10000001 | 20000002 | 80000004 | admit | Medical Ward | 2026-01-27T13:19:00Z | 2026-01-28T13:25:45Z |
| 10000001 | 20000002 | 80000005 | transfer | Step-Down Unit | 2026-01-28T13:25:45Z | 2026-01-29T18:54:00Z |
| 10000001 | 20000002 | 80000006 | discharge | NULL | 2026-01-29T18:54:00Z | NULL |
| 10000002 | 20000003 | 80000007 | admit | Medical Ward | 2026-02-03T09:23:00Z | 2026-02-08T20:38:00Z |
| 10000002 | 20000003 | 80000008 | discharge | NULL | 2026-02-08T20:38:00Z | NULL |
| 10000002 | 20000004 | 80000009 | admit | Medical Ward | 2026-02-14T22:40:00Z | 2026-02-17T00:37:00Z |
| 10000002 | 20000004 | 80000010 | transfer | Surgical Ward | 2026-02-17T00:37:00Z | 2026-02-19T13:40:00Z |

## Column definitions

| Column | SQL type | PK | Not null |
|---|---|---|---|
| subject_id | INTEGER | False | True |
| hadm_id | INTEGER | False | False |
| transfer_id | INTEGER | True | True |
| eventtype | TEXT | False | False |
| careunit | TEXT | False | False |
| intime | TEXT | False | False |
| outtime | TEXT | False | False |
