# HospitalFlow — business data dictionary

## 1. Dictionary basic information

| Field | Value |
| --- | --- |
| dictionary_id | NL2EVENTLOG:hospitalflow |
| name | HospitalFlow |
| version | 2026-11-03-realism-revision |
| description | Business definitions for synthetic patient, hospital-stay, order and clinical-record data. |
| language | en |
| dbms | SQLite |
| timezone | UTC |
| datetime_representation | RFC 3339 text with UTC Z suffix and second precision; a documented convention, not a SQL format CHECK. |
| source_summary | MIMIC-IV-inspired meanings with authored table adaptations, identifiers, constraints and wholly synthetic records. |
| maintainer | NL2EVENTLOG project maintainers |

- This is a variable-level business dictionary, following Harvard HMS/OSF guidance and extended with relational schema metadata. Those guides do not prescribe one mandatory universal template.
- Measurement units apply to measured quantities. A timestamp is an instant: its format and timezone are documented separately rather than treating UTC as a measurement unit.
- Allowed codes and meanings are explicit. Unset minimum/maximum means no additional business bound is declared; observed sample minima/maxima are not allowed-value constraints.
- SQL constraints and documented conventions are distinct. This schema is not declared STRICT; a business numeric/datetime definition must not be mistaken for complete SQL format/type validation. Foreign-key enforcement requires PRAGMA foreign_keys=ON.
- NULL meanings are column-specific. No special numeric/text missing-value sentinel is defined. Synonyms are optional and are left empty rather than invented.

## 2. Table definitions

| Table | Readable name | One row represents | Primary key | Declared SQL foreign keys |
| --- | --- | --- | --- | --- |
| patients | Patients | One row per patient. | subject_id | None declared |
| admissions | Admissions | One row per hospital admission, identified by hadm_id. | hadm_id | subject_id -> patients.subject_id |
| patient_profile | Patient profile | At most one supplementary profile per patient. | subject_id | None declared |
| admission_detail | Admission detail | At most one signed-summary record per hospital admission. | hadm_id | hadm_id -> admissions.hadm_id |
| lab_order | Lab order | One authored laboratory request for one patient, optionally associated with an admission. | order_id | hadm_id -> admissions.hadm_id; subject_id -> patients.subject_id |
| medication_order | Medication order | One medication prescription; dispensing records and dose records have their own identities. | order_id | hadm_id -> admissions.hadm_id |
| procedure_order | Procedure order | One row per procedure order; multiple execution episodes may belong to it. | order_id | hadm_id -> admissions.hadm_id |
| order_history | Order history | One row per order-action occurrence, including repeated reviews. | history_id | procedure_order_id -> procedure_order.order_id; medication_order_id -> medication_order.order_id; lab_order_id -> lab_order.order_id |
| labevents | Labevents | One row per measurement occurrence; repeated measurements have different labevent_id values. | labevent_id | order_id -> lab_order.order_id |
| emar | Emar | One administration or omission record referring to one pharmacy dispensing record. | emar_id | pharmacy_id -> pharmacy.pharmacy_id |
| procedure_episode | Procedure episode | One hospital-level procedure execution episode, not an ICU stay. | procedureevent_id | order_id -> procedure_order.order_id |
| pharmacy | Pharmacy | One dispensing record for one medication prescription; a prescription may have zero or multiple dispensing records. | pharmacy_id | order_id -> medication_order.order_id |

- A declared SQL relationship and a documented identifier relationship are different metadata. In particular, patient_profile.subject_id uses the patients identifier by convention without a declared SQL FK.

## 3. Column definitions

### patients — Patients

- **Business definition:** Synthetic patient identity, inspired by MIMIC subject_id.
- **One row represents:** One row per patient.
- **Additional documented relationships:** None additionally documented

| Variable name | Readable name | Definition | Measurement unit | Allowed values / code meanings | NULL meaning | Format / timezone |
| --- | --- | --- | --- | --- | --- | --- |
| subject_id | Patient ID | Identifier of the patient represented by this row. | Not applicable | Integer identifier; no positive-only or business min/max CHECK is declared. | NULL is not allowed by the declared schema. | Integer identifier |
| gender | Patient gender category | Synthetic demographic category recorded for the patient. | Not applicable | F = Female category in the synthetic dataset; M = Male category in the synthetic dataset | NULL is not allowed by the declared schema. | Text |

**Storage and declared constraints**

| Variable | SQL type | Required | PK position | Declared FK | Unique | Default | Column constraints |
| --- | --- | --- | --- | --- | --- | --- | --- |
| subject_id | INTEGER | yes | 1 | None declared | yes | No SQL default | PRIMARY KEY NOT NULL |
| gender | TEXT | yes |  | None declared | no | No SQL default | NOT NULL CHECK(gender IN ('F','M')) |

```sql
CREATE TABLE patients(subject_id INTEGER PRIMARY KEY NOT NULL, gender TEXT NOT NULL CHECK(gender IN ('F','M')));
```

