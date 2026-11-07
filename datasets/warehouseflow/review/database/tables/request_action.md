# request_action

**Rows:** 56 · **Columns:** 6

## Original records (first 10)

| action_id | request_id | worker_id | code_family | action_code | occurred_at |
| --- | --- | --- | --- | --- | --- |
| 0001 | 001 | 1 | REQUEST | CHECK | 2026-02-01T05:05:00Z |
| 0002 | 001 | 1 | REQUEST | RELEASE | 2026-02-01T05:12:00Z |
| 0003 | 002 | 2 | REQUEST | CHECK | 2026-02-01T10:05:00Z |
| 0004 | 002 | 2 | REQUEST | RELEASE | 2026-02-01T10:12:00Z |
| 0005 | 003 | 3 | REQUEST | CHECK | 2026-02-01T15:05:00Z |
| 0006 | 003 | 3 | REQUEST | RELEASE | 2026-02-01T15:12:00Z |
| 0007 | 004 | 4 | REQUEST | CHECK | 2026-02-01T20:05:00Z |
| 0008 | 004 | 4 | REQUEST | RELEASE | 2026-02-01T20:12:00Z |
| 0009 | 005 | 5 | REQUEST | CHECK | 2026-02-02T01:05:00Z |
| 0010 | 005 | 5 | REQUEST | HOLD | 2026-02-02T01:08:00Z |

## Column definitions

| Column | SQL type | PK | Not null |
|---|---|---|---|
| action_id | TEXT | True | True |
| request_id | TEXT | False | True |
| worker_id | TEXT | False | True |
| code_family | TEXT | False | True |
| action_code | TEXT | False | True |
| occurred_at | TEXT | False | True |
