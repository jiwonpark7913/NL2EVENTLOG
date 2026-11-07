# assignment

**Rows:** 20 · **Columns:** 8

## Original records (first 10)

| assignment_id | student_id | assignment_content | assignment_assigned_at | assignment_submitted_at | assignment_grade_finalized_at | assignment_revision_requested_at | assignment_resubmitted_at |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A002 | S002 | Synthetic assignment content | 2026-02-07T14:00:00Z | 2026-02-09T14:00:00Z | NULL | 2026-02-11T15:00:00Z | 2026-02-12T14:00:00Z |
| A003 | S003 | Synthetic assignment content | 2026-02-08T14:00:00Z | 2026-02-10T14:00:00Z | 2026-02-14T14:00:00Z | NULL | NULL |
| A006 | S006 | Synthetic assignment content | 2026-02-11T14:00:00Z | 2026-02-13T14:00:00Z | 2026-02-17T14:00:00Z | NULL | NULL |
| A007 | S007 | Synthetic assignment content | 2026-02-12T14:00:00Z | 2026-02-14T14:00:00Z | 2026-02-19T14:00:00Z | 2026-02-16T15:00:00Z | 2026-02-17T14:00:00Z |
| A010 | S010 | Synthetic assignment content | 2026-01-03T00:00:00Z | NULL | NULL | NULL | NULL |
| A011 | S011 | Synthetic assignment content | 2026-02-16T14:00:00Z | 2026-02-18T14:00:00Z | 2026-02-22T14:00:00Z | NULL | NULL |
| A014 | S014 | Synthetic assignment content | 2026-02-19T14:00:00Z | 2026-02-21T14:00:00Z | 2026-02-26T14:00:00Z | 2026-02-23T15:00:00Z | 2026-02-24T14:00:00Z |
| A015 | S015 | Synthetic assignment content | 2026-01-06T00:00:00Z | NULL | NULL | NULL | NULL |
| A018 | S018 | Synthetic assignment content | 2026-02-23T14:00:00Z | 2026-02-25T14:00:00Z | 2026-03-01T14:00:00Z | NULL | NULL |
| A019 | S019 | Synthetic assignment content | 2026-02-24T14:00:00Z | 2026-02-26T14:00:00Z | 2026-03-02T14:00:00Z | 2026-02-28T15:00:00Z | 2026-03-01T14:00:00Z |

## Column definitions

| Column | SQL type | PK | Not null |
|---|---|---|---|
| assignment_id | TEXT | True | True |
| student_id | TEXT | False | True |
| assignment_content | TEXT | False | True |
| assignment_assigned_at | TEXT | False | False |
| assignment_submitted_at | TEXT | False | False |
| assignment_grade_finalized_at | TEXT | False | False |
| assignment_revision_requested_at | TEXT | False | False |
| assignment_resubmitted_at | TEXT | False | False |
