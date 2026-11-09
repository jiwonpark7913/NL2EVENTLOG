# HospitalFlow — current realism and validation statement

HospitalFlow contains **synthetic** hospital data using selected MIMIC-IV hospital schema conventions, not a statistically calibrated or de-identified subsample of real MIMIC-IV encounters.

- Physical tables: 12; Gold object types: 11.
- Recorded patients: 12; admissions: 15; transfer-interval records: 38.
- Distinct Gold events: 627; questions: 44; answerable: 42.
- All Gold SQL files were checked against Gold CSVs.
- Only one object-identity merge is warranted: `admissions` + `admission_detail` by shared `hadm_id`.
- `transfers` is a separate occurrence object; its events can be attributed to an admission/patient without merging their identities.

These counts describe benchmark construction, not empirical healthcare distributions. See [current schema](schema_overview.md), [timestamp inventory](timestamp_columns.md), [Gold OT definitions](object_type_verification.md) and [official MIMIC-IV reference](https://mimic.mit.edu/docs/iv/modules/hosp/).
