# HospitalFlow — active benchmark requirements

- Keep a realistic but synthetic relational schema with documented PK/FK relations and MIMIC-IV-inspired column conventions.
- Expose only `input/database.sqlite` and `input/data_dictionary.json` as the default database evidence; questions are supplied separately.
- Preserve the distinction between same-identity object types and objects linked by relations.
- Require executable and independently validated SQL and Gold CSV for every answerable question.
- Represent `patients` as one physical master table, and retain distinct `admissions` and `transfers` records.
- Do not infer events from descriptive or current-state attributes without temporal evidence.
- Keep all Gold SQL, DFGs, object identities and inspection pages outside model-visible evidence.

[Current schema](../docs/schema_overview.md) · [Current dictionary](../docs/data_dictionary.md) · [Validation implementation](../validate.py)
