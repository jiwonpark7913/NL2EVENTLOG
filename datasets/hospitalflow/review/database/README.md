# hospitalflow — Database Inspection

Synthetic SQLite records; **review-only, never provide to evaluation models**. Click a table name to inspect its actual first 10 rows.

### Relational schema and timestamp evidence

![Annotated ERD](schema.svg)

**Legend:** Yellow = Gold event timestamp; blue = other timestamp (such as recording time); solid edges = declared SQL foreign keys; orange dashed edge = documented shared identity, not SQL FK.

**Why are `patients` and `patient_profile` connected by a dashed line?** Both use `subject_id` as the primary key and the authored Data Dictionary states that their identifiers refer to the same patient. Only 6 of 12 patients have profile rows. There is deliberately **no SQL foreign-key constraint** between these tables. The previous SVG renderer displayed SQL FKs only, despite the existing dashed edge in the Draw.io source.

### Gold Evidence Graph — author annotation, not a model prediction

![Gold Evidence Graph — source activity inventory](gold_evidence_graph.svg)

The Gold graph shows **all 12 physical table-to-object-type memberships** and **every Gold source activity type by table** (including repeated activity names across sources). It is a source-binding projection rather than the complete record-level attribution graph. See the [full Gold Evidence Graph inventory](../gold_dfg/event_graph.md) and the [question-level Gold DFG review](../gold_dfg/README.md).

### MIMIC-IV vs HospitalFlow (provenance)

**MIMIC-IV** is a real de-identified critical-care and hospital EHR dataset (Medical Information Mart for Intensive Care). **HospitalFlow is not a reduced extract of real MIMIC patient rows:** it uses synthetic records and a schema inspired by selected MIMIC-IV `hosp` tables, plus authored split-object and lifecycle extensions.

| MIMIC-IV `hosp` original table | Representative recorded time columns in MIMIC-IV | HospitalFlow relation |
|---|---|---|
| `patients` | `dod` (date of death); `anchor_year` is not an event timestamp | `patients` keeps IDs/demographic attribute; `patient_profile` is **authored**, not a native MIMIC table |
| `admissions` | `admittime`, `dischtime`, `deathtime`, `edregtime`, `edouttime` | `admissions` inspired by original; `discharge_authorized_at` is authored |
| `transfers` | `intime`, `outtime` | Not retained |
| `labevents` | `charttime`, `storetime` | `labevents` retains these timestamp names, but rows are synthetic |
| `emar` | `charttime`, `scheduletime`, `storetime` | `emar` retains `charttime`, `storetime`; synthetic |
| `poe` | `ordertime` | Not retained directly; authored `order_history` and three order tables represent simplified order lifecycles |
| `prescriptions` | `starttime`, `stoptime` | Replaced by authored `medication_order` representation |
| `pharmacy` | Linked medication workflow (see official `hosp` schema) | `pharmacy.dispensed_at` is authored |
| `procedures_icd` | `chartdate` (date-grained procedure coding) | Authored `procedure_order` and `procedure_episode` are **not** native MIMIC tables |

Official references: [MIMIC-IV dataset](https://physionet.org/content/mimiciv/3.1/), [hospital module](https://mimic.mit.edu/docs/iv/modules/hosp/), [admissions](https://mimic.mit.edu/docs/iv/modules/hosp/admissions.html), [labevents](https://mimic.mit.edu/docs/iv/modules/hosp/labevents.html), [eMAR](https://mimic.mit.edu/docs/iv/modules/hosp/emar.html), [orders](https://mimic.mit.edu/docs/iv/modules/hosp/poe.html). The timestamps listed above belong to the **real MIMIC schema**, not necessarily HospitalFlow.

### Actual SQLite tables and first 10 records

| Table | Rows | Columns | Open preview |
|---|---:|---:|---|
| admission_detail | 5 | 2 | [First 10 rows](tables/admission_detail.md) |
| admissions | 15 | 6 | [First 10 rows](tables/admissions.md) |
| emar | 67 | 5 | [First 10 rows](tables/emar.md) |
| lab_order | 34 | 5 | [First 10 rows](tables/lab_order.md) |
| labevents | 62 | 7 | [First 10 rows](tables/labevents.md) |
| medication_order | 29 | 4 | [First 10 rows](tables/medication_order.md) |
| order_history | 203 | 6 | [First 10 rows](tables/order_history.md) |
| patient_profile | 6 | 3 | [First 10 rows](tables/patient_profile.md) |
| patients | 12 | 2 | [First 10 rows](tables/patients.md) |
| pharmacy | 34 | 3 | [First 10 rows](tables/pharmacy.md) |
| procedure_episode | 23 | 5 | [First 10 rows](tables/procedure_episode.md) |
| procedure_order | 17 | 4 | [First 10 rows](tables/procedure_order.md) |

The table links are the dependable GitHub navigation path; SVG click-through may vary by GitHub's rendering/security restrictions.
Solid edges correspond to declared SQL foreign keys. The dashed patient-profile relation is a documented shared identifier, not a declared SQL FK.
