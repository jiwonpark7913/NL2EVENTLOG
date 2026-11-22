# HospitalFlow — business data dictionary

## 1. Dictionary basic information

| Field | Value |
| --- | --- |
| dictionary_id | NL2EVENTLOG:hospitalflow |
| name | HospitalFlow |
| version | 2026-11-03-semantics-revision |
| language | en |
| dbms | SQLite |
| timezone | UTC |
| datetime_representation | RFC 3339 UTC text, YYYY-MM-DDTHH:MM:SSZ |

## 2. Table definitions

| Table | Readable name | One row represents | Primary key | Declared SQL foreign keys |
| --- | --- | --- | --- | --- |
| patients | Patients | One row per patient. | subject_id | None declared |
| admissions | Admissions | One row per hospital admission, identified by hadm_id. | hadm_id | subject_id -> patients.subject_id |
| patient_profile | Patient profile | At most one supplementary profile per patient. | subject_id | None declared |
| admission_detail | Admission detail | One recorded signed discharge summary per admission represented in this table. Draft documents are outside this table. | hadm_id | hadm_id -> admissions.hadm_id |
| lab_order | Lab order | One authored laboratory request for one patient, optionally associated with an admission. | order_id | hadm_id -> admissions.hadm_id; subject_id -> patients.subject_id |
| medication_order | Medication order | One medication prescription; dispensing records and dose records have their own identities. | order_id | hadm_id -> admissions.hadm_id |
| procedure_order | Procedure order | One row per procedure order; multiple execution episodes may belong to it. | order_id | hadm_id -> admissions.hadm_id |
| order_history | Order history | One row per order-action occurrence, including repeated reviews. | history_id | procedure_order_id -> procedure_order.order_id; medication_order_id -> medication_order.order_id; lab_order_id -> lab_order.order_id |
| labevents | Labevents | One laboratory measurement result associated with a collected specimen and a laboratory request; collection and result availability have separate timestamps. | labevent_id | order_id -> lab_order.order_id |
| emar | Emar | One administration or omission record referring to one pharmacy dispensing record. | emar_id | pharmacy_id -> pharmacy.pharmacy_id |
| procedure_episode | Procedure episode | One hospital-level procedure execution episode, not an ICU stay. | procedureevent_id | order_id -> procedure_order.order_id |
| pharmacy | Pharmacy | One dispensing record for one medication prescription; a prescription may have zero or multiple dispensing records. | pharmacy_id | order_id -> medication_order.order_id |

## 3. Column definitions

### patients — Patients

- **Business definition:** Patient identifiers and demographic categories.
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
| edregtime | Emergency department registration time | Time of emergency department registration associated with this admission. | Not applicable | UTC timestamp text using the documented format; no additional date range is declared. | No emergency department registration time is recorded. Whether an ED registration occurred is unknown. | RFC 3339 UTC text, YYYY-MM-DDTHH:MM:SSZ; timezone UTC |
| admittime | Hospital admission time | Time when the patient was admitted for this hospital stay. | Not applicable | UTC timestamp text using the documented format; no additional date range is declared. | NULL is not allowed by the declared schema. | RFC 3339 UTC text, YYYY-MM-DDTHH:MM:SSZ; timezone UTC |
| discharge_authorized_at | Discharge authorization time | Time when discharge from this hospital stay was authorized. | Not applicable | UTC timestamp text using the documented format; no additional date range is declared. | No discharge authorization time is recorded. Whether authorization occurred is unknown. | RFC 3339 UTC text, YYYY-MM-DDTHH:MM:SSZ; timezone UTC |
| dischtime | Hospital discharge time | Time when the patient actually left this hospital stay. | Not applicable | UTC timestamp text using the documented format; no additional date range is declared. | No discharge time is recorded. Whether discharge occurred is unknown; an ongoing stay cannot be inferred from NULL alone. | RFC 3339 UTC text, YYYY-MM-DDTHH:MM:SSZ; timezone UTC |

**Storage and declared constraints**

