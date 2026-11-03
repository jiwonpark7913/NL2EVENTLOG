# HospitalFlow · synthetic hospital records — Schema overview

![Entity relationship diagram](schema.png)

[Editable draw.io diagram](schema.drawio) · [Column dictionary](data_dictionary.md) · [CSV dictionary](data_dictionary.csv)

| Table | Rows | Columns | Event encoding | Primary key | Role |
|---|---:|---:|---|---|---|
| patients | 12 | 2 | See author README | subject_id | Synthetic patient identity, inspired by MIMIC subject_id. |
| admissions | 15 | 6 | See author README | hadm_id | Distinct hospital stays per patient with actual admission/discharge milestones. |
| patient_profile | 6 | 3 | See author README | subject_id | Optional additional information for the SAME patient identified by patients.subject_id, in the SAME identifier namespace. A matching subject_id denotes the same actual patient. No FK is declared; this identity relationship is explicitly documented. Authored split-storage extension. |
| admission_detail | 5 | 3 | See author README | hadm_id | Optional additional information for the SAME hospital stay identified by admissions.hadm_id. A matching hadm_id denotes the same actual admission. Only a subset of admissions has a signed summary. Authored split-storage extension. |
| lab_order | 34 | 5 | See author README | order_id | Authored laboratory request; multiple measurements can fulfill it. subject_id identifies the patient even when hadm_id is NULL for a request outside an admission. |
| medication_order | 29 | 4 | See author README | order_id | One medication prescription, including its stop time. Dispensing is recorded separately in pharmacy. |
| procedure_order | 17 | 4 | See author README | order_id | Distinct procedure order; repeated execution episodes belong to one order. |
| order_history | 203 | 6 | See author README | history_id | Repeated order actions, inspired by provider order transaction semantics; not a copy of poe. |
| labevents | 62 | 7 | See author README | labevent_id | Measurement occurrences with separately charted and available-result times, inspired by MIMIC labevents. |
| emar | 67 | 5 | See author README | emar_id | Medication administration or omission occurrences, inspired by MIMIC emar. |
| procedure_episode | 23 | 5 | See author README | procedureevent_id | Authored hospital-level procedure execution episode; not the MIMIC ICU procedureevents table. |
| pharmacy | 34 | 3 | See author README | pharmacy_id | One distinct dispensing record for a medication prescription; repeated dispensing records can fulfill the same prescription. |

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
| patients | lab_order | subject_id | subject_id | 1 : 0..N | declared |
| admissions | medication_order | hadm_id | hadm_id | 1 : 0..N | declared |
| admissions | procedure_order | hadm_id | hadm_id | 1 : 0..N | declared |
| procedure_order | order_history | procedure_order_id | order_id | 1 : 0..N | declared |
| medication_order | order_history | medication_order_id | order_id | 1 : 0..N | declared |
| lab_order | order_history | lab_order_id | order_id | 1 : 0..N | declared |
| lab_order | labevents | order_id | order_id | 1 : 0..N | declared |
| pharmacy | emar | pharmacy_id | pharmacy_id | 1 : 0..N | declared |
| procedure_order | procedure_episode | order_id | order_id | 1 : 0..N | declared |
| medication_order | pharmacy | order_id | order_id | 1 : 0..N | declared |
| patients | patient_profile | subject_id | subject_id | documented same identity; no FK | logical |
