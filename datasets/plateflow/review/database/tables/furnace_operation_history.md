# furnace_operation_history

**Rows:** 70 · **Columns:** 7

## Original records (first 10)

| operation_id | material_id | process_group | operation_code | equipment_id | started_at | finished_at |
| --- | --- | --- | --- | --- | --- | --- |
| 0001 | M007 | FURNACE | C | FU2 | 2026-01-25T08:30:00Z | 2026-01-25T08:40:00Z |
| 0002 | M007 | FURNACE | A | FU2 | 2026-01-25T08:45:00Z | 2026-01-25T09:20:00Z |
| 0003 | M007 | FURNACE | D | FU2 | 2026-01-25T09:25:00Z | 2026-01-25T09:30:00Z |
| 0004 | M008 | FURNACE | C | FU1 | 2026-01-28T19:50:00Z | 2026-01-28T20:00:00Z |
| 0005 | M008 | FURNACE | A | FU1 | 2026-01-28T20:05:00Z | 2026-01-28T20:40:00Z |
| 0006 | M008 | FURNACE | D | FU1 | 2026-01-28T20:45:00Z | 2026-01-28T20:50:00Z |
| 0007 | M009 | FURNACE | C | FU2 | 2026-02-01T07:10:00Z | 2026-02-01T07:20:00Z |
| 0008 | M009 | FURNACE | A | FU2 | 2026-02-01T07:25:00Z | 2026-02-01T08:00:00Z |
| 0009 | M009 | FURNACE | D | FU2 | 2026-02-01T08:05:00Z | 2026-02-01T08:10:00Z |
| 0010 | M010 | FURNACE | C | FU1 | 2026-02-04T18:30:00Z | 2026-02-04T18:40:00Z |

## Column definitions

| Column | SQL type | PK | Not null |
|---|---|---|---|
| operation_id | TEXT | True | True |
| material_id | TEXT | False | True |
| process_group | TEXT | False | True |
| operation_code | TEXT | False | True |
| equipment_id | TEXT | False | True |
| started_at | TEXT | False | True |
| finished_at | TEXT | False | False |
