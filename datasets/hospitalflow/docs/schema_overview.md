# HospitalFlow — current database overview

Generated from current SQLite + authored Gold identity annotations.

[Editable Draw.io](schema.drawio) · [DB review](../review/database/README.md) · [Gold evidence](../review/database/gold_evidence_graph.svg)

| Table | Rows | Columns | PK | Gold OT |
|---|---:|---:|---|---|
| [admission_detail](../review/database/tables/admission_detail.md) | 5 | 2 | hadm_id | Hospital Admission |
| [admissions](../review/database/tables/admissions.md) | 15 | 16 | hadm_id | Hospital Admission |
| [emar](../review/database/tables/emar.md) | 67 | 5 | emar_id | Medication Administration |
| [lab_order](../review/database/tables/lab_order.md) | 34 | 5 | order_id | Laboratory Order |
| [labevents](../review/database/tables/labevents.md) | 62 | 7 | labevent_id | Lab Measurement |
| [medication_order](../review/database/tables/medication_order.md) | 29 | 4 | order_id | Medication Order |
| [order_history](../review/database/tables/order_history.md) | 203 | 6 | history_id | Order History Record |
| [patients](../review/database/tables/patients.md) | 12 | 6 | subject_id | Patient |
| [pharmacy](../review/database/tables/pharmacy.md) | 34 | 3 | pharmacy_id | Pharmacy Dispensing |
| [procedure_episode](../review/database/tables/procedure_episode.md) | 23 | 5 | procedureevent_id | Procedure Episode |
| [procedure_order](../review/database/tables/procedure_order.md) | 17 | 4 | order_id | Procedure Order |
| [transfers](../review/database/tables/transfers.md) | 38 | 7 | transfer_id | Care Unit Transfer |

## Physical foreign keys

| Child | Key | Parent | Key |
|---|---|---|---|
| admission_detail | hadm_id | admissions | hadm_id |
| admissions | subject_id | patients | subject_id |
| emar | pharmacy_id | pharmacy | pharmacy_id |
| lab_order | hadm_id | admissions | hadm_id |
| lab_order | subject_id | patients | subject_id |
| labevents | order_id | lab_order | order_id |
| medication_order | hadm_id | admissions | hadm_id |
| order_history | procedure_order_id | procedure_order | order_id |
| order_history | medication_order_id | medication_order | order_id |
| order_history | lab_order_id | lab_order | order_id |
| pharmacy | order_id | medication_order | order_id |
| procedure_episode | order_id | procedure_order | order_id |
| procedure_order | hadm_id | admissions | hadm_id |
| transfers | hadm_id | admissions | hadm_id |
| transfers | subject_id | patients | subject_id |

Foreign-key links are not Object Type identity equivalence.

