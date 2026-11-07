# medication_order

**Rows:** 29 · **Columns:** 4

## Original records (first 10)

| order_id | hadm_id | medication | stopped_at |
| --- | --- | --- | --- |
| 30000117 | 20000010 | Metformin | 2026-04-11T22:04:00Z |
| 30000691 | 20000007 | Omeprazole | 2026-03-09T18:11:00Z |
| 30000983 | 20000013 | Amoxicillin | 2026-05-31T17:45:00Z |
| 32001707 | 20000010 | Metformin | 2026-04-11T20:08:00Z |
| 32010923 | 20000014 | Amoxicillin | NULL |
| 32021335 | 20000009 | Amoxicillin | 2026-03-26T15:14:00Z |
| 32025317 | 20000007 | Acetaminophen | 2026-03-09T11:48:00Z |
| 32028896 | 20000001 | Acetaminophen | 2026-01-18T20:48:00Z |
| 32034073 | 20000007 | Metformin | 2026-03-09T14:41:00Z |
| 32034941 | 20000010 | Metformin | NULL |

## Column definitions

| Column | SQL type | PK | Not null |
|---|---|---|---|
| order_id | INTEGER | True | True |
| hadm_id | INTEGER | False | True |
| medication | TEXT | False | True |
| stopped_at | TEXT | False | False |
