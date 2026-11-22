# HospitalFlow — current Data Dictionary quality check

The current baseline Data Dictionary is `../input/data_dictionary.json`. The [rendered dictionary](data_dictionary.md) is generated from that file.

Checks required for the active benchmark:
- Every SQLite table and column has a matching Data Dictionary entry.
- MIMIC-inspired column names are distinguished from authored laboratory, pharmacy, order, and procedure fields.
- `patient_profile`, `preferred_language`, and `discharge_authorized_at` are absent from the current database schema.
- `transfers.eventtype` and its `intime` activity interpretation are described without creating duplicate admission/discharge events.

The pre-migration review dated 2026-11-03 is historical and must not be cited as validation of the present database. See [schema overview](schema_overview.md) and [semantic review](semantic_review.md).
