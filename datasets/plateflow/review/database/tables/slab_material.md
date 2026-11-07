# slab_material

**Rows:** 30 · **Columns:** 6

## Original records (first 10)

| slab_id | charge_id | steel_grade | received_at | verified_at | released_at |
| --- | --- | --- | --- | --- | --- |
| S001 | C001 | G1 | 2026-01-04T11:20:00Z | NULL | NULL |
| S002 | C001 | G2 | 2026-01-07T22:40:00Z | NULL | NULL |
| S003 | C001 | G1 | 2026-01-11T10:00:00Z | 2026-01-11T10:10:00Z | 2026-01-11T10:20:00Z |
| S004 | C002 | G2 | 2026-01-14T21:20:00Z | 2026-01-14T21:30:00Z | 2026-01-14T21:40:00Z |
| S005 | C002 | G1 | 2026-01-18T08:40:00Z | 2026-01-18T08:50:00Z | 2026-01-18T09:00:00Z |
| S006 | C002 | G2 | 2026-01-21T20:00:00Z | 2026-01-21T20:10:00Z | 2026-01-21T20:20:00Z |
| S007 | C003 | G1 | 2026-01-25T07:20:00Z | 2026-01-25T07:30:00Z | 2026-01-25T07:40:00Z |
| S008 | C003 | G2 | 2026-01-28T18:40:00Z | 2026-01-28T18:50:00Z | 2026-01-28T19:00:00Z |
| S009 | C003 | G1 | 2026-02-01T06:00:00Z | 2026-02-01T06:10:00Z | 2026-02-01T06:20:00Z |
| S010 | C004 | G2 | 2026-02-04T17:20:00Z | 2026-02-04T17:30:00Z | 2026-02-04T17:40:00Z |

## Column definitions

| Column | SQL type | PK | Not null |
|---|---|---|---|
| slab_id | TEXT | True | True |
| charge_id | TEXT | False | True |
| steel_grade | TEXT | False | True |
| received_at | TEXT | False | True |
| verified_at | TEXT | False | False |
| released_at | TEXT | False | False |
