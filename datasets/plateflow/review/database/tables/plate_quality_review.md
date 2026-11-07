# plate_quality_review

**Rows:** 46 · **Columns:** 5

## Original records (first 10)

| review_id | plate_id | started_at | finished_at | review_status |
| --- | --- | --- | --- | --- |
| P007-1-1 | P007-1 | 2026-01-25T20:40:00Z | 2026-01-25T20:50:00Z | REWORK |
| P007-1-2 | P007-1 | 2026-01-25T22:00:00Z | 2026-01-25T22:15:00Z | APPROVED |
| P007-2-1 | P007-2 | 2026-01-26T05:00:00Z | 2026-01-26T05:10:00Z | APPROVED |
| P008-1-1 | P008-1 | 2026-01-29T08:00:00Z | 2026-01-29T08:10:00Z | APPROVED |
| P008-2-1 | P008-2 | 2026-01-29T16:20:00Z | 2026-01-29T16:30:00Z | APPROVED |
| P008-3-1 | P008-3 | 2026-01-30T00:40:00Z | 2026-01-30T00:50:00Z | APPROVED |
| P009-1-1 | P009-1 | 2026-02-01T19:20:00Z | 2026-02-01T19:30:00Z | APPROVED |
| P010-1-1 | P010-1 | 2026-02-05T06:40:00Z | 2026-02-05T06:50:00Z | APPROVED |
| P010-2-1 | P010-2 | 2026-02-05T15:00:00Z | 2026-02-05T15:10:00Z | REWORK |
| P010-2-2 | P010-2 | 2026-02-05T16:20:00Z | 2026-02-05T16:35:00Z | APPROVED |

## Column definitions

| Column | SQL type | PK | Not null |
|---|---|---|---|
| review_id | TEXT | True | True |
| plate_id | TEXT | False | True |
| started_at | TEXT | False | True |
| finished_at | TEXT | False | False |
| review_status | TEXT | False | True |
