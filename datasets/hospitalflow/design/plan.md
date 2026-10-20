# HospitalFlow construction plan

- **Purpose:** test whether objects stored in different business tables can be selected under one common object type while preserving individual case identity.
- **Source:** public MIMIC-IV documentation; all records are synthetic. This is a source-inspired benchmark, not a MIMIC subset or a faithful MIMIC schema export.
- **Conceptual design:** Patient → Hospital Admission → Clinical Order. Laboratory, medication and procedure orders are three subtypes of Clinical Order. Each patient can have several admissions; each admission can contain all three order subtypes.
- **Logical design:** object_type defines three semantic types. object records globally unique object IDs and their types. patients/admissions/clinical_order reference that registry. lab_order, medication_order and procedure_order reference clinical_order with a checked subtype. No generic event table is exposed as an extraction shortcut.
- **Physical design:** SQLite PK/FK/UNIQUE/CHECK constraints and subtype/type triggers. Local order IDs deliberately overlap between subtype tables; global object IDs do not. Records and events are generated deterministically.
- **Row storage:** order_history stores repeated order actions; emar stores repeated administrations or omissions.
- **Column storage:** admissions and order subtype tables store actual one-time milestones. NULL means not occurred.
- **Mixed storage:** each labevents row is a distinct measurement occurrence with charttime and storetime producing different activities. procedureevents rows preserve repeat procedure occurrences, each with starttime/endtime milestones. Technical procedure storetime is excluded from event time selection.
- **Case views:** Patient, Hospital Admission, Clinical Order and three subtype-restricted Clinical Order populations. The latter are scopes, not three extra object types. Shared type does not mean one shared case.
- **Question generation:** freeze Q1/Q3 seeds first; the assistant LLM receives each seed plus a meaning-preservation instruction and writes Q2/Q4. Save prompts, outputs, pairing and semantic review. No claim of an external model/API call. Rebuilds reuse frozen outputs.
- **Validation:** independent generation-time event/object history versus SQL/CSV; every registered object has a full-lifecycle view; paired questions share ES/Gold; reject wrong types/subtypes and orphan links; preserve repeated measurements/doses/procedures; avoid join fan-out and cross-admission leakage; test pending, cancelled and empty cases.
- **Deliverables:** English DB, schema, source mapping, three-part dictionary profile, PNG/draw.io, timestamp inventory, object/type examples and verification SQL, questions, ES/SQL/CSV Gold and validation report.
