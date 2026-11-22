# HospitalFlow — current timestamp inventory

Gold event time is not interchangeable with other timestamps; storetime and outtime may record observations or interval ends.

| Table | Column | Gold event timestamp |
|---|---|---|
| admission_detail | discharge_summary_signed_at | Yes |
| admissions | edregtime | Yes |
| admissions | admittime | Yes |
| admissions | dischtime | Yes |
| admissions | deathtime | No |
| admissions | edouttime | Yes |
| emar | charttime | Yes |
| emar | storetime | No |
| lab_order | specimen_received_at | Yes |
| lab_order | results_verified_at | Yes |
| labevents | charttime | Yes |
| labevents | storetime | Yes |
| medication_order | stopped_at | Yes |
| order_history | occurred_at | Yes |
| pharmacy | dispensed_at | Yes |
| procedure_episode | starttime | Yes |
| procedure_episode | endtime | Yes |
| procedure_episode | storetime | No |
| procedure_order | preparation_completed_at | Yes |
| transfers | intime | Yes |
| transfers | outtime | No |
