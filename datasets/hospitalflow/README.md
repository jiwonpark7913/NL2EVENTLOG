# HospitalFlow dataset

- **Purpose:** evaluate whether different Physical Objects represent the SAME business object type with compatible instance identity.
- **Source:** public MIMIC-IV documentation with wholly synthetic records. Split-storage extensions are authored, not original MIMIC tables.
- The database contains ordinary hospital business tables. It has no object, object_type or clinical_order registry/supertype table and no persisted generic object/type identifier.

| Dataset | Tables | Object / case types | Activity types | Timestamp columns | Event timestamp columns | Distinct events | Questions | Gold CSVs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| HospitalFlow | 11 | 9 | 20 | 19 | 17 | 372 | 40 | 38 |

- **Physical Objects:** 11 table/PK representations. **Expected identity-compatible groups:** 9. **Distinct business/occurrence instances:** 267.

## Identity grouping scenarios

- patients and patient_profile store different information about the SAME patient. The subject_id namespace is shared; 6 of 12 patients have profile rows. There is intentionally no FK between these tables; the dictionary explicitly documents the identifier relationship.
- admissions and admission_detail store different information about the SAME hospital stay. Their hadm_id namespace is shared, corroborated by a shared-PK FK; 5 of 15 admissions have supplementary summary records.
- Patient Profile Verified originates in patient_profile; admission events originate in admissions and Discharge Summary Signed originates in admission_detail. Grouping does not erase the physical source or collapse different events.
- lab_order, medication_order and procedure_order identify different requests. Their local order_id values overlap deliberately; this does not justify grouping them as one identity-compatible type.
- order_history.history_id identifies a history occurrence. Its order FK does not make it the same object as an order. Measurement, dose and procedure episode records also keep their own identities.
- **Gold grouping:** 11 Physical Objects → 9 groups, with exactly two expected MERGE pairs. The pair labels are reference answers, not results of running the user's Step 2 implementation.
- [Grouping examples and evaluation boundary](docs/object_type_verification.md)

## Scenarios and activities

| Object Type | Instances | Activity types | Activity scope |
| --- | --- | --- | --- |
| Patient | 12 | 20 | Discharge Authorized, Discharge Summary Signed, Emergency Department Registered, Hospital Admitted, Hospital Discharged, Lab Measurement Charted, Lab Result Available, Lab Results Verified, Medication Administered, Medication Dispensed, Medication Not Given, Medication Stopped, Order Cancelled, Order Entered, Order Reviewed, Patient Profile Verified, Procedure Completed, Procedure Preparation Completed, Procedure Started, Specimen Received |
| Hospital Admission | 15 | 19 | Discharge Authorized, Discharge Summary Signed, Emergency Department Registered, Hospital Admitted, Hospital Discharged, Lab Measurement Charted, Lab Result Available, Lab Results Verified, Medication Administered, Medication Dispensed, Medication Not Given, Medication Stopped, Order Cancelled, Order Entered, Order Reviewed, Procedure Completed, Procedure Preparation Completed, Procedure Started, Specimen Received |
| Laboratory Order | 15 | 6 | Lab Measurement Charted, Lab Result Available, Lab Results Verified, Order Entered, Order Reviewed, Specimen Received |
| Medication Order | 15 | 6 | Medication Administered, Medication Dispensed, Medication Not Given, Medication Stopped, Order Entered, Order Reviewed |
| Procedure Order | 15 | 6 | Order Cancelled, Order Entered, Order Reviewed, Procedure Completed, Procedure Preparation Completed, Procedure Started |
| Order History Record | 102 | 3 | Order Cancelled, Order Entered, Order Reviewed |
| Lab Measurement | 33 | 2 | Lab Measurement Charted, Lab Result Available |
| Medication Administration | 45 | 2 | Medication Administered, Medication Not Given |
| Procedure Episode | 15 | 2 | Procedure Completed, Procedure Started |

- Eleven Physical Objects map to nine expected identity-compatible Object Type groups. History/measurement/dose/episode records retain independent occurrence identities.
- Individual instances may contain fewer activities due to cancellation, ongoing care or missing records.

## Event storage

