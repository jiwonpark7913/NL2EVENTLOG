# Timestamp column inventory

- Timestamp columns count physical table.column pairs storing date-and-time instants. Date-only birth/planning fields and recurring class schedules are excluded. Event timestamp columns are the subset actually selected as event times by the current ES; roles distinguish plans, technical times, snapshots, interval starts and copied key timestamps. Phase-aware variants may select actual interval starts as event times.

| Table | Column | Role | Used as event time | Non-null rows |
|---|---|---|---|---:|
| transaction_record | occurred_at | actual event time | Yes | 80 |
| transaction_record_activity | occurred_at | actual event time | Yes | 314 |

- Date-only fields excluded: None.
- Timestamp questions TS01/TS02/... and their P counterparts test the named milestones. WarehouseFlow stores these in carrier-driven history rows; other datasets may use milestone columns.