### admissions — Admissions

- **Business definition:** Distinct hospital stays per patient with actual admission/discharge milestones.
- **One row represents:** One row per hospital admission, identified by hadm_id.
- **Additional documented relationships:** None additionally documented

| Variable name | Readable name | Definition | Measurement unit | Allowed values / code meanings | NULL meaning | Format / timezone |
| --- | --- | --- | --- | --- | --- | --- |
| hadm_id | Hospital admission ID | Identifier of this particular hospital admission, distinct from the patient identifier. | Not applicable | Integer identifier; no positive-only or business min/max CHECK is declared. | NULL is not allowed by the declared schema. | Integer identifier |
| subject_id | Patient ID | Patient to whom this hospital admission belongs. | Not applicable | Existing patients.subject_id values. | NULL is not allowed by the declared schema. | Integer identifier |
| edregtime | Emergency department registration time | Time of emergency department registration associated with this admission. | Not applicable | UTC timestamp text using the documented format; no additional date range is declared. | No emergency department registration time is recorded; the simulation also uses this for admissions without ED registration. | RFC 3339 UTC text, YYYY-MM-DDTHH:MM:SSZ; timezone UTC |
| admittime | Hospital admission time | Time when the patient was admitted for this hospital stay. | Not applicable | UTC timestamp text using the documented format; no additional date range is declared. | NULL is not allowed by the declared schema. | RFC 3339 UTC text, YYYY-MM-DDTHH:MM:SSZ; timezone UTC |
| discharge_authorized_at | Discharge authorization time | Time when discharge from this hospital stay was authorized. | Not applicable | UTC timestamp text using the documented format; no additional date range is declared. | No discharge authorization time is recorded. | RFC 3339 UTC text, YYYY-MM-DDTHH:MM:SSZ; timezone UTC |
| dischtime | Hospital discharge time | Time when the patient actually left this hospital stay. | Not applicable | UTC timestamp text using the documented format; no additional date range is declared. | No discharge time is recorded; used for an ongoing stay in this simulation. | RFC 3339 UTC text, YYYY-MM-DDTHH:MM:SSZ; timezone UTC |

**Storage and declared constraints**

| Variable | SQL type | Required | PK position | Declared FK | Unique | Default | Column constraints |
| --- | --- | --- | --- | --- | --- | --- | --- |
| hadm_id | INTEGER | yes | 1 | None declared | yes | No SQL default | PRIMARY KEY NOT NULL |
| subject_id | INTEGER | yes |  | patients.subject_id | no | No SQL default | NOT NULL REFERENCES patients(subject_id) |
| edregtime | TEXT | no |  | None declared | no | No SQL default | No additional column constraint |
| admittime | TEXT | yes |  | None declared | no | No SQL default | NOT NULL |
| discharge_authorized_at | TEXT | no |  | None declared | no | No SQL default | No additional column constraint |
| dischtime | TEXT | no |  | None declared | no | No SQL default | No additional column constraint |

