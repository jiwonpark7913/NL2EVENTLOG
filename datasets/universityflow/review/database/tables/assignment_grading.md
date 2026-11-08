# assignment_grading

**Rows:** 25 · **Columns:** 7

## Original records (first 10)

| assignment_id | instructor_id | grading_time | score | evaluation | grading_kind | reassessment_event_id |
| --- | --- | --- | --- | --- | --- | --- |
| A002 | I03 | 2026-02-11T14:00:00Z | 70 | Initial feedback | A | NULL |
| A003 | I01 | 2026-02-12T14:00:00Z | 70 | Initial feedback | A | NULL |
| A006 | I01 | 2026-02-15T14:00:00Z | 70 | Initial feedback | A | NULL |
| A007 | I02 | 2026-02-16T14:00:00Z | 70 | Initial feedback | A | NULL |
| A007 | I02 | 2026-02-17T14:00:00Z | 80 | Revised feedback | A | NULL |
| A011 | I03 | 2026-02-20T14:00:00Z | 70 | Initial feedback | A | NULL |
| A014 | I03 | 2026-02-23T14:00:00Z | 70 | Initial feedback | A | NULL |
| A014 | I03 | 2026-02-24T14:00:00Z | 80 | Revised feedback | A | NULL |
| A018 | I01 | 2026-02-27T14:00:00Z | 70 | Initial feedback | A | NULL |
| A019 | I02 | 2026-02-28T14:00:00Z | 70 | Initial feedback | A | NULL |

## Column definitions

| Column | SQL type | PK | Not null |
|---|---|---|---|
| assignment_id | TEXT | True | True |
| instructor_id | TEXT | True | True |
| grading_time | TEXT | True | True |
| score | INTEGER | False | True |
| evaluation | TEXT | False | True |
| grading_kind | TEXT | False | True |
| reassessment_event_id | TEXT | False | False |
