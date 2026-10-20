# HospitalFlow — data dictionary

## 1. Dictionary basic information

| Field | Value |
| --- | --- |
| dictionary_id | NL2EVENTLOG:hospitalflow |
| version | 2026-10-20 |
| name | HospitalFlow |
| description | English synthetic relational database for query-conditioned process-view and event-log extraction. |
| language | en |
| timezone | UTC |
| dbms | SQLite |
| namespace | hospitalflow |
| timestamp_columns | 19 |
| event_timestamp_columns | 17 |
| maintainer | NL2EVENTLOG project maintainers |
| registration_status | Project-maintained draft; not ISO-registered or certified |
| source_policy | Source definitions are retained and authored lifecycle additions are identified in source/design documents. |
| standards_profile | Project profile informed by ISO/IEC 11179-3 and 11179-4 public abstracts; no full clause-by-clause conformance assessment. |
| layout | 1 Dictionary basic information; 2 Table definitions; 3 Column definitions |

- A table has at most one PRIMARY KEY constraint. Multiple PK-marked columns are members of that single composite key; they are not independent primary keys. FK marks can overlap with those PK columns.
- The three-part layout is a project documentation choice, not a mandated ISO/IEC template.
- ISO/IEC 11179-4 addresses semantic definitions rather than prescribing their formatting. Only public standard scope descriptions were consulted.
- SQL keys and constraints are taken from the executable DB. SQLite TEXT has no declared maximum length unless an explicit constraint says otherwise. Examples are observed synthetic values, not additional allowed-value constraints.
- [ISO/IEC 11179-3:2023](https://www.iso.org/standard/78915.html): Registry identification, administration and definition concepts.
- [ISO/IEC 11179-4:2004](https://www.iso.org/standard/35346.html): Semantic formulation of data definitions.

## 2. Table definitions

| Metadata ID | Logical name | Physical name | Rows | PK | FK | Event encoding | Definition |
| --- | --- | --- | --- | --- | --- | --- | --- |
| hospitalflow.patients | Patients | patients | 12 | subject_id | None declared | No event encoding | Synthetic patient identity, inspired by MIMIC subject_id. |
| hospitalflow.admissions | Admissions | admissions | 15 | hadm_id | subject_id → patients.subject_id | Column encoding | Distinct hospital stays per patient with actual admission/discharge milestones. |
| hospitalflow.patient_profile | Patient Profile | patient_profile | 6 | subject_id | None declared | Column encoding | Optional additional information for the SAME patient identified by patients.subject_id, in the SAME identifier namespace. A matching subject_id denotes the same actual patient. No FK is declared; this identity relationship is explicitly documented. Authored split-storage extension. |
| hospitalflow.admission_detail | Admission Detail | admission_detail | 5 | hadm_id | hadm_id → admissions.hadm_id | Column encoding | Optional additional information for the SAME hospital stay identified by admissions.hadm_id. A matching hadm_id denotes the same actual admission. Only a subset of admissions has a signed summary. Authored split-storage extension. |
| hospitalflow.lab_order | Lab Order | lab_order | 15 | order_id | hadm_id → admissions.hadm_id | Column encoding | Distinct laboratory order; several measurements may belong to one order. |
| hospitalflow.medication_order | Medication Order | medication_order | 15 | order_id | hadm_id → admissions.hadm_id | Column encoding | Distinct medication order; repeated doses belong to one order. |
| hospitalflow.procedure_order | Procedure Order | procedure_order | 15 | order_id | hadm_id → admissions.hadm_id | Column encoding | Distinct procedure order; repeated execution episodes belong to one order. |
| hospitalflow.order_history | Order History | order_history | 102 | history_id | procedure_order_id → procedure_order.order_id; medication_order_id → medication_order.order_id; lab_order_id → lab_order.order_id | Row encoding | Repeated order actions, inspired by provider order transaction semantics; not a copy of poe. |
| hospitalflow.labevents | Labevents | labevents | 33 | labevent_id | order_id → lab_order.order_id | Mixed (row + column) | Measurement occurrences with separately charted and available-result times, inspired by MIMIC labevents. |
| hospitalflow.emar | Emar | emar | 45 | emar_id | order_id → medication_order.order_id | Row encoding | Medication administration or omission occurrences, inspired by MIMIC emar. |
| hospitalflow.procedureevents | Procedureevents | procedureevents | 15 | procedureevent_id | order_id → procedure_order.order_id | Mixed (row + column) | Procedure execution episodes with start/end times, inspired by MIMIC procedureevents. |

- Row encoding: an event occurrence is represented by a row.
- Column encoding: an object row stores one or more actual business milestone timestamps in dedicated columns.
- No event encoding: contextual, reference, planned or relationship/index data; this does not mean the related business object lacks an event log.
- **patients:** Type, identity or context only; does not store an event.
- **admissions:** Actual one-time milestones are separate timestamp columns on the business object. NULL means not occurred.
- **patient_profile:** Actual one-time milestones are separate timestamp columns on the business object. NULL means not occurred.
- **admission_detail:** Actual one-time milestones are separate timestamp columns on the business object. NULL means not occurred.
- **lab_order:** Actual one-time milestones are separate timestamp columns on the business object. NULL means not occurred.
- **medication_order:** Actual one-time milestones are separate timestamp columns on the business object. NULL means not occurred.
- **procedure_order:** Actual one-time milestones are separate timestamp columns on the business object. NULL means not occurred.
- **order_history:** Each occurrence is a separate row; action/event_txt determines activity. Technical emar.storetime is excluded.
- **labevents:** Each row preserves a repeated occurrence; multiple timestamp columns emit distinct activity types within that occurrence.
- **emar:** Each occurrence is a separate row; action/event_txt determines activity. Technical emar.storetime is excluded.
- **procedureevents:** Each row preserves a repeated occurrence; multiple timestamp columns emit distinct activity types within that occurrence.

## 3. Column definitions

### patients

| Element ID | Logical / physical name | Definition | Representation / SQL type | Length | Required | PK / FK | Default | Value domain / constraints | Unit | Examples |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| hospitalflow.patients.subject_id | Subject Id / subject_id | Synthetic patient identity; can occur in multiple hospital admissions. | Identifier / INTEGER | Not applicable | yes | 1 /  | No SQL default | SQL type and declared constraints: See executable table DDL | See column definition; no implicit unit | [1, 2, 3] |
| hospitalflow.patients.gender | Gender / gender | Synthetic demographic category, F or M. | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: See executable table DDL | See column definition; no implicit unit | ["F", "M"] |

- **Declared table constraints:** `CREATE TABLE patients(subject_id INTEGER PRIMARY KEY NOT NULL, gender TEXT NOT NULL CHECK(gender IN ('F','M')))`

### admissions

| Element ID | Logical / physical name | Definition | Representation / SQL type | Length | Required | PK / FK | Default | Value domain / constraints | Unit | Examples |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| hospitalflow.admissions.hadm_id | Hadm Id / hadm_id | Synthetic unique hospital admission identity. | Identifier / INTEGER | Not applicable | yes | 1 /  | No SQL default | SQL type and declared constraints: See executable table DDL | See column definition; no implicit unit | [1, 2, 3] |
| hospitalflow.admissions.subject_id | Subject Id / subject_id | Synthetic patient identity; can occur in multiple hospital admissions. | Identifier / INTEGER | Not applicable | yes |  / patients.subject_id | No SQL default | SQL type and declared constraints: See executable table DDL | See column definition; no implicit unit | [1, 2, 3] |
| hospitalflow.admissions.edregtime | Edregtime / edregtime | Actual emergency department registration time; NULL for admissions without ED registration. | Text / TEXT | Not bounded by declared SQLite type | no |  /  | No SQL default | SQL type and declared constraints: See executable table DDL | See column definition; no implicit unit | ["2026-01-09T08:00:00Z", "2026-01-26T00:00:00Z", "2026-02-11T16:00:00Z"] |
| hospitalflow.admissions.admittime | Admittime / admittime | Actual hospital admission time. | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: See executable table DDL | See column definition; no implicit unit | ["2026-01-09T09:00:00Z", "2026-01-17T17:00:00Z", "2026-01-26T01:00:00Z"] |
| hospitalflow.admissions.discharge_authorized_at | Discharge Authorized At / discharge_authorized_at | Authored actual discharge authorization time; NULL if not occurred. | Date/time text / TEXT | Not bounded by declared SQLite type | no |  /  | No SQL default | SQL type and declared constraints: See executable table DDL | UTC for actual event timestamps; source birth dates and planned dates retain their documented meaning | ["2026-01-12T16:00:00Z", "2026-01-21T00:00:00Z", "2026-01-29T08:00:00Z"] |
| hospitalflow.admissions.dischtime | Dischtime / dischtime | Actual hospital discharge time; NULL for an ongoing stay. | Text / TEXT | Not bounded by declared SQLite type | no |  /  | No SQL default | SQL type and declared constraints: See executable table DDL | See column definition; no implicit unit | ["2026-01-12T18:00:00Z", "2026-01-21T02:00:00Z", "2026-01-29T10:00:00Z"] |

- **Declared table constraints:** `CREATE TABLE admissions(hadm_id INTEGER PRIMARY KEY NOT NULL, subject_id INTEGER NOT NULL REFERENCES patients(subject_id), edregtime TEXT, admittime TEXT NOT NULL, discharge_authorized_at TEXT, dischtime TEXT, CHECK(edregtime IS NULL OR edregtime<=admittime), CHECK(dischtime IS NULL OR discharge_authorized_at<=dischtime))`

### patient_profile

| Element ID | Logical / physical name | Definition | Representation / SQL type | Length | Required | PK / FK | Default | Value domain / constraints | Unit | Examples |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| hospitalflow.patient_profile.subject_id | Subject Id / subject_id | Synthetic patient identity; can occur in multiple hospital admissions. | Identifier / INTEGER | Not applicable | yes | 1 /  | No SQL default | SQL type and declared constraints: See executable table DDL | See column definition; no implicit unit | [1, 3, 5] |
| hospitalflow.patient_profile.profile_verified_at | Profile Verified At / profile_verified_at | Actual verification of supplementary patient information; one-time milestone for the same patient, not a separate profile object. | Date/time text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: See executable table DDL | UTC for actual event timestamps; source birth dates and planned dates retain their documented meaning | ["2026-01-08T12:00:00Z", "2026-01-25T04:00:00Z", "2026-02-10T20:00:00Z"] |
| hospitalflow.patient_profile.preferred_language | Preferred Language / preferred_language | Synthetic preferred language. | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: See executable table DDL | See column definition; no implicit unit | ["English"] |

- **Declared table constraints:** `CREATE TABLE patient_profile(subject_id INTEGER PRIMARY KEY NOT NULL, profile_verified_at TEXT NOT NULL, preferred_language TEXT NOT NULL)`

### admission_detail

| Element ID | Logical / physical name | Definition | Representation / SQL type | Length | Required | PK / FK | Default | Value domain / constraints | Unit | Examples |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| hospitalflow.admission_detail.hadm_id | Hadm Id / hadm_id | Synthetic unique hospital admission identity. | Identifier / INTEGER | Not applicable | yes | 1 / admissions.hadm_id | No SQL default | SQL type and declared constraints: See executable table DDL | See column definition; no implicit unit | [1, 4, 7] |
| hospitalflow.admission_detail.discharge_summary_signed_at | Discharge Summary Signed At / discharge_summary_signed_at | Actual signing time of the summary for the same hospital admission; not a separate admission instance. | Date/time text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: See executable table DDL | UTC for actual event timestamps; source birth dates and planned dates retain their documented meaning | ["2026-01-12T17:00:00Z", "2026-02-06T17:00:00Z", "2026-03-03T17:00:00Z"] |
| hospitalflow.admission_detail.summary_status | Summary Status / summary_status | SIGNED; a recorded signed summary is present. | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: See executable table DDL | See column definition; no implicit unit | ["SIGNED"] |

- **Declared table constraints:** `CREATE TABLE admission_detail(hadm_id INTEGER PRIMARY KEY NOT NULL REFERENCES admissions(hadm_id), discharge_summary_signed_at TEXT NOT NULL, summary_status TEXT NOT NULL CHECK(summary_status='SIGNED'))`

### lab_order

| Element ID | Logical / physical name | Definition | Representation / SQL type | Length | Required | PK / FK | Default | Value domain / constraints | Unit | Examples |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| hospitalflow.lab_order.order_id | Order Id / order_id | Identity of a distinct order within its own business table. The three order tables use independent namespaces; equal integers do not mean the same request. | Identifier / INTEGER | Not applicable | yes | 1 /  | No SQL default | SQL type and declared constraints: See executable table DDL | See column definition; no implicit unit | [1, 2, 3] |
| hospitalflow.lab_order.hadm_id | Hadm Id / hadm_id | Synthetic unique hospital admission identity. | Identifier / INTEGER | Not applicable | yes |  / admissions.hadm_id | No SQL default | SQL type and declared constraints: See executable table DDL | See column definition; no implicit unit | [1, 2, 3] |
| hospitalflow.lab_order.specimen_received_at | Specimen Received At / specimen_received_at | Authored actual receipt of a specimen for this order. | Date/time text / TEXT | Not bounded by declared SQLite type | no |  /  | No SQL default | SQL type and declared constraints: See executable table DDL | UTC for actual event timestamps; source birth dates and planned dates retain their documented meaning | ["2026-01-09T13:00:00Z", "2026-01-17T21:00:00Z", "2026-01-26T05:00:00Z"] |
| hospitalflow.lab_order.results_verified_at | Results Verified At / results_verified_at | Authored actual verification of results after all recorded measurements become available. | Date/time text / TEXT | Not bounded by declared SQLite type | no |  /  | No SQL default | SQL type and declared constraints: See executable table DDL | UTC for actual event timestamps; source birth dates and planned dates retain their documented meaning | ["2026-01-09T22:00:00Z", "2026-01-18T06:00:00Z", "2026-01-26T14:00:00Z"] |

- **Declared table constraints:** `CREATE TABLE lab_order(order_id INTEGER PRIMARY KEY NOT NULL, hadm_id INTEGER NOT NULL REFERENCES admissions(hadm_id), specimen_received_at TEXT, results_verified_at TEXT)`

### medication_order

| Element ID | Logical / physical name | Definition | Representation / SQL type | Length | Required | PK / FK | Default | Value domain / constraints | Unit | Examples |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| hospitalflow.medication_order.order_id | Order Id / order_id | Identity of a distinct order within its own business table. The three order tables use independent namespaces; equal integers do not mean the same request. | Identifier / INTEGER | Not applicable | yes | 1 /  | No SQL default | SQL type and declared constraints: See executable table DDL | See column definition; no implicit unit | [1, 2, 3] |
| hospitalflow.medication_order.hadm_id | Hadm Id / hadm_id | Synthetic unique hospital admission identity. | Identifier / INTEGER | Not applicable | yes |  / admissions.hadm_id | No SQL default | SQL type and declared constraints: See executable table DDL | See column definition; no implicit unit | [1, 2, 3] |
| hospitalflow.medication_order.medication | Medication / medication | Fictional medication label; no treatment recommendation. | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: See executable table DDL | See column definition; no implicit unit | ["Synthetic Medicine 1", "Synthetic Medicine 2", "Synthetic Medicine 0"] |
| hospitalflow.medication_order.dispensed_at | Dispensed At / dispensed_at | Authored actual dispensing time. | Date/time text / TEXT | Not bounded by declared SQLite type | no |  /  | No SQL default | SQL type and declared constraints: See executable table DDL | UTC for actual event timestamps; source birth dates and planned dates retain their documented meaning | ["2026-01-09T13:00:00Z", "2026-01-17T21:00:00Z", "2026-01-26T05:00:00Z"] |
| hospitalflow.medication_order.stopped_at | Stopped At / stopped_at | Authored actual stop time; NULL if not stopped. | Date/time text / TEXT | Not bounded by declared SQLite type | no |  /  | No SQL default | SQL type and declared constraints: See executable table DDL | UTC for actual event timestamps; source birth dates and planned dates retain their documented meaning | ["2026-01-11T00:00:00Z", "2026-01-19T08:00:00Z", "2026-01-27T16:00:00Z"] |

- **Declared table constraints:** `CREATE TABLE medication_order(order_id INTEGER PRIMARY KEY NOT NULL, hadm_id INTEGER NOT NULL REFERENCES admissions(hadm_id), medication TEXT NOT NULL, dispensed_at TEXT, stopped_at TEXT)`

### procedure_order

| Element ID | Logical / physical name | Definition | Representation / SQL type | Length | Required | PK / FK | Default | Value domain / constraints | Unit | Examples |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| hospitalflow.procedure_order.order_id | Order Id / order_id | Identity of a distinct order within its own business table. The three order tables use independent namespaces; equal integers do not mean the same request. | Identifier / INTEGER | Not applicable | yes | 1 /  | No SQL default | SQL type and declared constraints: See executable table DDL | See column definition; no implicit unit | [1, 2, 3] |
| hospitalflow.procedure_order.hadm_id | Hadm Id / hadm_id | Synthetic unique hospital admission identity. | Identifier / INTEGER | Not applicable | yes |  / admissions.hadm_id | No SQL default | SQL type and declared constraints: See executable table DDL | See column definition; no implicit unit | [1, 2, 3] |
| hospitalflow.procedure_order.procedure_name | Procedure Name / procedure_name | Fictional procedure label. | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: See executable table DDL | See column definition; no implicit unit | ["Synthetic Procedure 1", "Synthetic Procedure 2", "Synthetic Procedure 0"] |
| hospitalflow.procedure_order.preparation_completed_at | Preparation Completed At / preparation_completed_at | Authored actual completion of preparation for this procedure order. | Date/time text / TEXT | Not bounded by declared SQLite type | no |  /  | No SQL default | SQL type and declared constraints: See executable table DDL | UTC for actual event timestamps; source birth dates and planned dates retain their documented meaning | ["2026-01-09T13:00:00Z", "2026-01-17T21:00:00Z", "2026-01-26T05:00:00Z"] |

- **Declared table constraints:** `CREATE TABLE procedure_order(order_id INTEGER PRIMARY KEY NOT NULL, hadm_id INTEGER NOT NULL REFERENCES admissions(hadm_id), procedure_name TEXT NOT NULL, preparation_completed_at TEXT)`

### order_history

| Element ID | Logical / physical name | Definition | Representation / SQL type | Length | Required | PK / FK | Default | Value domain / constraints | Unit | Examples |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| hospitalflow.order_history.history_id | History Id / history_id | Unique occurrence identity for a repeated order action. | Identifier / INTEGER | Not applicable | yes | 1 /  | No SQL default | SQL type and declared constraints: See executable table DDL | See column definition; no implicit unit | [1, 2, 3] |
| hospitalflow.order_history.lab_order_id | Lab Order Id / lab_order_id | FK to a distinct laboratory order; exactly one order FK is non-null per history row. | Identifier / INTEGER | Not applicable | no |  / lab_order.order_id | No SQL default | SQL type and declared constraints: See executable table DDL | See column definition; no implicit unit | [1, 2, 3] |
| hospitalflow.order_history.medication_order_id | Medication Order Id / medication_order_id | FK to a distinct medication order; exactly one order FK is non-null per history row. | Identifier / INTEGER | Not applicable | no |  / medication_order.order_id | No SQL default | SQL type and declared constraints: See executable table DDL | See column definition; no implicit unit | [1, 2, 3] |
| hospitalflow.order_history.procedure_order_id | Procedure Order Id / procedure_order_id | FK to a distinct procedure order; exactly one order FK is non-null per history row. | Identifier / INTEGER | Not applicable | no |  / procedure_order.order_id | No SQL default | SQL type and declared constraints: See executable table DDL | See column definition; no implicit unit | [1, 2, 3] |
| hospitalflow.order_history.action | Action / action | ENTERED, REVIEWED or CANCELLED order action; repeated REVIEWED is permitted. | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: See executable table DDL | See column definition; no implicit unit | ["ENTERED", "REVIEWED", "CANCELLED"] |
| hospitalflow.order_history.occurred_at | Occurred At / occurred_at | Actual UTC time of the order action. | Date/time text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: See executable table DDL | UTC for actual event timestamps; source birth dates and planned dates retain their documented meaning | ["2026-01-09T10:00:00Z", "2026-01-09T11:00:00Z", "2026-01-17T18:00:00Z"] |

- **Declared table constraints:** `CREATE TABLE order_history(history_id INTEGER PRIMARY KEY NOT NULL, lab_order_id INTEGER REFERENCES lab_order(order_id), medication_order_id INTEGER REFERENCES medication_order(order_id), procedure_order_id INTEGER REFERENCES procedure_order(order_id), action TEXT NOT NULL CHECK(action IN ('ENTERED','REVIEWED','CANCELLED')), occurred_at TEXT NOT NULL, CHECK((lab_order_id IS NOT NULL)+(medication_order_id IS NOT NULL)+(procedure_order_id IS NOT NULL)=1))`

### labevents

| Element ID | Logical / physical name | Definition | Representation / SQL type | Length | Required | PK / FK | Default | Value domain / constraints | Unit | Examples |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| hospitalflow.labevents.labevent_id | Labevent Id / labevent_id | Unique measurement occurrence identity; repeated item measurements remain distinct. | Identifier / INTEGER | Not applicable | yes | 1 /  | No SQL default | SQL type and declared constraints: See executable table DDL | See column definition; no implicit unit | [1, 2, 3] |
| hospitalflow.labevents.order_id | Order Id / order_id | Identity of a distinct order within its own business table. The three order tables use independent namespaces; equal integers do not mean the same request. | Identifier / INTEGER | Not applicable | yes |  / lab_order.order_id | No SQL default | SQL type and declared constraints: See executable table DDL | See column definition; no implicit unit | [1, 2, 3] |
| hospitalflow.labevents.itemid | Itemid / itemid | Synthetic laboratory concept ID; no original MIMIC item code is claimed. | Number / INTEGER | Not applicable | yes |  /  | No SQL default | SQL type and declared constraints: See executable table DDL | See column definition; no implicit unit | [1, 2] |
| hospitalflow.labevents.charttime | Charttime / charttime | Actual charted measurement time in labevents; medication administration/omission time in emar. Not lab result-availability time. | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: See executable table DDL | See column definition; no implicit unit | ["2026-01-09T14:00:00Z", "2026-01-09T16:00:00Z", "2026-01-09T18:00:00Z"] |
| hospitalflow.labevents.storetime | Storetime / storetime | For labevents, time result becomes available; for emar/procedureevents, system record time excluded as a separate business event. | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: See executable table DDL | See column definition; no implicit unit | ["2026-01-09T15:00:00Z", "2026-01-09T17:00:00Z", "2026-01-09T19:00:00Z"] |
| hospitalflow.labevents.valuenum | Valuenum / valuenum | Synthetic measurement numeric value. | Number / REAL | Not applicable | no |  /  | No SQL default | SQL type and declared constraints: See executable table DDL | See column definition; no implicit unit | [11.0, 12.0, 13.0] |
| hospitalflow.labevents.valueuom | Valueuom / valueuom | Measurement unit; all current synthetic measurements use arbitrary units. | Text / TEXT | Not bounded by declared SQLite type | no |  /  | No SQL default | SQL type and declared constraints: See executable table DDL | See column definition; no implicit unit | ["arbitrary units"] |

- **Declared table constraints:** `CREATE TABLE labevents(labevent_id INTEGER PRIMARY KEY NOT NULL, order_id INTEGER NOT NULL REFERENCES lab_order(order_id), itemid INTEGER NOT NULL, charttime TEXT NOT NULL, storetime TEXT NOT NULL, valuenum REAL, valueuom TEXT, CHECK(charttime<=storetime))`

### emar

| Element ID | Logical / physical name | Definition | Representation / SQL type | Length | Required | PK / FK | Default | Value domain / constraints | Unit | Examples |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| hospitalflow.emar.emar_id | Emar Id / emar_id | Unique synthetic dose occurrence ID; simplified from the MIMIC identity structure. | Identifier / INTEGER | Not applicable | yes | 1 /  | No SQL default | SQL type and declared constraints: See executable table DDL | See column definition; no implicit unit | [1, 2, 3] |
| hospitalflow.emar.order_id | Order Id / order_id | Identity of a distinct order within its own business table. The three order tables use independent namespaces; equal integers do not mean the same request. | Identifier / INTEGER | Not applicable | yes |  / medication_order.order_id | No SQL default | SQL type and declared constraints: See executable table DDL | See column definition; no implicit unit | [1, 2, 3] |
| hospitalflow.emar.charttime | Charttime / charttime | Actual charted measurement time in labevents; medication administration/omission time in emar. Not lab result-availability time. | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: See executable table DDL | See column definition; no implicit unit | ["2026-01-09T16:00:00Z", "2026-01-10T00:00:00Z", "2026-01-10T08:00:00Z"] |
| hospitalflow.emar.event_txt | Event Txt / event_txt | Administered or Not Given; selects the activity of this dose occurrence. | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: See executable table DDL | See column definition; no implicit unit | ["Administered", "Not Given"] |
| hospitalflow.emar.storetime | Storetime / storetime | For labevents, time result becomes available; for emar/procedureevents, system record time excluded as a separate business event. | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: See executable table DDL | See column definition; no implicit unit | ["2026-01-09T16:06:00Z", "2026-01-10T00:06:00Z", "2026-01-10T08:06:00Z"] |

- **Declared table constraints:** `CREATE TABLE emar(emar_id INTEGER PRIMARY KEY NOT NULL, order_id INTEGER NOT NULL REFERENCES medication_order(order_id), charttime TEXT NOT NULL, event_txt TEXT NOT NULL CHECK(event_txt IN ('Administered','Not Given')), storetime TEXT NOT NULL, CHECK(charttime<=storetime))`

### procedureevents

| Element ID | Logical / physical name | Definition | Representation / SQL type | Length | Required | PK / FK | Default | Value domain / constraints | Unit | Examples |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| hospitalflow.procedureevents.procedureevent_id | Procedureevent Id / procedureevent_id | Authored unique procedure episode identity; not an original MIMIC column. | Identifier / INTEGER | Not applicable | yes | 1 /  | No SQL default | SQL type and declared constraints: See executable table DDL | See column definition; no implicit unit | [1, 2, 3] |
| hospitalflow.procedureevents.order_id | Order Id / order_id | Identity of a distinct order within its own business table. The three order tables use independent namespaces; equal integers do not mean the same request. | Identifier / INTEGER | Not applicable | yes |  / procedure_order.order_id | No SQL default | SQL type and declared constraints: See executable table DDL | See column definition; no implicit unit | [1, 2, 3] |
| hospitalflow.procedureevents.starttime | Starttime / starttime | Actual procedure episode start. | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: See executable table DDL | See column definition; no implicit unit | ["2026-01-09T16:00:00Z", "2026-01-18T00:00:00Z", "2026-01-26T08:00:00Z"] |
| hospitalflow.procedureevents.endtime | Endtime / endtime | Actual procedure episode completion; NULL if ongoing. | Text / TEXT | Not bounded by declared SQLite type | no |  /  | No SQL default | SQL type and declared constraints: See executable table DDL | See column definition; no implicit unit | ["2026-01-09T18:00:00Z", "2026-01-18T02:00:00Z", "2026-01-26T10:00:00Z"] |
| hospitalflow.procedureevents.storetime | Storetime / storetime | For labevents, time result becomes available; for emar/procedureevents, system record time excluded as a separate business event. | Text / TEXT | Not bounded by declared SQLite type | yes |  /  | No SQL default | SQL type and declared constraints: See executable table DDL | See column definition; no implicit unit | ["2026-01-09T19:00:00Z", "2026-01-18T03:00:00Z", "2026-01-26T11:00:00Z"] |

- **Declared table constraints:** `CREATE TABLE procedureevents(procedureevent_id INTEGER PRIMARY KEY NOT NULL, order_id INTEGER NOT NULL REFERENCES procedure_order(order_id), starttime TEXT NOT NULL, endtime TEXT, storetime TEXT NOT NULL, CHECK(endtime IS NULL OR starttime<=endtime))`

### Business meanings and extraction rules

- Physical Objects are table/PK representations, not tables named object or object_type.
- patients and patient_profile use the same patient identifier namespace; optional profile rows represent the SAME patient, with no declared FK.
- admissions and admission_detail use the same admission namespace; the shared-PK FK corroborates the documented SAME-stay identity.
- Laboratory, medication and procedure orders have distinct identities and namespaces. Overlapping local order_id integers do not establish identity.
- order_history.history_id identifies a history occurrence, not the referenced order. Each row has exactly one declared order FK.
- All timestamps and records are synthetic UTC; MIMIC-inspired fields and authored split-storage additions are distinguished.
- labevents.charttime is charted measurement time; storetime is result availability. emar/procedureevents storetime is technical documentation time.
- Physical source table/PK and own-versus-FK attribution remain available for every event binding.
- Missing events do not prove care did not occur; full lifecycle means the recorded declared scope.
- Model input comprises DB/schema, dictionary and input/model_questions.jsonl. private/identity_gold.json and private event history are evaluation answers, not model inputs.

### Objects, types and activity scopes

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
