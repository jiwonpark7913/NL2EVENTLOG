# rolling_operation_history

**Rows:** 44 · **Columns:** 7

## Original records (first 10)

| operation_id | material_id | process_group | phase_code | equipment_id | started_at | finished_at |
| --- | --- | --- | --- | --- | --- | --- |
| 0001 | M007 | ROLLING | R | RO2 | 2026-01-25T09:40:00Z | 2026-01-25T10:00:00Z |
| 0002 | M007 | ROLLING | F | RO2 | 2026-01-25T10:10:00Z | 2026-01-25T10:35:00Z |
| 0003 | M008 | ROLLING | R | RO1 | 2026-01-28T21:00:00Z | 2026-01-28T21:20:00Z |
| 0004 | M008 | ROLLING | F | RO1 | 2026-01-28T21:30:00Z | 2026-01-28T21:55:00Z |
| 0005 | M009 | ROLLING | R | RO2 | 2026-02-01T08:20:00Z | 2026-02-01T08:40:00Z |
| 0006 | M009 | ROLLING | F | RO2 | 2026-02-01T08:50:00Z | 2026-02-01T09:15:00Z |
| 0007 | M010 | ROLLING | R | RO1 | 2026-02-04T19:40:00Z | 2026-02-04T20:00:00Z |
| 0008 | M010 | ROLLING | F | RO1 | 2026-02-04T20:10:00Z | 2026-02-04T20:35:00Z |
| 0009 | M012 | ROLLING | R | RO1 | 2026-02-11T18:20:00Z | 2026-02-11T18:40:00Z |
| 0010 | M012 | ROLLING | F | RO1 | 2026-02-11T18:50:00Z | 2026-02-11T19:15:00Z |

## Column definitions

| Column | SQL type | PK | Not null |
|---|---|---|---|
| operation_id | TEXT | True | True |
| material_id | TEXT | False | True |
| process_group | TEXT | False | True |
| phase_code | TEXT | False | True |
| equipment_id | TEXT | False | True |
| started_at | TEXT | False | True |
| finished_at | TEXT | False | False |
