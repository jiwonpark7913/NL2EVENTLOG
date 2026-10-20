# Timestamp column inventory

- Timestamp columns count physical table.column pairs storing date-and-time instants. Date-only birth/planning fields and recurring class schedules are excluded. Event timestamp columns are the subset actually selected as event times by the current ES; plans, technical times, snapshots, interval starts and copied key timestamps are listed separately.

| Table | Column | Role | Used as event time | Non-null rows |
|---|---|---|---|---:|
| admissions | edregtime | actual event time | Yes | 8 |
| admissions | admittime | actual event time | Yes | 15 |
| admissions | discharge_authorized_at | actual event time | Yes | 14 |
| admissions | dischtime | actual event time | Yes | 14 |
| patient_profile | profile_verified_at | actual event time | Yes | 6 |
| admission_detail | discharge_summary_signed_at | actual event time | Yes | 5 |
| lab_order | specimen_received_at | actual event time | Yes | 13 |
| lab_order | results_verified_at | actual event time | Yes | 13 |
| medication_order | dispensed_at | actual event time | Yes | 15 |
| medication_order | stopped_at | actual event time | Yes | 14 |
| procedure_order | preparation_completed_at | actual event time | Yes | 12 |
| order_history | occurred_at | actual event time | Yes | 102 |
| labevents | charttime | actual event time | Yes | 33 |
| labevents | storetime | actual event time | Yes | 33 |
| emar | charttime | actual event time | Yes | 45 |
| emar | storetime | technical documentation time | No | 45 |
| procedureevents | starttime | actual event time | Yes | 15 |
| procedureevents | endtime | actual event time | Yes | 15 |
| procedureevents | storetime | technical documentation time | No | 15 |

- Date-only fields excluded: None.
- New timestamp questions TS01/TS02/... and their P counterparts explicitly test milestone-column extraction.
