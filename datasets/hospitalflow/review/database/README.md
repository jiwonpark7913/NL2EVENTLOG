# Hospitalflow — Database and Gold Evidence Review

HospitalFlow models synthetic patient encounters, clinical orders, medication administration, laboratory testing, procedures, and care-unit transfers. Its patient and admission structures and time-column vocabulary are inspired by the public MIMIC-IV hospital schema; all records are synthetic, not MIMIC-IV patient records.

## Gold Evidence Graph

![Gold Object Types → Physical Tables → Activities](gold_evidence_graph.svg)

The diagram separates **core business object concepts** from supporting entities and activity-record types, without changing the Gold identity assignments. 
Each physical table belongs to exactly one Gold Object Type. An event can be associated with several business objects through foreign keys without its source table belonging to multiple OTs.

**This is an author-annotated Gold source projection, not an inferred Evidence Graph or a full provenance graph.**
Gold SQL and record-level references remain in the evaluation-only files.

## Relational Schema (SQL foreign keys)

![Relational database schema](schema.svg)

## Table inspector

| Physical table | Rows | Columns | Gold OT | First ten records |
|---|---:|---:|---|---|
| admission_detail | 5 | 2 | Hospital Admission | [Preview](tables/admission_detail.md) |
| admissions | 15 | 16 | Hospital Admission | [Preview](tables/admissions.md) |
| emar | 67 | 5 | Medication Administration | [Preview](tables/emar.md) |
| lab_order | 34 | 5 | Laboratory Order | [Preview](tables/lab_order.md) |
| labevents | 62 | 7 | Lab Measurement | [Preview](tables/labevents.md) |
| medication_order | 29 | 4 | Medication Order | [Preview](tables/medication_order.md) |
| order_history | 203 | 6 | Order History Record | [Preview](tables/order_history.md) |
| patients | 12 | 6 | Patient | [Preview](tables/patients.md) |
| pharmacy | 34 | 3 | Pharmacy Dispensing | [Preview](tables/pharmacy.md) |
| procedure_episode | 23 | 5 | Procedure Episode | [Preview](tables/procedure_episode.md) |
| procedure_order | 17 | 4 | Procedure Order | [Preview](tables/procedure_order.md) |
| transfers | 38 | 7 | Care Unit Transfer | [Preview](tables/transfers.md) |

## Gold object types vs. core business objects

Gold identity types: **11**; principal business object concepts in this domain: **5**. 
The core set is a conceptual layer for interpreting process scope, not a rule that forces unrelated PK domains to merge.

**Core business concepts:** Hospital Admission, Laboratory Order, Medication Order, Patient, Procedure Order.

Supporting Gold types: Care Unit Transfer, Lab Measurement, Medication Administration, Order History Record, Pharmacy Dispensing, Procedure Episode.

## Evaluation evidence

- Gold SQL/CSV pairs executable and consistent: 42; compared event rows across questions: 6656.
- [Gold source inventory](../gold_dfg/event_graph.md)
- [Question-level Gold DFGs](../gold_dfg/README.md)
- [Editable Draw.io schema](../../docs/schema.drawio)

*SQLite, dictionary and Gold outputs are unchanged by this review-page regeneration.*

## MIMIC-IV provenance

HospitalFlow is a synthetic database informed by the [MIMIC-IV hospital schema](https://mimic.mit.edu/docs/iv/modules/hosp/).
The patient master contains gender, anchor_age, anchor_year, anchor_year_group and dod. The admissions record uses admittime, dischtime, deathtime, edregtime and edouttime. Transfer intervals use eventtype, careunit, intime and outtime.
All individual records are synthetic.
