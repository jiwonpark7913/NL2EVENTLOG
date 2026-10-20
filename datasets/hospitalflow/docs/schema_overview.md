# HospitalFlow · split business-object storage — Schema overview

![Entity relationship diagram](schema.png)

- [Editable draw.io diagram](schema.drawio) · [Column dictionary](data_dictionary.md) · [CSV dictionary](data_dictionary.csv)

| Table | Rows | Columns | Event encoding | Primary key | Role |
|---|---:|---:|---|---|---|
| patients | 12 | 2 | No event encoding | subject_id | Synthetic patient identity, inspired by MIMIC subject_id. |
| admissions | 15 | 6 | Column encoding | hadm_id | Distinct hospital stays per patient with actual admission/discharge milestones. |
| patient_profile | 6 | 3 | Column encoding | subject_id | Optional additional information for the SAME patient identified by patients.subject_id, in the SAME identifier namespace. A matching subject_id denotes the same actual patient. No FK is declared; this identity relationship is explicitly documented. Authored split-storage extension. |
| admission_detail | 5 | 3 | Column encoding | hadm_id | Optional additional information for the SAME hospital stay identified by admissions.hadm_id. A matching hadm_id denotes the same actual admission. Only a subset of admissions has a signed summary. Authored split-storage extension. |
| lab_order | 15 | 4 | Column encoding | order_id | Distinct laboratory order; several measurements may belong to one order. |
| medication_order | 15 | 5 | Column encoding | order_id | Distinct medication order; repeated doses belong to one order. |
| procedure_order | 15 | 4 | Column encoding | order_id | Distinct procedure order; repeated execution episodes belong to one order. |
| order_history | 102 | 6 | Row encoding | history_id | Repeated order actions, inspired by provider order transaction semantics; not a copy of poe. |
| labevents | 33 | 7 | Mixed (row + column) | labevent_id | Measurement occurrences with separately charted and available-result times, inspired by MIMIC labevents. |
| emar | 45 | 5 | Row encoding | emar_id | Medication administration or omission occurrences, inspired by MIMIC emar. |
| procedureevents | 15 | 5 | Mixed (row + column) | procedureevent_id | Procedure execution episodes with start/end times, inspired by MIMIC procedureevents. |

- Row encoding: each occurrence is a separate row; its activity comes from a code, label or the table meaning.
- Column encoding: an object row stores actual milestone times in dedicated columns. It can contain one or several milestones.
- No event encoding: the table supplies context, plans, identities or links rather than direct events.
- Planned dates, snapshots and technical timestamps do not automatically become events.


## Relationships

| Parent | Child | Child FK | Parent key | Parent-to-child count | Kind |
|---|---|---|---|---|---|
| patients | admissions | subject_id | subject_id | 1 : 0..N | declared |
| admissions | admission_detail | hadm_id | hadm_id | 1 : 0..N | declared |
| admissions | lab_order | hadm_id | hadm_id | 1 : 0..N | declared |
| admissions | medication_order | hadm_id | hadm_id | 1 : 0..N | declared |
| admissions | procedure_order | hadm_id | hadm_id | 1 : 0..N | declared |
| procedure_order | order_history | procedure_order_id | order_id | 1 : 0..N | declared |
| medication_order | order_history | medication_order_id | order_id | 1 : 0..N | declared |
| lab_order | order_history | lab_order_id | order_id | 1 : 0..N | declared |
| lab_order | labevents | order_id | order_id | 1 : 0..N | declared |
| medication_order | emar | order_id | order_id | 1 : 0..N | declared |
| procedure_order | procedureevents | order_id | order_id | 1 : 0..N | declared |
| patients | patient_profile | subject_id | subject_id | documented same identity; no FK | logical |
