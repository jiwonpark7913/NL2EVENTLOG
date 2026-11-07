# planned_rolling_instruction

**Rows:** 28 · **Columns:** 6

## Original records (first 10)

| plan_id | slab_id | planned_reheat_at | submitted_at | approved_at | released_at |
| --- | --- | --- | --- | --- | --- |
| L003 | S003 | 2026-01-11T18:20:00Z | 2026-01-11T10:30:00Z | NULL | NULL |
| L004 | S004 | 2026-01-15T05:40:00Z | 2026-01-14T21:50:00Z | NULL | NULL |
| L005 | S005 | 2026-01-18T17:00:00Z | 2026-01-18T09:10:00Z | 2026-01-18T09:20:00Z | 2026-01-18T09:30:00Z |
| L006 | S006 | 2026-01-22T04:20:00Z | 2026-01-21T20:30:00Z | 2026-01-21T20:40:00Z | 2026-01-21T20:50:00Z |
| L007 | S007 | 2026-01-25T15:40:00Z | 2026-01-25T07:50:00Z | 2026-01-25T08:00:00Z | 2026-01-25T08:10:00Z |
| L008 | S008 | 2026-01-29T03:00:00Z | 2026-01-28T19:10:00Z | 2026-01-28T19:20:00Z | 2026-01-28T19:30:00Z |
| L009 | S009 | 2026-02-01T14:20:00Z | 2026-02-01T06:30:00Z | 2026-02-01T06:40:00Z | 2026-02-01T06:50:00Z |
| L010 | S010 | 2026-02-05T01:40:00Z | 2026-02-04T17:50:00Z | 2026-02-04T18:00:00Z | 2026-02-04T18:10:00Z |
| L011 | S011 | 2026-02-08T13:00:00Z | 2026-02-08T05:10:00Z | 2026-02-08T05:20:00Z | 2026-02-08T05:30:00Z |
| L012 | S012 | 2026-02-12T00:20:00Z | 2026-02-11T16:30:00Z | 2026-02-11T16:40:00Z | 2026-02-11T16:50:00Z |

## Column definitions

| Column | SQL type | PK | Not null |
|---|---|---|---|
| plan_id | TEXT | True | True |
| slab_id | TEXT | False | True |
| planned_reheat_at | TEXT | False | True |
| submitted_at | TEXT | False | True |
| approved_at | TEXT | False | False |
| released_at | TEXT | False | False |
