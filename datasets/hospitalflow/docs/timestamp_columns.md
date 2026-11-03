# Timestamp columns

| Table | Column | Event time? | Meaning |
| --- | --- | --- | --- |
| admissions | edregtime | True | Actual event time |
| admissions | admittime | True | Actual event time |
| admissions | discharge_authorized_at | True | Actual event time |
| admissions | dischtime | True | Actual event time |
| patient_profile | profile_verified_at | True | Actual event time |
| admission_detail | discharge_summary_signed_at | True | Actual event time |
| lab_order | specimen_received_at | True | Actual event time |
| lab_order | results_verified_at | True | Actual event time |
| medication_order | stopped_at | True | Actual event time |
| procedure_order | preparation_completed_at | True | Actual event time |
| order_history | occurred_at | True | Actual event time |
| labevents | charttime | True | Actual event time |
| labevents | storetime | True | Actual event time |
| emar | charttime | True | Actual event time |
| emar | storetime | False | Technical documentation time |
| procedure_episode | starttime | True | Actual event time |
| procedure_episode | endtime | True | Actual event time |
| procedure_episode | storetime | False | Technical documentation time |
| pharmacy | dispensed_at | True | Actual event time |
