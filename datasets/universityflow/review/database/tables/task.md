# task

**Rows:** 3 · **Columns:** 10

## Original records (first 10)

| task_id | task_title | task_description | task_start_date | task_end_date | task_location | design_task_created_at | design_task_approved_at | design_task_published_at | design_task_closed_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| T01 | Course Design Task 1 | Analyze simulation output | 2026-02-01 | 2026-05-31 | Teaching Laboratory | 2025-12-31T00:00:00Z | 2026-01-01T00:00:00Z | 2026-01-02T00:00:00Z | NULL |
| T02 | Course Design Task 2 | Analyze simulation output | 2026-02-01 | 2026-05-31 | Teaching Laboratory | 2026-01-01T00:00:00Z | 2026-01-02T00:00:00Z | 2026-01-03T00:00:00Z | 2026-02-03T00:00:00Z |
| T03 | Course Design Task 3 | Analyze simulation output | 2026-02-01 | 2026-05-31 | Teaching Laboratory | 2026-01-02T00:00:00Z | 2026-01-03T00:00:00Z | 2026-01-04T00:00:00Z | 2026-02-04T00:00:00Z |

## Column definitions

| Column | SQL type | PK | Not null |
|---|---|---|---|
| task_id | TEXT | True | True |
| task_title | TEXT | False | True |
| task_description | TEXT | False | True |
| task_start_date | TEXT | False | True |
| task_end_date | TEXT | False | True |
| task_location | TEXT | False | True |
| design_task_created_at | TEXT | False | False |
| design_task_approved_at | TEXT | False | False |
| design_task_published_at | TEXT | False | False |
| design_task_closed_at | TEXT | False | False |
