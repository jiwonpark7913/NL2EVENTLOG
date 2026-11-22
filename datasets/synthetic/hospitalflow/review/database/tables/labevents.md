# labevents

**Rows:** 62 · **Columns:** 7

## Original records (first 10)

| labevent_id | order_id | itemid | charttime | storetime | valuenum | valueuom |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 31070762 | 1003 | 2026-01-27T19:38:00Z | 2026-01-27T23:09:00Z | 14.6 | g/dL |
| 2 | 31079248 | 1003 | 2026-02-03T16:09:00Z | 2026-02-03T19:00:00Z | 14.1 | g/dL |
| 3 | 31079248 | 1002 | 2026-02-03T15:16:00Z | 2026-02-03T19:38:00Z | 141.8 | mmol/L |
| 4 | 31073704 | 1001 | 2026-02-03T15:46:00Z | 2026-02-03T17:28:00Z | 1.13 | mg/dL |
| 5 | 31096075 | 1002 | 2026-02-15T02:54:00Z | 2026-02-15T05:54:00Z | 133.2 | mmol/L |
| 6 | 30000691 | 1002 | 2026-03-06T10:09:00Z | 2026-03-06T14:12:00Z | 132.2 | mmol/L |
| 7 | 30000691 | 1001 | 2026-03-06T09:55:00Z | 2026-03-06T11:43:00Z | 1.25 | mg/dL |
| 8 | 30000691 | 1001 | 2026-03-06T09:13:00Z | 2026-03-06T13:48:00Z | 1.66 | mg/dL |
| 9 | 30000691 | 1001 | 2026-03-06T09:53:00Z | 2026-03-06T13:21:00Z | 1.15 | mg/dL |
| 10 | 30000691 | 1003 | 2026-03-06T08:37:00Z | 2026-03-06T11:15:00Z | 12.5 | g/dL |

## Column definitions

| Column | SQL type | PK | Not null |
|---|---|---|---|
| labevent_id | INTEGER | True | True |
| order_id | INTEGER | False | True |
| itemid | INTEGER | False | True |
| charttime | TEXT | False | True |
| storetime | TEXT | False | True |
| valuenum | REAL | False | False |
| valueuom | TEXT | False | False |
