# course

**Rows:** 6 · **Columns:** 10

## Original records (first 10)

| course_id | course_name | credits | instructor | class_time | class_location | course_offering_proposed_at | course_offering_approved_at | course_offering_published_at | course_offering_closed_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C01 | Database Systems | 3 | Instructor 1 | Monday 09:00 | Room 001 | 2026-02-04T11:00:00Z | 2026-02-05T11:00:00Z | 2026-02-06T11:00:00Z | NULL |
| C02 | Statistics | 3 | Instructor 2 | Monday 09:00 | Room 002 | 2026-02-05T12:00:00Z | 2026-02-06T12:00:00Z | 2026-02-07T12:00:00Z | 2026-04-07T12:00:00Z |
| C03 | Operations Research | 3 | Instructor 3 | Monday 09:00 | Room 003 | 2026-02-24T13:00:00Z | 2026-02-25T13:00:00Z | 2026-02-26T13:00:00Z | 2026-04-07T13:00:00Z |
| C04 | Programming | 3 | Instructor 4 | Monday 09:00 | Room 004 | 2026-02-05T14:00:00Z | 2026-02-06T14:00:00Z | 2026-02-07T14:00:00Z | 2026-04-14T14:00:00Z |
| C05 | Economics | 3 | Instructor 5 | Monday 09:00 | Room 005 | 2026-02-05T15:00:00Z | 2026-02-06T15:00:00Z | 2026-02-07T15:00:00Z | 2026-04-15T15:00:00Z |
| C06 | Process Mining | 3 | Instructor 6 | Monday 09:00 | Room 006 | 2026-02-04T16:00:00Z | 2026-02-05T16:00:00Z | 2026-02-06T16:00:00Z | 2026-04-14T16:00:00Z |

## Column definitions

| Column | SQL type | PK | Not null |
|---|---|---|---|
| course_id | TEXT | True | True |
| course_name | TEXT | False | True |
| credits | INTEGER | False | True |
| instructor | TEXT | False | True |
| class_time | TEXT | False | True |
| class_location | TEXT | False | True |
| course_offering_proposed_at | TEXT | False | False |
| course_offering_approved_at | TEXT | False | False |
| course_offering_published_at | TEXT | False | False |
| course_offering_closed_at | TEXT | False | False |