- **Definition references:** [https://mimic.mit.edu/docs/iv/modules/hosp/admissions.html](https://mimic.mit.edu/docs/iv/modules/hosp/admissions.html). Local SQL constraints and synthetic adaptations remain HospitalFlow conventions.

```sql
CREATE TABLE admissions(hadm_id INTEGER PRIMARY KEY NOT NULL, subject_id INTEGER NOT NULL REFERENCES patients(subject_id), edregtime TEXT, admittime TEXT NOT NULL, discharge_authorized_at TEXT, dischtime TEXT, CHECK(edregtime IS NULL OR edregtime<=admittime), CHECK(dischtime IS NULL OR discharge_authorized_at<=dischtime));
```

### patient_profile — Patient profile

- **Business definition:** Optional additional information for the SAME patient identified by patients.subject_id, in the SAME identifier namespace. A matching subject_id denotes the same actual patient. No FK is declared; this identity relationship is explicitly documented. Authored split-storage extension.
- **One row represents:** At most one supplementary profile per patient.
- **Additional documented relationships:** subject_id -> patients(subject_id): Documented identifier relationship; no declared SQL foreign key

| Variable name | Readable name | Definition | Measurement unit | Allowed values / code meanings | NULL meaning | Format / timezone |
| --- | --- | --- | --- | --- | --- | --- |
| subject_id | Patient ID | Identifier of the same patient represented in patients.subject_id; this is a documented shared identifier, not a declared SQL foreign key. | Not applicable | Patient identifiers in patients.subject_id by documented convention; no SQL foreign key enforces that relationship. | NULL is not allowed by the declared schema. | Integer identifier |
| profile_verified_at | Profile verification time | Time when the supplementary patient information was verified. | Not applicable | UTC timestamp text using the documented format; no additional date range is declared. | NULL is not allowed by the declared schema. | RFC 3339 UTC text, YYYY-MM-DDTHH:MM:SSZ; timezone UTC |
| preferred_language | Preferred language | Language preference recorded in the supplementary patient information. | Not applicable | Text; no controlled vocabulary or maximum text length is declared. | NULL is not allowed by the declared schema. | Text |

**Storage and declared constraints**

| Variable | SQL type | Required | PK position | Declared FK | Unique | Default | Column constraints |
| --- | --- | --- | --- | --- | --- | --- | --- |
| subject_id | INTEGER | yes | 1 | None declared | yes | No SQL default | PRIMARY KEY NOT NULL |
| profile_verified_at | TEXT | yes |  | None declared | no | No SQL default | NOT NULL |
| preferred_language | TEXT | yes |  | None declared | no | No SQL default | NOT NULL |

- **subject_id:** This logical patient reference is intentionally not a declared SQL FK; keep documented relationships separate from enforced relationships.

```sql
CREATE TABLE patient_profile(subject_id INTEGER PRIMARY KEY NOT NULL, profile_verified_at TEXT NOT NULL, preferred_language TEXT NOT NULL);
```

### admission_detail — Admission detail

- **Business definition:** Optional additional information for the SAME hospital stay identified by admissions.hadm_id. A matching hadm_id denotes the same actual admission. Only a subset of admissions has a signed summary. Authored split-storage extension.
- **One row represents:** At most one signed-summary record per hospital admission.
- **Additional documented relationships:** None additionally documented

| Variable name | Readable name | Definition | Measurement unit | Allowed values / code meanings | NULL meaning | Format / timezone |
| --- | --- | --- | --- | --- | --- | --- |
| hadm_id | Hospital admission ID | Identifier of the same hospital stay represented in admissions.hadm_id. | Not applicable | Existing admissions.hadm_id values. | NULL is not allowed by the declared schema. | Integer identifier |
| discharge_summary_signed_at | Discharge summary signing time | Time when the discharge summary for this hospital stay was signed. | Not applicable | UTC timestamp text using the documented format; no additional date range is declared. | NULL is not allowed by the declared schema. | RFC 3339 UTC text, YYYY-MM-DDTHH:MM:SSZ; timezone UTC |
| summary_status | Discharge summary status | Recorded signing status of this discharge summary. | Not applicable | SIGNED = The discharge summary has been signed | NULL is not allowed by the declared schema. | Text |

**Storage and declared constraints**

| Variable | SQL type | Required | PK position | Declared FK | Unique | Default | Column constraints |
| --- | --- | --- | --- | --- | --- | --- | --- |
| hadm_id | INTEGER | yes | 1 | admissions.hadm_id | yes | No SQL default | PRIMARY KEY NOT NULL REFERENCES admissions(hadm_id) |
| discharge_summary_signed_at | TEXT | yes |  | None declared | no | No SQL default | NOT NULL |
| summary_status | TEXT | yes |  | None declared | no | No SQL default | NOT NULL CHECK(summary_status='SIGNED') |

```sql
CREATE TABLE admission_detail(hadm_id INTEGER PRIMARY KEY NOT NULL REFERENCES admissions(hadm_id), discharge_summary_signed_at TEXT NOT NULL, summary_status TEXT NOT NULL CHECK(summary_status='SIGNED'));
```

### lab_order — Lab order

- **Business definition:** Authored laboratory request; multiple measurements can fulfill it. subject_id identifies the patient even when hadm_id is NULL for a request outside an admission.
- **One row represents:** One authored laboratory request for one patient, optionally associated with an admission.
- **Additional documented relationships:** None additionally documented

| Variable name | Readable name | Definition | Measurement unit | Allowed values / code meanings | NULL meaning | Format / timezone |
| --- | --- | --- | --- | --- | --- | --- |
| order_id | Laboratory order ID | Identifier of this laboratory request in the laboratory-order identifier namespace. | Not applicable | Integer identifier; no positive-only or business min/max CHECK is declared. | NULL is not allowed by the declared schema. | Integer identifier |
| subject_id | Patient ID | Patient for this laboratory request, including requests not associated with a hospital admission. | Not applicable | Patient identifiers in patients.subject_id by documented convention; no SQL foreign key enforces that relationship. | NULL is not allowed by the declared schema. | Integer identifier |
| hadm_id | Hospital admission ID | Optional hospital admission associated with this laboratory request. | Not applicable | Existing admissions.hadm_id values. | No hospital admission is associated with this request, as in outpatient testing. | Integer identifier |
| specimen_received_at | Specimen receipt time | Time when the specimen associated with this laboratory order was received. | Not applicable | UTC timestamp text using the documented format; no additional date range is declared. | No specimen receipt time is recorded. | RFC 3339 UTC text, YYYY-MM-DDTHH:MM:SSZ; timezone UTC |
| results_verified_at | Laboratory results verification time | Time when the recorded results for this laboratory order were verified. | Not applicable | UTC timestamp text using the documented format; no additional date range is declared. | No results-verification time is recorded. | RFC 3339 UTC text, YYYY-MM-DDTHH:MM:SSZ; timezone UTC |

**Storage and declared constraints**

| Variable | SQL type | Required | PK position | Declared FK | Unique | Default | Column constraints |
| --- | --- | --- | --- | --- | --- | --- | --- |
| order_id | INTEGER | yes | 1 | None declared | yes | No SQL default | PRIMARY KEY NOT NULL |
| subject_id | INTEGER | yes |  | patients.subject_id | no | No SQL default | NOT NULL REFERENCES patients(subject_id) |
| hadm_id | INTEGER | no |  | admissions.hadm_id | no | No SQL default | REFERENCES admissions(hadm_id) |
| specimen_received_at | TEXT | no |  | None declared | no | No SQL default | No additional column constraint |
| results_verified_at | TEXT | no |  | None declared | no | No SQL default | No additional column constraint |

- **order_id:** Equal integer values in the three order tables do not establish the same request identity.

- **subject_id:** This logical patient reference is intentionally not a declared SQL FK; keep documented relationships separate from enforced relationships.

```sql
CREATE TABLE lab_order(order_id INTEGER PRIMARY KEY NOT NULL, subject_id INTEGER NOT NULL REFERENCES patients(subject_id), hadm_id INTEGER REFERENCES admissions(hadm_id), specimen_received_at TEXT, results_verified_at TEXT);
```

### medication_order — Medication order

- **Business definition:** One medication prescription, including its stop time. Dispensing is recorded separately in pharmacy.
- **One row represents:** One medication prescription; dispensing records and dose records have their own identities.
- **Additional documented relationships:** None additionally documented

| Variable name | Readable name | Definition | Measurement unit | Allowed values / code meanings | NULL meaning | Format / timezone |
| --- | --- | --- | --- | --- | --- | --- |
| order_id | Medication order ID | Identifier of this medication request in the medication-order identifier namespace. | Not applicable | Integer identifier; no positive-only or business min/max CHECK is declared. | NULL is not allowed by the declared schema. | Integer identifier |
| hadm_id | Hospital admission ID | Hospital admission under which this medication request was made. | Not applicable | Existing admissions.hadm_id values. | NULL is not allowed by the declared schema. | Integer identifier |
| medication | Medication name | Generic medication name for synthetic records; not a treatment recommendation. | Not applicable | Text; no controlled vocabulary or maximum text length is declared. | NULL is not allowed by the declared schema. | Text |
| stopped_at | Medication stopping time | Time when medication under this request was stopped. | Not applicable | UTC timestamp text using the documented format; no additional date range is declared. | No medication stopping time is recorded. | RFC 3339 UTC text, YYYY-MM-DDTHH:MM:SSZ; timezone UTC |

**Storage and declared constraints**

| Variable | SQL type | Required | PK position | Declared FK | Unique | Default | Column constraints |
| --- | --- | --- | --- | --- | --- | --- | --- |
| order_id | INTEGER | yes | 1 | None declared | yes | No SQL default | PRIMARY KEY NOT NULL |
| hadm_id | INTEGER | yes |  | admissions.hadm_id | no | No SQL default | NOT NULL REFERENCES admissions(hadm_id) |
| medication | TEXT | yes |  | None declared | no | No SQL default | NOT NULL |
| stopped_at | TEXT | no |  | None declared | no | No SQL default | No additional column constraint |

- **order_id:** Equal integer values in the three order tables do not establish the same request identity.

- **medication:** Illustrative generic drug labels; these records do not represent treatment recommendations.

```sql
CREATE TABLE medication_order(order_id INTEGER PRIMARY KEY NOT NULL, hadm_id INTEGER NOT NULL REFERENCES admissions(hadm_id), medication TEXT NOT NULL, stopped_at TEXT);
```

### procedure_order — Procedure order

- **Business definition:** Distinct procedure order; repeated execution episodes belong to one order.
- **One row represents:** One row per procedure order; multiple execution episodes may belong to it.
- **Additional documented relationships:** None additionally documented

| Variable name | Readable name | Definition | Measurement unit | Allowed values / code meanings | NULL meaning | Format / timezone |
| --- | --- | --- | --- | --- | --- | --- |
| order_id | Procedure order ID | Identifier of this procedure request in the procedure-order identifier namespace. | Not applicable | Integer identifier; no positive-only or business min/max CHECK is declared. | NULL is not allowed by the declared schema. | Integer identifier |
| hadm_id | Hospital admission ID | Hospital admission under which this procedure request was made. | Not applicable | Existing admissions.hadm_id values. | NULL is not allowed by the declared schema. | Integer identifier |
| procedure_name | Procedure name | Fictional procedure label associated with this synthetic procedure request. | Not applicable | Text; no controlled vocabulary or maximum text length is declared. | NULL is not allowed by the declared schema. | Text |
| preparation_completed_at | Procedure preparation completion time | Time when preparation for this procedure request was completed. | Not applicable | UTC timestamp text using the documented format; no additional date range is declared. | No preparation completion time is recorded. | RFC 3339 UTC text, YYYY-MM-DDTHH:MM:SSZ; timezone UTC |

**Storage and declared constraints**

| Variable | SQL type | Required | PK position | Declared FK | Unique | Default | Column constraints |
| --- | --- | --- | --- | --- | --- | --- | --- |
| order_id | INTEGER | yes | 1 | None declared | yes | No SQL default | PRIMARY KEY NOT NULL |
| hadm_id | INTEGER | yes |  | admissions.hadm_id | no | No SQL default | NOT NULL REFERENCES admissions(hadm_id) |
| procedure_name | TEXT | yes |  | None declared | no | No SQL default | NOT NULL |
| preparation_completed_at | TEXT | no |  | None declared | no | No SQL default | No additional column constraint |

- **order_id:** Equal integer values in the three order tables do not establish the same request identity.

```sql
CREATE TABLE procedure_order(order_id INTEGER PRIMARY KEY NOT NULL, hadm_id INTEGER NOT NULL REFERENCES admissions(hadm_id), procedure_name TEXT NOT NULL, preparation_completed_at TEXT);
```

### order_history — Order history

- **Business definition:** Repeated order actions, inspired by provider order transaction semantics; not a copy of poe.
- **One row represents:** One row per order-action occurrence, including repeated reviews.
- **Additional documented relationships:** None additionally documented

| Variable name | Readable name | Definition | Measurement unit | Allowed values / code meanings | NULL meaning | Format / timezone |
| --- | --- | --- | --- | --- | --- | --- |
| history_id | Order action record ID | Identifier of one order-action occurrence; separate reviews of an order have separate identifiers. | Not applicable | Integer identifier; no positive-only or business min/max CHECK is declared. | NULL is not allowed by the declared schema. | Integer identifier |
| lab_order_id | Referenced laboratory order ID | Laboratory order on which this action was performed, when the action concerns a laboratory request. | Not applicable | Existing lab_order.order_id values. | The action concerns another order category; exactly one order-reference column is non-NULL. | Integer identifier |
| medication_order_id | Referenced medication order ID | Medication order on which this action was performed, when the action concerns a medication request. | Not applicable | Existing medication_order.order_id values. | The action concerns another order category; exactly one order-reference column is non-NULL. | Integer identifier |
| procedure_order_id | Referenced procedure order ID | Procedure order on which this action was performed, when the action concerns a procedure request. | Not applicable | Existing procedure_order.order_id values. | The action concerns another order category; exactly one order-reference column is non-NULL. | Integer identifier |
| action | Recorded order action | Kind of action performed on the referenced order. | Not applicable | ENTERED = The order was entered; REVIEWED = The order was reviewed; CANCELLED = The order was cancelled | NULL is not allowed by the declared schema. | Text |
| occurred_at | Order action time | Time when this particular order action occurred. | Not applicable | UTC timestamp text using the documented format; no additional date range is declared. | NULL is not allowed by the declared schema. | RFC 3339 UTC text, YYYY-MM-DDTHH:MM:SSZ; timezone UTC |

**Storage and declared constraints**

| Variable | SQL type | Required | PK position | Declared FK | Unique | Default | Column constraints |
| --- | --- | --- | --- | --- | --- | --- | --- |
| history_id | INTEGER | yes | 1 | None declared | yes | No SQL default | PRIMARY KEY NOT NULL |
| lab_order_id | INTEGER | no |  | lab_order.order_id | no | No SQL default | REFERENCES lab_order(order_id) |
| medication_order_id | INTEGER | no |  | medication_order.order_id | no | No SQL default | REFERENCES medication_order(order_id) |
| procedure_order_id | INTEGER | no |  | procedure_order.order_id | no | No SQL default | REFERENCES procedure_order(order_id) |
| action | TEXT | yes |  | None declared | no | No SQL default | NOT NULL CHECK(action IN ('ENTERED','REVIEWED','CANCELLED')) |
| occurred_at | TEXT | yes |  | None declared | no | No SQL default | NOT NULL |

```sql
CREATE TABLE order_history(history_id INTEGER PRIMARY KEY NOT NULL, lab_order_id INTEGER REFERENCES lab_order(order_id), medication_order_id INTEGER REFERENCES medication_order(order_id), procedure_order_id INTEGER REFERENCES procedure_order(order_id), action TEXT NOT NULL CHECK(action IN ('ENTERED','REVIEWED','CANCELLED')), occurred_at TEXT NOT NULL, CHECK((lab_order_id IS NOT NULL)+(medication_order_id IS NOT NULL)+(procedure_order_id IS NOT NULL)=1));
```

### labevents — Labevents

- **Business definition:** Measurement occurrences with separately charted and available-result times, inspired by MIMIC labevents.
- **One row represents:** One row per measurement occurrence; repeated measurements have different labevent_id values.
- **Additional documented relationships:** None additionally documented

| Variable name | Readable name | Definition | Measurement unit | Allowed values / code meanings | NULL meaning | Format / timezone |
| --- | --- | --- | --- | --- | --- | --- |
| labevent_id | Laboratory measurement ID | Identifier of this individual laboratory measurement occurrence. | Not applicable | Integer identifier; no positive-only or business min/max CHECK is declared. | NULL is not allowed by the declared schema. | Integer identifier |
| order_id | Referenced laboratory order ID | Laboratory order to which this measurement belongs. | Not applicable | Existing lab_order.order_id values. | NULL is not allowed by the declared schema. | Integer identifier |
| itemid | Laboratory measurement category ID | Authored laboratory concept: 1001 Creatinine (mg/dL), 1002 Sodium (mmol/L), 1003 Hemoglobin (g/dL). Not original MIMIC codes. | Not applicable | 1001 = Creatinine; 1002 = Sodium; 1003 = Hemoglobin. Authored concept codes. | NULL is not allowed by the declared schema. | Integer identifier |
| charttime | Laboratory measurement charting time | Time assigned to the charted laboratory measurement; distinct from the time the result became available. | Not applicable | UTC timestamp text using the documented format; no additional date range is declared. | NULL is not allowed by the declared schema. | RFC 3339 UTC text, YYYY-MM-DDTHH:MM:SSZ; timezone UTC |
| storetime | Laboratory result availability time | Time when this laboratory result became available in the laboratory system. | Not applicable | UTC timestamp text using the documented format; no additional date range is declared. | NULL is not allowed by the declared schema. | RFC 3339 UTC text, YYYY-MM-DDTHH:MM:SSZ; timezone UTC |
| valuenum | Numeric measurement result | Numeric result recorded for this synthetic laboratory measurement. | As specified by valueuom for the corresponding test. | Numeric measurement value; no SQL min/max bound is declared. | No numeric measurement result is recorded. | Numeric value |
| valueuom | Measurement unit label | Measurement unit; mg/dL for Creatinine, mmol/L for Sodium, g/dL for Hemoglobin. | Not applicable | mg/dL, mmol/L or g/dL, as specified by itemid. | No measurement unit is specified. | Text |

**Storage and declared constraints**

| Variable | SQL type | Required | PK position | Declared FK | Unique | Default | Column constraints |
| --- | --- | --- | --- | --- | --- | --- | --- |
| labevent_id | INTEGER | yes | 1 | None declared | yes | No SQL default | PRIMARY KEY NOT NULL |
| order_id | INTEGER | yes |  | lab_order.order_id | no | No SQL default | NOT NULL REFERENCES lab_order(order_id) |
| itemid | INTEGER | yes |  | None declared | no | No SQL default | NOT NULL |
| charttime | TEXT | yes |  | None declared | no | No SQL default | NOT NULL |
| storetime | TEXT | yes |  | None declared | no | No SQL default | NOT NULL |
| valuenum | REAL | no |  | None declared | no | No SQL default | No additional column constraint |
| valueuom | TEXT | no |  | None declared | no | No SQL default | No additional column constraint |

- **itemid:** Authored concept dictionary; no original MIMIC item IDs are claimed.

- **valuenum:** Synthetic illustrative values; not fitted to clinical distributions.

- **valueuom:** 1001 uses mg/dL; 1002 uses mmol/L; 1003 uses g/dL.

- **Definition references:** [https://mimic.mit.edu/docs/iv/modules/hosp/labevents.html](https://mimic.mit.edu/docs/iv/modules/hosp/labevents.html). Local SQL constraints and synthetic adaptations remain HospitalFlow conventions.

```sql
CREATE TABLE labevents(labevent_id INTEGER PRIMARY KEY NOT NULL, order_id INTEGER NOT NULL REFERENCES lab_order(order_id), itemid INTEGER NOT NULL, charttime TEXT NOT NULL, storetime TEXT NOT NULL, valuenum REAL, valueuom TEXT, CHECK(charttime<=storetime));
```

### emar — Emar

- **Business definition:** Medication administration or omission occurrences, inspired by MIMIC emar.
- **One row represents:** One administration or omission record referring to one pharmacy dispensing record.
- **Additional documented relationships:** None additionally documented

| Variable name | Readable name | Definition | Measurement unit | Allowed values / code meanings | NULL meaning | Format / timezone |
| --- | --- | --- | --- | --- | --- | --- |
| emar_id | Dose record ID | Local integer identifier of this administration or omission record; it is not the original MIMIC formatted eMAR identifier. | Not applicable | Integer identifier; no positive-only or business min/max CHECK is declared. | NULL is not allowed by the declared schema. | Integer identifier |
| pharmacy_id | Pharmacy dispensing ID | Dispensing record associated with this administration or omission. | Not applicable | Integer dispensing identifier; emar references an existing pharmacy record. | NULL is not allowed by the declared schema. | Integer identifier |
| charttime | Administration or omission time | Time when the administration or omission documented by this dose record occurred. | Not applicable | UTC timestamp text using the documented format; no additional date range is declared. | NULL is not allowed by the declared schema. | RFC 3339 UTC text, YYYY-MM-DDTHH:MM:SSZ; timezone UTC |
| event_txt | Administration disposition | Recorded disposition of this medication dose, indicating administration or omission. | Not applicable | Administered = The medication dose was given; Not Given = The medication dose was not given | NULL is not allowed by the declared schema. | Text |
| storetime | Dose documentation time | Time when the dose record was documented in the medication system. | Not applicable | UTC timestamp text using the documented format; no additional date range is declared. | NULL is not allowed by the declared schema. | RFC 3339 UTC text, YYYY-MM-DDTHH:MM:SSZ; timezone UTC |

**Storage and declared constraints**

| Variable | SQL type | Required | PK position | Declared FK | Unique | Default | Column constraints |
| --- | --- | --- | --- | --- | --- | --- | --- |
| emar_id | INTEGER | yes | 1 | None declared | yes | No SQL default | PRIMARY KEY NOT NULL |
| pharmacy_id | INTEGER | yes |  | pharmacy.pharmacy_id | no | No SQL default | NOT NULL REFERENCES pharmacy(pharmacy_id) |
| charttime | TEXT | yes |  | None declared | no | No SQL default | NOT NULL |
| event_txt | TEXT | yes |  | None declared | no | No SQL default | NOT NULL CHECK(event_txt IN ('Administered','Not Given')) |
| storetime | TEXT | yes |  | None declared | no | No SQL default | NOT NULL |

- **Definition references:** [https://mimic.mit.edu/docs/iv/modules/hosp/emar.html](https://mimic.mit.edu/docs/iv/modules/hosp/emar.html). Local SQL constraints and synthetic adaptations remain HospitalFlow conventions.

```sql
CREATE TABLE emar(emar_id INTEGER PRIMARY KEY NOT NULL, pharmacy_id INTEGER NOT NULL REFERENCES pharmacy(pharmacy_id), charttime TEXT NOT NULL, event_txt TEXT NOT NULL CHECK(event_txt IN ('Administered','Not Given')), storetime TEXT NOT NULL, CHECK(charttime<=storetime));
```

### procedure_episode — Procedure episode

- **Business definition:** Authored hospital-level procedure execution episode; not the MIMIC ICU procedureevents table.
- **One row represents:** One hospital-level procedure execution episode, not an ICU stay.
- **Additional documented relationships:** None additionally documented

| Variable name | Readable name | Definition | Measurement unit | Allowed values / code meanings | NULL meaning | Format / timezone |
| --- | --- | --- | --- | --- | --- | --- |
| procedureevent_id | Procedure episode ID | Local synthetic identifier of one procedure execution episode; repeat episodes have separate identifiers. | Not applicable | Integer identifier; no positive-only or business min/max CHECK is declared. | NULL is not allowed by the declared schema. | Integer identifier |
| order_id | Referenced procedure order ID | Procedure order executed in this episode. | Not applicable | Existing procedure_order.order_id values. | NULL is not allowed by the declared schema. | Integer identifier |
| starttime | Procedure episode start time | Time when this procedure execution episode began. | Not applicable | UTC timestamp text using the documented format; no additional date range is declared. | NULL is not allowed by the declared schema. | RFC 3339 UTC text, YYYY-MM-DDTHH:MM:SSZ; timezone UTC |
| endtime | Procedure episode end time | Time when this procedure execution episode ended. | Not applicable | UTC timestamp text using the documented format; no additional date range is declared. | No completion time is recorded; used for an ongoing episode in this simulation. | RFC 3339 UTC text, YYYY-MM-DDTHH:MM:SSZ; timezone UTC |
| storetime | Procedure episode documentation time | Time when this episode was recorded in the procedure system. | Not applicable | UTC timestamp text using the documented format; no additional date range is declared. | NULL is not allowed by the declared schema. | RFC 3339 UTC text, YYYY-MM-DDTHH:MM:SSZ; timezone UTC |

**Storage and declared constraints**

| Variable | SQL type | Required | PK position | Declared FK | Unique | Default | Column constraints |
| --- | --- | --- | --- | --- | --- | --- | --- |
| procedureevent_id | INTEGER | yes | 1 | None declared | yes | No SQL default | PRIMARY KEY NOT NULL |
| order_id | INTEGER | yes |  | procedure_order.order_id | no | No SQL default | NOT NULL REFERENCES procedure_order(order_id) |
| starttime | TEXT | yes |  | None declared | no | No SQL default | NOT NULL |
| endtime | TEXT | no |  | None declared | no | No SQL default | No additional column constraint |
| storetime | TEXT | yes |  | None declared | no | No SQL default | NOT NULL |

```sql
CREATE TABLE procedure_episode(procedureevent_id INTEGER PRIMARY KEY NOT NULL, order_id INTEGER NOT NULL REFERENCES procedure_order(order_id), starttime TEXT NOT NULL, endtime TEXT, storetime TEXT NOT NULL, CHECK(endtime IS NULL OR starttime<=endtime));
```

### pharmacy — Pharmacy

- **Business definition:** One distinct dispensing record for a medication prescription; repeated dispensing records can fulfill the same prescription.
- **One row represents:** One dispensing record for one medication prescription; a prescription may have zero or multiple dispensing records.
- **Additional documented relationships:** None additionally documented

| Variable name | Readable name | Definition | Measurement unit | Allowed values / code meanings | NULL meaning | Format / timezone |
| --- | --- | --- | --- | --- | --- | --- |
| pharmacy_id | Pharmacy dispensing ID | Identifier of a single pharmacy dispensing record, distinct from prescription and administration identifiers. | Not applicable | Integer dispensing identifier; emar references an existing pharmacy record. | NULL is not allowed by the declared schema. | Integer identifier |
| order_id | Medication order ID | Medication prescription fulfilled by this dispensing record. | Not applicable | Integer identifier; no positive-only or business min/max CHECK is declared. | NULL is not allowed by the declared schema. | Integer identifier |
| dispensed_at | Medication dispensing time | Time when medication for this request was dispensed. | Not applicable | UTC timestamp text using the documented format; no additional date range is declared. | NULL is not allowed by the declared schema. | RFC 3339 UTC text, YYYY-MM-DDTHH:MM:SSZ; timezone UTC |

**Storage and declared constraints**

| Variable | SQL type | Required | PK position | Declared FK | Unique | Default | Column constraints |
| --- | --- | --- | --- | --- | --- | --- | --- |
| pharmacy_id | INTEGER | yes | 1 | None declared | yes | No SQL default | PRIMARY KEY NOT NULL |
| order_id | INTEGER | yes |  | medication_order.order_id | no | No SQL default | NOT NULL REFERENCES medication_order(order_id) |
| dispensed_at | TEXT | yes |  | None declared | no | No SQL default | NOT NULL |

- **dispensed_at:** Authored dispensing milestone; not an original MIMIC pharmacy column.

```sql
CREATE TABLE pharmacy(pharmacy_id INTEGER PRIMARY KEY NOT NULL, order_id INTEGER NOT NULL REFERENCES medication_order(order_id), dispensed_at TEXT NOT NULL);
```

### Cross-table business conventions

- A patient can have multiple hospital admissions; hadm_id identifies an admission and subject_id identifies a patient.
- Supplementary profile rows use the patient identifier documented in patients; their logical relationship is not enforced by an SQL foreign key.
- A signed-summary row uses the identifier of its hospital admission.
- Laboratory, medication and procedure requests have separate local identifier namespaces.
- An order-action history row has exactly one populated order-reference column; repeated reviews are separate records.
- A laboratory order can have multiple measurements; a medication order can have multiple dose records; a procedure order can have multiple execution episodes.
- Laboratory charting and result availability are different recorded times. Medication/procedure documentation times describe system recording.
- Missing timestamps describe unrecorded times according to the column definition; NULL does not universally establish that an action never happened.
- Identifiers, text lengths and numeric ranges have no extra restrictions inferred from the current sample. SQL constraints and documented representation conventions are distinguished.
- All rows are synthetic. MIMIC documentation informs selected meanings, not a claim of original MIMIC identifiers, full schema coverage or patient-record reuse.
- Laboratory, medication and procedure requests retain separate identifier namespaces; equal local values identify different requests.
- lab_order.subject_id identifies its patient even when hadm_id is NULL. When hadm_id is present its patient must agree with admissions.subject_id; this is a documented cross-table rule checked by the construction validator.
- medication_order represents a prescription; pharmacy represents a dispensing record; emar represents an administration or omission associated with one dispensing record.
- Lab concept codes 1001, 1002 and 1003 mean Creatinine (mg/dL), Sodium (mmol/L) and Hemoglobin (g/dL), respectively.
- The three order tables are an intentional alternative to MIMIC poe; laboratory-request and dispensing-milestone structures are authored simplifications.
- Hospital-level procedure_episode is authored and does not reproduce the ICU procedureevents table.

### Documentation references

- [Harvard HMS Data Dictionary](https://datamanagement.hms.harvard.edu/collect-analyze/documentation-metadata/data-dictionary)
- [OSF How to Make a Data Dictionary](https://help.osf.io/article/217-how-to-make-a-data-dictionary)
- [SQLite CREATE TABLE and declared constraints](https://www.sqlite.org/lang_createtable.html)
