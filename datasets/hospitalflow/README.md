# HospitalFlow

HospitalFlow models synthetic patient encounters, clinical orders, medication administration, laboratory testing, procedures, and care-unit transfers. Its patient and admission structures and time-column vocabulary are inspired by the public MIMIC-IV hospital schema; all records are synthetic, not MIMIC-IV patient records.

[Relational schema](#relational-schema) · [Table previews](#table-inspector) · [Questions](#questions) · [Gold source projection](#gold-event-extraction-graph-eeg-source-projection)

## Entity types and identifiers

[Concepts and formal definitions](../../docs/system/ENTITY_IDENTITY_AND_STORAGE.md) · [Storage cases across datasets](../ENTITY_STORAGE_CASES.md) · [Actual PK, UNIQUE and FK inventory](docs/entity_identifiers.md)

The source projection below assigns a principal type for display. It does not mean a table can identify or reference only one ET. Entity identity is resolved from table/column/condition rules, separately from table membership.

## Dataset overview

| Physical ERs | Entity Type candidates | Core business concepts | Gold SQL/CSV pairs verified |
|---:|---:|---:|---:|
| 12 | 11 | 5 | 42 |

[SQLite database](input/database.sqlite) · [Business Data Dictionary](input/data_dictionary.json) · [Readable dictionary](docs/data_dictionary.md) · [Detailed database review](review/database/README.md)

## Relational schema

![Relational database schema with highlighted timestamp columns](review/database/schema.svg)

**Yellow:** Gold event-time source, where established. **Blue:** other temporal columns. A temporal column is not automatically an event timestamp.

[Open full-size ERD](review/database/schema.svg) · [Editable Draw.io diagram](docs/schema.drawio) · [Timestamp inventory and roles](docs/timestamp_columns.md)

## Table inspector

| Physical table | Rows | Columns | ET candidate | First ten records |
|---|---:|---:|---|---|
| admission_detail | 5 | 2 | Hospital Admission | [Preview](review/database/tables/admission_detail.md) |
| admissions | 15 | 16 | Hospital Admission | [Preview](review/database/tables/admissions.md) |
| emar | 67 | 5 | Medication Administration | [Preview](review/database/tables/emar.md) |
| lab_order | 34 | 5 | Laboratory Order | [Preview](review/database/tables/lab_order.md) |
| labevents | 62 | 7 | Lab Measurement | [Preview](review/database/tables/labevents.md) |
| medication_order | 29 | 4 | Medication Order | [Preview](review/database/tables/medication_order.md) |
| order_history | 203 | 6 | Order History Record | [Preview](review/database/tables/order_history.md) |
| patients | 12 | 6 | Patient | [Preview](review/database/tables/patients.md) |
| pharmacy | 34 | 3 | Pharmacy Dispensing | [Preview](review/database/tables/pharmacy.md) |
| procedure_episode | 23 | 5 | Procedure Episode | [Preview](review/database/tables/procedure_episode.md) |
| procedure_order | 17 | 4 | Procedure Order | [Preview](review/database/tables/procedure_order.md) |
| transfers | 38 | 7 | Care Unit Transfer | [Preview](review/database/tables/transfers.md) |

## Questions

[**Full question list, types and answerability**](docs/questions.md) · [Question texts (JSONL)](evaluation/model_questions.jsonl) · [Question-level Gold DFGs and source records](review/gold_dfg/README.md)

The checked-in question-text file contains **44 requests**. Explicit requests enumerate activities; implicit requests ask for a recorded lifecycle. Paired paraphrases, where present, are listed in the full question documentation.

<details>
<summary>Browse all 44 question texts</summary>

| ID | Request |
|---|---|
| H01 | For each hospital admission, extract Order Entered, Order Reviewed and Order Cancelled events. |
| H01P | For every hospital stay, build a timeline of when its orders were placed, checked and, if applicable, cancelled. |
| H02 | For each hospital admission, extract Lab Result Available, Medication Administered and Procedure Completed events. |
| H02P | For every hospital stay, show when laboratory findings became available, medicines were given and procedures finished. |
| H03 | For each laboratory order, extract Specimen Collected, Lab Result Available and Lab Results Verified events. |
| H03P | For every laboratory request, show when specimens were collected, when results became available and when those results were verified. |
| H04 | For each medication order, extract Medication Dispensed, Medication Administered, Medication Not Given and Medication Stopped events. |
| H04P | Create a timeline for each medication order covering dispensing, each dose given or not given, and the stopping of the medication. |
| H05 | For each procedure order, extract Procedure Preparation Completed, Procedure Started and Procedure Completed events. |
| H05P | For every procedure order, show when preparation finished and when each procedure occurrence began and ended. |
| H06 | For each hospital admission, extract Emergency Department Registered, Hospital Admitted, Emergency Department Departed and Hospital Discharged events. |
| H06P | For every hospital stay, show arrival registration in the emergency department, admission, departure from the emergency department and actual discharge. |
| H07 | For each patient, extract Hospital Admitted, Lab Result Available, Medication Administered, Procedure Completed and Hospital Discharged events. |
| H07P | For each patient, collect the recorded hospital entries and departures, availability of laboratory findings, medicine administrations and finishes of procedures. |
| H08 | For each hospital admission, extract Insurance Claim Paid events. |
| H08P | For each hospital stay, show when its insurance claim was settled by payment. |
| HF01 | Extract the full recorded lifecycle for each patient. |
| HF01P | Build a complete timeline of all recorded care events for every patient. |
| HF02 | Extract the full recorded lifecycle for each hospital admission. |
| HF02P | Show the entire recorded history of each individual hospital stay. |
| HF03 | Extract the full recorded lifecycle for each order history record. |
| HF03P | Show the complete recorded history of every individual order history record. |
| HF04 | Extract the full recorded lifecycle for each laboratory order. |
| HF04P | Show everything recorded over the life of each laboratory order. |
| HF05 | Extract the full recorded lifecycle for each medication order. |
| HF05P | Build the complete recorded history of each medication order. |
| HF06 | Extract the full recorded lifecycle for each procedure order. |
| HF06P | Trace the whole recorded lifecycle of every procedure order. |
| H09 | For each patient, extract Care Unit Transferred events. |
| H09P | Show when each patient moved to a different hospital care unit. |
| H10 | For each hospital admission, extract Discharge Summary Signed events. |
| H10P | For each hospital stay, show when its discharge summary was signed. |
| H11 | For each patient, extract Patient Profile Verified and Hospital Admitted events. |
| H11P | Build a timeline for every patient showing verification of their supplementary personal information and their entries into hospital. |
| HF07 | Extract the full recorded lifecycle for each lab measurement. |
| HF07P | Show the entire recorded history of each individual laboratory measurement. |
| HF08 | Extract the full recorded lifecycle for each medication administration. |
| HF08P | Build the complete recorded history of every individual medication administration record. |
| HF09 | Extract the full recorded lifecycle for each procedure episode. |
| HF09P | Trace each individual procedure episode through its whole recorded lifecycle. |
| HF10 | Extract the full recorded lifecycle for each pharmacy dispensing record. |
| HF10P | Show the complete recorded course associated with each individual pharmacy dispensing record. |
| H12 | For each pharmacy dispensing record, extract Medication Dispensed, Medication Administered and Medication Not Given events. |
| H12P | Group the medication dispensing, subsequent doses given and doses not given by the pharmacy dispensing record they refer to. |

</details>

## Gold Event Extraction Graph (EEG) Source Projection

![Entity Type candidates → Entity Representations → Activities](review/database/gold_evidence_graph.svg)

The diagram distinguishes core business entity concepts from supporting entity and event-record types. 
Each physical ER has exactly one currently annotated Entity Type candidate. Event-to-entity case attribution is separate from the source ER's provisional ET annotation; FK paths alone do not establish lifecycle membership.

**This is a source-level author-annotated projection, not an inferred EEG or a validated namespace-aware ET Gold.**
Gold SQL and record-level evidence are available in the linked inspection materials; their internal consistency does not validate the target namespace model. The current membership labels originate from the pre-namespace Gold; an independently validated ET/Identity Namespace Gold is a separate evaluation task.



**Entity-model status:** A physical table is one **Entity Representation (ER)**. Its displayed **Entity Type (ET) candidate** comes from legacy Gold annotations. ET semantic grouping and cross-ER instance identity resolution must be validated independently. FK reachability alone does not establish Case Attribution or Lifecycle Membership. [Terminology and namespace contract](../../docs/system/EEG_ENTITY_MODEL.md).

## Entity Type candidates vs. core business objects

Legacy identity groups (ET candidates): **11**; principal business object concepts in this domain: **5**. 
The core set is a candidate semantic grouping, not a rule for merging unrelated instances or Identity Namespaces.

**Core business concepts:** Hospital Admission, Laboratory Order, Medication Order, Patient, Procedure Order.

Supporting Gold types: Care Unit Transfer, Lab Measurement, Medication Administration, Order History Record, Pharmacy Dispensing, Procedure Episode.

## Evaluation evidence

- Gold SQL/CSV pairs executable and consistent: 42; compared event rows across questions: 6656.
- [Gold source inventory](review/gold_dfg/event_graph.md)
- [Question-level Gold DFGs](review/gold_dfg/README.md)
- [Editable Draw.io schema](docs/schema.drawio)


## MIMIC-IV provenance

HospitalFlow is a synthetic database informed by the [MIMIC-IV hospital schema](https://mimic.mit.edu/docs/iv/modules/hosp/).
The patient master contains gender, anchor_age, anchor_year, anchor_year_group and dod. The admissions record uses admittime, dischtime, deathtime, edregtime and edouttime. Transfer intervals use eventtype, careunit, intime and outtime.
All individual records are synthetic.

## Model input boundary

This README, diagrams, table previews and Gold evidence are reader/reviewer material. Use the [model-input manifest](evaluation/model_input_manifest.json) to identify evaluation inputs; do not supply Gold annotations or review materials to the model.
