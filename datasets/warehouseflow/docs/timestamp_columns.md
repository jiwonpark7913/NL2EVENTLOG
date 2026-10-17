# Timestamp column inventory

- Timestamp columns count physical table.column pairs storing date-and-time instants. Date-only birth/planning fields and recurring class schedules are excluded. Event timestamp columns are the subset actually selected as event times by the current ES; plans, technical times, snapshots, interval starts and copied key timestamps are listed separately.

| Table | Column | Role | Used as event time | Non-null rows |
|---|---|---|---|---:|
| transaction_record | occurred_at | actual event time | Yes | 80 |
| transaction_record | receiving_requested_at | actual event time | Yes | 45 |
| transaction_record | receiving_scheduled_at | actual event time | Yes | 45 |
| transaction_record | dispatch_requested_at | actual event time | Yes | 35 |
| transaction_record | dispatch_approved_at | actual event time | Yes | 35 |
| transaction_record_activity | occurred_at | actual event time | Yes | 154 |

- Date-only fields excluded: None.
- New timestamp questions TS01/TS02/... and their P counterparts explicitly test milestone-column extraction.
