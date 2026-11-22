# registration

**Rows:** 47 · **Columns:** 9

## Original records (first 10)

| student_id | course_id | registration_time | status | registration_requested_at | registration_approved_at | course_started_at | course_assessment_completed_at | course_grade_finalized_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| S002 | C01 | 2026-02-07T11:00:00Z | REGISTERED | 2026-02-07T07:00:00Z | 2026-02-07T09:00:00Z | 2026-02-09T11:00:00Z | 2026-02-27T11:00:00Z | NULL |
| S002 | C06 | 2026-02-07T16:00:00Z | REGISTERED | 2026-02-07T12:00:00Z | 2026-02-07T14:00:00Z | 2026-02-09T16:00:00Z | 2026-02-27T16:00:00Z | 2026-03-01T16:00:00Z |
| S003 | C02 | 2026-02-08T12:00:00Z | REGISTERED | 2026-02-08T08:00:00Z | 2026-02-08T10:00:00Z | 2026-02-10T12:00:00Z | 2026-02-28T12:00:00Z | 2026-03-02T12:00:00Z |
| S003 | C05 | 2026-02-08T15:00:00Z | REGISTERED | 2026-02-08T11:00:00Z | 2026-02-08T13:00:00Z | 2026-02-10T15:00:00Z | 2026-02-28T15:00:00Z | 2026-03-02T15:00:00Z |
| S003 | C04 | 2026-02-08T14:00:00Z | REGISTERED | 2026-02-08T10:00:00Z | 2026-02-08T12:00:00Z | 2026-02-10T14:00:00Z | 2026-02-28T14:00:00Z | 2026-03-02T14:00:00Z |
| S006 | C06 | 2026-02-11T16:00:00Z | REGISTERED | 2026-02-11T12:00:00Z | 2026-02-11T14:00:00Z | 2026-02-13T16:00:00Z | 2026-03-03T16:00:00Z | 2026-03-05T16:00:00Z |
| S006 | C04 | 2026-02-11T14:00:00Z | REGISTERED | 2026-02-11T10:00:00Z | 2026-02-11T12:00:00Z | 2026-02-13T14:00:00Z | 2026-03-03T14:00:00Z | 2026-03-05T14:00:00Z |
| S006 | C02 | 2026-02-11T12:00:00Z | REGISTERED | 2026-02-11T08:00:00Z | 2026-02-11T10:00:00Z | 2026-02-13T12:00:00Z | 2026-03-03T12:00:00Z | NULL |
| S007 | C01 | 2026-02-12T11:00:00Z | REGISTERED | 2026-02-12T07:00:00Z | 2026-02-12T09:00:00Z | 2026-02-14T11:00:00Z | 2026-03-04T11:00:00Z | 2026-03-06T11:00:00Z |
| S007 | C02 | 2026-02-12T12:00:00Z | REGISTERED | 2026-02-12T08:00:00Z | 2026-02-12T10:00:00Z | 2026-02-14T12:00:00Z | 2026-03-04T12:00:00Z | 2026-03-06T12:00:00Z |

## Column definitions

| Column | SQL type | PK | Not null |
|---|---|---|---|
| student_id | TEXT | True | True |
| course_id | TEXT | True | True |
| registration_time | TEXT | False | True |
| status | TEXT | False | True |
| registration_requested_at | TEXT | False | False |
| registration_approved_at | TEXT | False | False |
| course_started_at | TEXT | False | False |
| course_assessment_completed_at | TEXT | False | False |
| course_grade_finalized_at | TEXT | False | False |
