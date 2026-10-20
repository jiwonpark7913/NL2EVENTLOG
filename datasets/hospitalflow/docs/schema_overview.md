# HospitalFlow · MIMIC-inspired synthetic — Schema overview

![Entity relationship diagram](schema.png)

- [Editable draw.io diagram](schema.drawio) · [Column dictionary](data_dictionary.md) · [CSV dictionary](data_dictionary.csv)

| Table | Rows | Columns | Event encoding | Primary key | Role |
|---|---:|---:|---|---|---|
| object_type | 3 | 3 | No event encoding | type_code | Semantic object types shared across business tables; not activities or case instances. |
| object | 72 | 2 | No event encoding | object_id | Globally unique object identities and their semantic types; no events are stored here. |
| patients | 12 | 3 | No event encoding | subject_id | Synthetic patient identity, inspired by MIMIC subject_id. |
| admissions | 15 | 7 | Column encoding | hadm_id | Distinct hospital stays per patient with actual admission/discharge milestones. |
| clinical_order | 45 | 4 | No event encoding | object_id | Authored common parent for laboratory, medication and procedure orders; not a MIMIC table. |
| lab_order | 15 | 5 | Column encoding | order_id | Authored laboratory-order subtype; several measurements may belong to one order. |
| medication_order | 15 | 6 | Column encoding | order_id | Authored medication-order subtype; repeated doses belong to one order. |
| procedure_order | 15 | 5 | Column encoding | order_id | Authored procedure-order subtype; repeated execution episodes belong to one order. |
| order_history | 102 | 4 | Row encoding | history_id | Repeated order actions, inspired by provider order transaction semantics; not a copy of poe. |
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
| object_type | object | type_code | type_code | 1 : 0..N | declared |
| object | patients | object_id | object_id | 1 : 0..1 | declared |
| object | admissions | object_id | object_id | 1 : 0..1 | declared |
| patients | admissions | subject_id | subject_id | 1 : 0..N | declared |
| admissions | clinical_order | hadm_id, subject_id | hadm_id, subject_id | 1 : 0..N | declared |
| object | clinical_order | object_id | object_id | 1 : 0..1 | declared |
| clinical_order | lab_order | object_id, order_kind | object_id, order_kind | 1 : 0..1 | declared |
| clinical_order | medication_order | object_id, order_kind | object_id, order_kind | 1 : 0..1 | declared |
| clinical_order | procedure_order | object_id, order_kind | object_id, order_kind | 1 : 0..1 | declared |
| clinical_order | order_history | object_id | object_id | 1 : 0..N | declared |
| lab_order | labevents | order_id | order_id | 1 : 0..N | declared |
| medication_order | emar | order_id | order_id | 1 : 0..N | declared |
| procedure_order | procedureevents | order_id | order_id | 1 : 0..N | declared |
