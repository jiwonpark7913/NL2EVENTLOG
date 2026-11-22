# dimension_inspection

**Rows:** 46 · **Columns:** 5

## Original records (first 10)

| inspection_id | plate_id | inspected_at | result_code | thickness_mm |
| --- | --- | --- | --- | --- |
| P007-1-1 | P007-1 | 2026-01-25T20:35:00Z | FAIL | 22.5 |
| P007-1-2 | P007-1 | 2026-01-25T21:55:00Z | PASS | 20.1 |
| P007-2-1 | P007-2 | 2026-01-26T04:55:00Z | PASS | 20.1 |
| P008-1-1 | P008-1 | 2026-01-29T07:55:00Z | PASS | 20.1 |
| P008-2-1 | P008-2 | 2026-01-29T16:15:00Z | PASS | 20.1 |
| P008-3-1 | P008-3 | 2026-01-30T00:35:00Z | PASS | 20.1 |
| P009-1-1 | P009-1 | 2026-02-01T19:15:00Z | PASS | 20.1 |
| P010-1-1 | P010-1 | 2026-02-05T06:35:00Z | PASS | 20.1 |
| P010-2-1 | P010-2 | 2026-02-05T14:55:00Z | FAIL | 22.5 |
| P010-2-2 | P010-2 | 2026-02-05T16:15:00Z | PASS | 20.1 |

## Column definitions

| Column | SQL type | PK | Not null |
|---|---|---|---|
| inspection_id | TEXT | True | True |
| plate_id | TEXT | False | True |
| inspected_at | TEXT | False | True |
| result_code | TEXT | False | True |
| thickness_mm | REAL | False | True |
