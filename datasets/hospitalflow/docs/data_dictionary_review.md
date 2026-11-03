# HospitalFlow dictionary review — 2026-11-03

- **Baseline commit:** bb57d37e01cf60870f5f56e27e3a3d73bfc936fd.
- **Scope:** business metadata and its generation paths. The database, declared SQL schema, questions and private Gold artifacts are preserved.
- **Sources:** Harvard HMS/OSF variable-documentation guidance; existing HospitalFlow schema and author conventions; official MIMIC references for selected clinical-record time meanings.
- This is a preparatory author review, not independent clinical validation or an executed model evaluation.

## Before/after comparison

| Topic | Previous dictionary | Revised dictionary |
|---|---|---|
| Basic information | 15 fields, including benchmark timestamp counts and registry-style statements | 10 concise document/data-context fields |
| Physical variable names | Present | Preserved exactly for 50 columns |
| Readable names | Mostly title-cased physical names, including Edregtime and Admittime | Context-specific labels such as Emergency department registration time and Hospital admission time |
| Definitions | Some shared descriptions mixed meanings across different tables | Table-specific definitions for each variable |
| Units | Generic See column definition or broad UTC text repeated | Measurement unit separated from timestamp format/timezone; numeric result refers to valueuom |
| Allowed values | Mostly See executable table DDL | Four explicit coded domains and their meanings; declared versus documented restrictions distinguished |
| Numeric/text domains | Sample examples could be mistaken for allowed ranges | No sample-derived bounds, invented vocabularies or text lengths |
| NULL interpretation | Mainly required flags or broad absence descriptions | Column-specific NULL meanings for all 14 nullable columns |
| Datetime representation | Several time fields classified as ordinary text by name heuristics | All 19 datetime variables explicitly documented |
| Relational interpretation | PK/FK metadata present; table row grain implicit | Row grain, actual SQL keys and documented non-FK relationships separated |
| Optional synonyms/descriptions | Not consistently represented | Explicit optional fields; no invented synonyms; extended interpretation notes where justified |
| References | Primarily generic standard-scope references | Harvard/OSF documentation basis plus relevant definition references and authored-convention attribution |
| Event classification | Row/column/mixed labels and extraction details embedded | Removed from JSON/Markdown/CSV business dictionaries; author material remains separate |
| Benchmark instructions | Event-time counts and evaluation/extraction rules embedded | Excluded from business definitions; default inputs explicitly allowlisted |
| Regeneration | Legacy annotation/rendering could reinsert answers | Hospital-specific source profile and guarded metadata entry points |

## Examples

- admissions.admittime is TEXT in SQLite but a hospital-admission datetime semantically; those two facts are now documented separately.
- labevents.storetime means laboratory result availability. emar.storetime means medication-record documentation time. procedureevents.storetime means procedure-system documentation time.
- order_id has a table-specific readable meaning. The local ID in a laboratory-order table does not implicitly identify a medication/procedure request.
- patient_profile.subject_id is documented in the patients identifier namespace, but its SQL FK list remains empty.
- enum constraints are stated explicitly for gender, summary_status, action and event_txt. No broader MIMIC code vocabulary is silently substituted for the local synthetic schema.

## Verification performed in this edit

- Static reconciliation of 11 CREATE TABLE declarations and all 50 column names/types.
- Static reconciliation of primary keys, declared NOT NULL/UNIQUE/references, four coded variable domains and existing table CHECK text.
- Coverage of 19 datetime definitions and all 14 nullable columns.
- Synchronized generation of model-facing JSON, two Markdown copies, two CSV files and dictionary basic-information JSON.
- Structural Markdown/CSV and forbidden-answer-field checks.
- Git-tree verification that database.sqlite, schema.sql, questions and private Gold blobs remain at their baseline SHAs.

## Runtime verification not executed in this edit

- No usable execution environment was available. Python compilation, SQLite introspection against the binary DB, renderer round-trip and Gold SQL/CSV execution were not rerun here.
- A dedicated runtime check is supplied as datasets/hospitalflow/validate_dictionary.py and is invoked by the existing HospitalFlow validator.
- Run from the repository root:
  - python hospital_dictionary.py datasets/hospitalflow
  - python datasets/hospitalflow/validate_dictionary.py
  - python datasets/hospitalflow/validate.py
- Do not interpret earlier validation_report.json results as results of these newly added checks. This edit's static/runtime distinction is recorded separately.

## Remaining human-review decisions

- Decide whether numeric measurement categories require an authored lookup table; current itemid values have no supplied clinical category definitions. No names or physiological ranges were invented.
- Decide whether to add stricter datatype/datetime/range checks. Current SQL is not STRICT and does not validate RFC 3339 formatting.
- Existing admissions CHECK text does not fully establish every clinically plausible chronology; in particular, it does not explicitly require authorization whenever a discharge is present. No stronger enforcement was claimed or silently added.
- Confirm the business meaning of missing timestamps. The dictionary describes unrecorded times rather than universally asserting non-occurrence.
- Review clinical realism and event/phase selection in the next dataset-review stage. Existing author classification tables are not certified by the Harvard/OSF dictionary guides.
- Freeze the dictionary version and input manifest before comparing method results. A dictionary revision changes model evidence even when DB and Gold remain unchanged.

## References

- [Harvard HMS](https://datamanagement.hms.harvard.edu/collect-analyze/documentation-metadata/data-dictionary)
- [OSF](https://help.osf.io/article/217-how-to-make-a-data-dictionary)
- [MIMIC admissions](https://mimic.mit.edu/docs/iv/modules/hosp/admissions.html)
- [MIMIC labevents](https://mimic.mit.edu/docs/iv/modules/hosp/labevents.html)
- [MIMIC emar](https://mimic.mit.edu/docs/iv/modules/hosp/emar.html)
- [MIMIC procedureevents](https://mimic.mit.edu/docs/iv/modules/icu/procedureevents.html)