| Variable | SQL type | Required | PK position | Declared FK | Unique | Default | Column constraints |
| --- | --- | --- | --- | --- | --- | --- | --- |
| hadm_id | INTEGER | yes | 1 | None declared | yes | No SQL default | PRIMARY KEY NOT NULL |
| subject_id | INTEGER | yes |  | patients.subject_id | no | No SQL default | NOT NULL REFERENCES patients(subject_id) |
| edregtime | TEXT | no |  | None declared | no | No SQL default | No additional column constraint |
| admittime | TEXT | yes |  | None declared | no | No SQL default | NOT NULL |
| discharge_authorized_at | TEXT | no |  | None declared | no | No SQL default | No additional column constraint |
| dischtime | TEXT | no |  | None declared | no | No SQL default | No additional column constraint |

- **Definition references:** [https://mimic.mit.edu/docs/iv/modules/hosp/admissions.html](https://mimic.mit.edu/docs/iv/modules/hosp/admissions.html).

- **Constraint interpretation:** CHECK(dischtime IS NULL OR discharge_authorized_at<=dischtime) rejects a known authorization time later than discharge. When discharge_authorized_at is NULL and dischtime is present, the expression evaluates to UNKNOWN and SQLite permits the row. Authorization is not mandatory for a recorded discharge.

```sql
CREATE TABLE admissions(hadm_id INTEGER PRIMARY KEY NOT NULL, subject_id INTEGER NOT NULL REFERENCES patients(subject_id), edregtime TEXT, admittime TEXT NOT NULL, discharge_authorized_at TEXT, dischtime TEXT, CHECK(edregtime IS NULL OR edregtime<=admittime), CHECK(dischtime IS NULL OR discharge_authorized_at<=dischtime));
```

### patient_profile — Patient profile

- **Business definition:** Supplementary patient information keyed by patients.subject_id. Matching subject_id refers to the patient in patients; no SQL foreign key is declared.
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

- **Business definition:** Recorded signed discharge summaries associated with hospital admissions.
- **One row represents:** One recorded signed discharge summary per admission represented in this table. Draft documents are outside this table.
- **Additional documented relationships:** None additionally documented

| Variable name | Readable name | Definition | Measurement unit | Allowed values / code meanings | NULL meaning | Format / timezone |
| --- | --- | --- | --- | --- | --- | --- |
| hadm_id | Hospital admission ID | Identifier of the same hospital stay represented in admissions.hadm_id. | Not applicable | Existing admissions.hadm_id values. | NULL is not allowed by the declared schema. | Integer identifier |
| discharge_summary_signed_at | Discharge summary signing time | Time when the discharge summary for this admission was signed; signing may occur after the patient has left the hospital. | Not applicable | UTC timestamp text using the documented format; no additional date range is declared. | NULL is not allowed by the declared schema. | RFC 3339 UTC text, YYYY-MM-DDTHH:MM:SSZ; timezone UTC |

**Storage and declared constraints**

| Variable | SQL type | Required | PK position | Declared FK | Unique | Default | Column constraints |
| --- | --- | --- | --- | --- | --- | --- | --- |
| hadm_id | INTEGER | yes | 1 | admissions.hadm_id | yes | No SQL default | PRIMARY KEY NOT NULL REFERENCES admissions(hadm_id) |
| discharge_summary_signed_at | TEXT | yes |  | None declared | no | No SQL default | NOT NULL |

```sql
CREATE TABLE admission_detail(hadm_id INTEGER PRIMARY KEY NOT NULL REFERENCES admissions(hadm_id), discharge_summary_signed_at TEXT NOT NULL);
```

### lab_order — Lab order

- **Business definition:** Laboratory request; multiple measurements can fulfill it. subject_id identifies the patient even when hadm_id is NULL for a request outside an admission.
- **One row represents:** One authored laboratory request for one patient, optionally associated with an admission.
- **Additional documented relationships:** None additionally documented

| Variable name | Readable name | Definition | Measurement unit | Allowed values / code meanings | NULL meaning | Format / timezone |
| --- | --- | --- | --- | --- | --- | --- |
| order_id | Laboratory order ID | Identifier of this laboratory request in the laboratory-order identifier namespace. | Not applicable | Integer identifier; no positive-only or business min/max CHECK is declared. | NULL is not allowed by the declared schema. | Integer identifier |
| subject_id | Patient ID | Patient for this laboratory request, including requests not associated with a hospital admission. | Not applicable | Patient identifiers in patients.subject_id by documented convention; no SQL foreign key enforces that relationship. | NULL is not allowed by the declared schema. | Integer identifier |
| hadm_id | Hospital admission ID | Optional hospital admission associated with this laboratory request. | Not applicable | Existing admissions.hadm_id values. | No hospital admission is associated with this request, as in outpatient testing. | Integer identifier |
| specimen_received_at | Specimen receipt time | Time when specimens associated with this laboratory request were received by the laboratory. | Not applicable | UTC timestamp text using the documented format; no additional date range is declared. | No specimen receipt time is recorded. Whether receipt occurred is unknown. | RFC 3339 UTC text, YYYY-MM-DDTHH:MM:SSZ; timezone UTC |
| results_verified_at | Laboratory results verification time | Time when the recorded results for this laboratory order were verified. | Not applicable | UTC timestamp text using the documented format; no additional date range is declared. | No results-verification time is recorded. Whether verification occurred is unknown. | RFC 3339 UTC text, YYYY-MM-DDTHH:MM:SSZ; timezone UTC |

**Storage and declared constraints**

| Variable | SQL type | Required | PK position | Declared FK | Unique | Default | Column constraints |
| --- | --- | --- | --- | --- | --- | --- | --- |
| order_id | INTEGER | yes | 1 | None declared | yes | No SQL default | PRIMARY KEY NOT NULL |
| subject_id | INTEGER | yes |  | patients.subject_id | no | No SQL default | NOT NULL REFERENCES patients(subject_id) |
| hadm_id | INTEGER | no |  | admissions.hadm_id | no | No SQL default | REFERENCES admissions(hadm_id) |
| specimen_received_at | TEXT | no |  | None declared | no | No SQL default | No additional column constraint |
| results_verified_at | TEXT | no |  | None declared | no | No SQL default | No additional column constraint |

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
| stopped_at | Medication stopping time | Time when medication under this request was stopped. | Not applicable | UTC timestamp text using the documented format; no additional date range is declared. | No prescription stop time is recorded. Whether stopping occurred is unknown. | RFC 3339 UTC text, YYYY-MM-DDTHH:MM:SSZ; timezone UTC |

**Storage and declared constraints**

| Variable | SQL type | Required | PK position | Declared FK | Unique | Default | Column constraints |
| --- | --- | --- | --- | --- | --- | --- | --- |
| order_id | INTEGER | yes | 1 | None declared | yes | No SQL default | PRIMARY KEY NOT NULL |
| hadm_id | INTEGER | yes |  | admissions.hadm_id | no | No SQL default | NOT NULL REFERENCES admissions(hadm_id) |
| medication | TEXT | yes |  | None declared | no | No SQL default | NOT NULL |
| stopped_at | TEXT | no |  | None declared | no | No SQL default | No additional column constraint |

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
| preparation_completed_at | Procedure preparation completion time | Time when preparation for this procedure request was completed. | Not applicable | UTC timestamp text using the documented format; no additional date range is declared. | No preparation completion time is recorded. Whether completion occurred is unknown. | RFC 3339 UTC text, YYYY-MM-DDTHH:MM:SSZ; timezone UTC |

**Storage and declared constraints**

| Variable | SQL type | Required | PK position | Declared FK | Unique | Default | Column constraints |
| --- | --- | --- | --- | --- | --- | --- | --- |
| order_id | INTEGER | yes | 1 | None declared | yes | No SQL default | PRIMARY KEY NOT NULL |
| hadm_id | INTEGER | yes |  | admissions.hadm_id | no | No SQL default | NOT NULL REFERENCES admissions(hadm_id) |
| procedure_name | TEXT | yes |  | None declared | no | No SQL default | NOT NULL |
| preparation_completed_at | TEXT | no |  | None declared | no | No SQL default | No additional column constraint |

```sql
CREATE TABLE procedure_order(order_id INTEGER PRIMARY KEY NOT NULL, hadm_id INTEGER NOT NULL REFERENCES admissions(hadm_id), procedure_name TEXT NOT NULL, preparation_completed_at TEXT);
```

### order_history — Order history

- **Business definition:** Recorded actions on laboratory, medication or procedure requests, including repeated reviews.
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

- **Business definition:** Laboratory measurement results with specimen collection and result-availability times. charttime denotes specimen collection, not measurement execution.
- **One row represents:** One laboratory measurement result associated with a collected specimen and a laboratory request; collection and result availability have separate timestamps.
- **Additional documented relationships:** None additionally documented

| Variable name | Readable name | Definition | Measurement unit | Allowed values / code meanings | NULL meaning | Format / timezone |
| --- | --- | --- | --- | --- | --- | --- |
| labevent_id | Laboratory measurement ID | Identifier of this individual laboratory measurement occurrence. | Not applicable | Integer identifier; no positive-only or business min/max CHECK is declared. | NULL is not allowed by the declared schema. | Integer identifier |
| order_id | Referenced laboratory order ID | Laboratory order to which this measurement belongs. | Not applicable | Existing lab_order.order_id values. | NULL is not allowed by the declared schema. | Integer identifier |
| itemid | Laboratory measurement category ID | Authored laboratory concept: 1001 Creatinine (mg/dL), 1002 Sodium (mmol/L), 1003 Hemoglobin (g/dL). Not original MIMIC codes. | Not applicable | 1001 = Creatinine; 1002 = Sodium; 1003 = Hemoglobin. Authored concept codes. | NULL is not allowed by the declared schema. | Integer identifier |
| charttime | Specimen collection time | Time when the specimen used for this laboratory measurement was collected. This column does not store measurement execution time. | Not applicable | UTC timestamp text using the documented format; no additional date range is declared. | NULL is not allowed by the declared schema. | RFC 3339 UTC text, YYYY-MM-DDTHH:MM:SSZ; timezone UTC |
| storetime | Laboratory result availability time | Time when this laboratory result became available in the laboratory system. | Not applicable | UTC timestamp text using the documented format; no additional date range is declared. | NULL is not allowed by the declared schema. | RFC 3339 UTC text, YYYY-MM-DDTHH:MM:SSZ; timezone UTC |
| valuenum | Numeric measurement result | Numeric result recorded for this laboratory measurement. | As specified by valueuom for the corresponding test. | Numeric measurement value; no SQL min/max bound is declared. | No numeric measurement result is recorded. | Numeric value |
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

- **Definition references:** [https://mimic.mit.edu/docs/iv/modules/hosp/labevents.html](https://mimic.mit.edu/docs/iv/modules/hosp/labevents.html); [https://mimic.mit.edu/docs/iv/modules/hosp/labevents.html#charttime](https://mimic.mit.edu/docs/iv/modules/hosp/labevents.html#charttime).

```sql
CREATE TABLE labevents(labevent_id INTEGER PRIMARY KEY NOT NULL, order_id INTEGER NOT NULL REFERENCES lab_order(order_id), itemid INTEGER NOT NULL, charttime TEXT NOT NULL, storetime TEXT NOT NULL, valuenum REAL, valueuom TEXT, CHECK(charttime<=storetime));
```

### emar — Emar

- **Business definition:** Medication administration or omission records associated with pharmacy dispensing records.
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

- **Definition references:** [https://mimic.mit.edu/docs/iv/modules/hosp/emar.html](https://mimic.mit.edu/docs/iv/modules/hosp/emar.html).

```sql
CREATE TABLE emar(emar_id INTEGER PRIMARY KEY NOT NULL, pharmacy_id INTEGER NOT NULL REFERENCES pharmacy(pharmacy_id), charttime TEXT NOT NULL, event_txt TEXT NOT NULL CHECK(event_txt IN ('Administered','Not Given')), storetime TEXT NOT NULL, CHECK(charttime<=storetime));
```

### procedure_episode — Procedure episode

- **Business definition:** Hospital-level procedure execution episodes; the ICU stay_id hierarchy is excluded.
- **One row represents:** One hospital-level procedure execution episode, not an ICU stay.
- **Additional documented relationships:** None additionally documented

| Variable name | Readable name | Definition | Measurement unit | Allowed values / code meanings | NULL meaning | Format / timezone |
| --- | --- | --- | --- | --- | --- | --- |
| procedureevent_id | Procedure episode ID | Local synthetic identifier of one procedure execution episode; repeat episodes have separate identifiers. | Not applicable | Integer identifier; no positive-only or business min/max CHECK is declared. | NULL is not allowed by the declared schema. | Integer identifier |
| order_id | Referenced procedure order ID | Procedure order executed in this episode. | Not applicable | Existing procedure_order.order_id values. | NULL is not allowed by the declared schema. | Integer identifier |
| starttime | Procedure episode start time | Time when this procedure execution episode began. | Not applicable | UTC timestamp text using the documented format; no additional date range is declared. | NULL is not allowed by the declared schema. | RFC 3339 UTC text, YYYY-MM-DDTHH:MM:SSZ; timezone UTC |
| endtime | Procedure episode end time | Time when this procedure execution episode ended. | Not applicable | UTC timestamp text using the documented format; no additional date range is declared. | No procedure completion time is recorded. Whether completion occurred is unknown; an ongoing procedure cannot be inferred from NULL alone. | RFC 3339 UTC text, YYYY-MM-DDTHH:MM:SSZ; timezone UTC |
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
| dispensed_at | Dispensing record time | Time of the individual dispensing represented by this pharmacy record. This is not the first dispensing time for the prescription; each additional dispensing has its own pharmacy_id and row. | Not applicable | UTC timestamp text using the documented format; no additional date range is declared. | NULL is not allowed by the declared schema. | RFC 3339 UTC text, YYYY-MM-DDTHH:MM:SSZ; timezone UTC |

**Storage and declared constraints**

| Variable | SQL type | Required | PK position | Declared FK | Unique | Default | Column constraints |
| --- | --- | --- | --- | --- | --- | --- | --- |
| pharmacy_id | INTEGER | yes | 1 | None declared | yes | No SQL default | PRIMARY KEY NOT NULL |
| order_id | INTEGER | yes |  | medication_order.order_id | no | No SQL default | NOT NULL REFERENCES medication_order(order_id) |
| dispensed_at | TEXT | yes |  | None declared | no | No SQL default | NOT NULL |

```sql
CREATE TABLE pharmacy(pharmacy_id INTEGER PRIMARY KEY NOT NULL, order_id INTEGER NOT NULL REFERENCES medication_order(order_id), dispensed_at TEXT NOT NULL);
```

### Cross-table business conventions

- A patient can have multiple hospital admissions; hadm_id identifies an admission and subject_id identifies a patient.
- Supplementary profile rows use the patient identifier documented in patients; their logical relationship is not enforced by an SQL foreign key.
- A signed discharge summary uses the identifier of its hospital admission. Draft documents are not stored in admission_detail.
- Laboratory, medication and procedure requests use separate local identifier namespaces.
- An order-action history row has exactly one populated order-reference column; repeated reviews are separate records.
- A laboratory request can cover several specimens or measurements. For a recorded result the collection time precedes laboratory receipt, which precedes result availability; verification follows the available results.
- When a laboratory request has an associated admission, lab_order.subject_id must equal admissions.subject_id for that hadm_id. NULL hadm_id means no associated admission.
- A medication prescription can have multiple pharmacy dispensing records; each dispensing can have multiple administration or omission records.
- NULL is interpreted by the column-specific rule: an unrecorded clinical timestamp gives unknown occurrence status; a non-applicable order-reference column and an absent admission association have their separately defined structural meanings.
- Laboratory charttime represents specimen collection; storetime represents result availability. Medication and procedure storetime values represent system documentation times.
- Lab concept codes 1001, 1002 and 1003 mean Creatinine (mg/dL), Sodium (mmol/L) and Hemoglobin (g/dL), respectively.
