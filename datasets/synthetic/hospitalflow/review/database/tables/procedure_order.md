# procedure_order

**Rows:** 17 · **Columns:** 4

## Original records (first 10)

| order_id | hadm_id | procedure_name | preparation_completed_at |
| --- | --- | --- | --- |
| 30000117 | 20000011 | Wound Debridement | NULL |
| 30000691 | 20000007 | Bronchoscopy | 2026-03-08T20:31:00Z |
| 30000983 | 20000008 | Endoscopy | 2026-03-18T20:27:00Z |
| 33023112 | 20000015 | Wound Debridement | 2026-07-03T15:31:00Z |
| 33032683 | 20000002 | Bronchoscopy | 2026-01-27T16:50:00Z |
| 33043088 | 20000010 | Endoscopy | 2026-04-11T03:41:00Z |
| 33050292 | 20000008 | Endoscopy | NULL |
| 33058137 | 20000008 | Wound Debridement | 2026-03-18T22:26:00Z |
| 33059272 | 20000015 | Endoscopy | 2026-07-03T11:24:00Z |
| 33060273 | 20000004 | Endoscopy | NULL |

## Column definitions

| Column | SQL type | PK | Not null |
|---|---|---|---|
| order_id | INTEGER | True | True |
| hadm_id | INTEGER | False | True |
| procedure_name | TEXT | False | True |
| preparation_completed_at | TEXT | False | False |
