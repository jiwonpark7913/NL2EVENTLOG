# HospitalFlow — MIMIC-IV-inspired synthetic hospital database

The database uses MIMIC-IV-inspired schema and timestamp names but wholly synthetic patient, admission and transfer records.
No real MIMIC-IV individual-level patient data are included.

## Current benchmark summary

| Tables | Patients | Admissions | Transfer rows | Object types | Distinct events | Answerable questions |
|---:|---:|---:|---:|---:|---:|---:|
| 12 | 12 | 15 | 38 | 11 | 627 | 42 |

## Design changes

- Patient demographics and anchor metadata now reside in patients; patient_profile and preferred_language were removed.
- Original MIMIC admission timestamp names used: admittime, dischtime, deathtime, edregtime, edouttime.
- transfers contains eventtype, careunit, intime and outtime and is linked to patient and hospital admission.
- Only actual transfer eventtype rows create Care Unit Transferred events; admission/discharge intervals are not counted twice.
- Gold SQL and event logs were regenerated, including a new Care Unit Transferred activity.

## Inspection

- [Database and first 10 rows per table](review/database/README.md)
- [Gold DFGs](review/gold_dfg/README.md)
- [Gold source evidence inventory](review/gold_dfg/event_graph.md)
- [Editable Draw.io ERD](docs/schema.drawio)
- [MIMIC-IV hospital schema documentation](https://mimic.mit.edu/docs/iv/modules/hosp/)

All files under private and review are author-only, never model inputs.