| Table | Encoding |
| --- | --- |
| patients | No event encoding |
| patient_profile | Column encoding |
| admissions | Column encoding |
| admission_detail | Column encoding |
| lab_order | Column encoding |
| medication_order | Column encoding |
| procedure_order | Column encoding |
| order_history | Row encoding |
| emar | Row encoding |
| labevents | Mixed (row + column) |
| procedureevents | Mixed (row + column) |

- Row tables preserve repeat actions. Column tables store actual one-time milestones. Mixed tables preserve repeat occurrences and distinct milestone times within each occurrence.
- Only identical case/event occurrences are deduplicated; grouping never merges different event IDs.

## Question types and pairs

| Type | Questions | Answerable | Non-answerable | Avg. requested activity types |
|---|---:|---:|---:|---:|
| Q1 | 11 | 10 | 1 | 2.73 |
| Q2 | 11 | 10 | 1 | 2.73 |
| Q3 | 9 | 9 | 0 | 7.33 |
| Q4 | 9 | 9 | 0 | 7.33 |

- Avg. requested activity types = sum of requested activity-type counts / all questions in that row, including non-answerable questions. Q3/Q4 counts use the Gold catalog scope. This counts distinct activity types, not event occurrences.

- Q1/Q3 seeds are frozen before the assistant LLM creates Q2/Q4. Prompts, outputs and review notes are stored in source/llm_paraphrases.json. No external API call is claimed.
- Each pair has identical scope, answerability, ES and Gold. Unsupported pairs have no CSV.
- [Questions, counts and requested activities](docs/questions.md)

## Model input and evaluation answers

- Model inputs: input/database.sqlite, input/schema.sql, input/data_dictionary.json and input/model_questions.jsonl.
- Optional input/task_scope_catalog.json declares default activity scopes only. It omits table memberships, namespace answers and instance populations. Evaluating identity without a scope catalog is also possible.
- private/identity_gold.json contains author-assigned table/PK grouping answers and full-key statistics. It must not be provided to the identity judge.
- private/event_binding_provenance.json records each source table, complete PK and own versus FK attribution. private/case_population.json and private/object_event_links.json are Gold annotations.
- design/, docs/ and this README include construction explanations and answers; exclude them from model inputs. The data dictionary is legitimate input evidence and explicitly describes identifier semantics without supplying final MERGE/SEPARATE labels.
- Main-schema gold pairs cover two positive split-storage cases and distinct-identity negatives. UNRESOLVED and group-conflict scenarios are separately specified in private/identity_edge_cases.json; these are not claimed live-table cases or executed semantic-judge tests.

## Build and validation

- Run `python datasets/hospitalflow/build.py`, `python make_docs.py`, `python question_summary.py`, `python validate_lifecycles.py` and `python validate_timestamp_columns.py` from the repository root.
- SQL/CSV outputs are compared with independent generation-time histories. Tests check identity groups, optional extensions, no-FK identity evidence, order/history separation, own/FK provenance, time order, repeated occurrences, empty cases and frozen question pairs.
- The NL2EventLog Step 2 identity classifier is not present in this dataset repository. This provides test inputs and Gold answers; it does not claim measured classifier accuracy, LLM identity decisions or candidate/decision audit statistics.
- [Construction plan](design/plan.md)
- [Source mapping](design/source_mapping.json)
- [Source references](source/references.md)
- [Object-specific Gold logs](docs/object_event_logs.md)

## Schema and documentation

![Schema](docs/schema.png)

- [Table inventory and relationships](docs/schema_overview.md)
- [English column dictionary](docs/data_dictionary.md)
- [CSV dictionary](docs/data_dictionary.csv)
- [Editable draw.io diagram](docs/schema.drawio)
- [Object-based Gold logs and coverage](docs/object_event_logs.md)

## Timestamp columns

- Timestamp columns count physical table.column pairs storing date-and-time instants. Date-only birth/planning fields and recurring class schedules are excluded. Event timestamp columns are the subset actually selected as event times by the current ES; plans, technical times, snapshots, interval starts and copied key timestamps are listed separately.
- [Timestamp inventory and roles](docs/timestamp_columns.md)
- [Milestone-column extraction questions and Gold activity counts](docs/questions.md)
- Single-occurrence milestone times are stored on the existing business record. Repeated actions remain row encoded; the same event is not stored twice.
