# HospitalFlow realism and evaluation-validity revision

- Scope: fix weak evaluation controls while keeping the model compact. These are synthetic illustrative pathways, not a statistically calibrated hospital population or an exact MIMIC schema.
- The previous published construction used 11 tables, 9 groups, 372 events and 40 questions. The revised construction has 12 tables, 10 groups, 628 events and 44 questions (42 Gold CSVs).
- 19 physical datetime columns remain; 17 supply business event times. Dispensing time moved to pharmacy rather than being duplicated on prescriptions. More timestamps are not needed to fix constant intervals.
- Dictionary, schema, questions, ES, SQL, canonical histories, Gold CSVs, identity answers and ERD are regenerated together. Existing query IDs keep their meanings, but record IDs and Gold content intentionally change. Do not combine old CSVs with the new DB.

| Concern | Implemented change |
| --- | --- |
| Identifier aliasing | 1xxxxxxx patient IDs, 2xxxxxxx admission IDs, shuffled 3xxxxxxx order IDs; three shared values across independent order namespaces. |
| Uniform fan-out | Zero-to-many request, dispensing, dose, measurement and episode counts. Counts have explicit long-tail coverage; they are not fitted estimates. |
| Fixed times | Variable minute-scale intervals, bounded lognormal stays and nonconstant readmission gaps. |
| Accidental ties | Second offsets only for incidental sample collisions, audited in private/timestamp_collision_audit.json. No simultaneous events are intended in this clean core. |
| MIMIC poe mismatch | Three order tables intentionally retained and documented as authored. |
| ICU procedureevents mismatch | Renamed procedure_episode; no ICU hierarchy or stay_id claim. |
| Prescription/dispensing conflation | medication_order → pharmacy → emar, each with its own identity. |
| Unassociated admission | Four lab requests have subject_id and NULL hadm_id. Their 27 events are in patient/order views and excluded from admission views. |
| Meaningless labels | Creatinine, Sodium, Hemoglobin with mg/dL, mmol/L, g/dL; generic medication and procedure names. |
| Scope kept small | Transfers, full ICU/ED tables and corrupted/noisy variant deferred. UTC 2026 dates and clean constraints retained. |

## Observed cardinalities

| Relation | Minimum | Maximum | Number of distinct counts |
| --- | --- | --- | --- |
| lab_order_per_admission | 0 | 7 | 7 |
| medication_order_per_admission | 0 | 7 | 6 |
| procedure_order_per_admission | 0 | 4 | 5 |
| dispensings_per_prescription | 0 | 2 | 3 |
| doses_per_dispensing | 0 | 5 | 5 |
| doses_per_prescription | 0 | 10 | 8 |

## Observed time intervals

| Interval | Records | Minimum minutes | Maximum minutes | Distinct intervals |
| --- | --- | --- | --- | --- |
| stay_minutes | 13 | 2160.0 | 10533.0 | 13 |
| ed_to_admission_minutes | 8 | 22.0 | 216.0 | 8 |
| lab_turnaround_minutes | 62 | 84.0 | 309.0 | 55 |
| authorization_to_discharge_minutes | 13 | 47.0 | 220.0 | 13 |
| readmission_gap_minutes | 4 | 8762.0 | 11476.0 | 4 |

## Negative SQL controls

| Deliberately wrong query | Correct rows | Wrong rows | Detected |
| --- | --- | --- | --- |
| wrong_lab_order_order_id_to_hadm_id | 30 | 0 | True |
| wrong_medication_order_order_id_to_hadm_id | 29 | 0 | True |
| wrong_procedure_order_order_id_to_hadm_id | 17 | 0 | True |
| unrelated_lab_fanout | 67 | 83 | True |

- Passing these probes demonstrates detection of these specified errors, not every possible wrong SQL statement. Integrity, case membership and independent-history comparisons are checked separately.
- The independent generation history is emitted while simulating events; ES SQL reconstructs rows from persisted business tables. Simulation collision resolution updates both representations before comparison and has its own audit.
- [Machine-readable results](realism_validation.json) · [Business dictionary](data_dictionary.md) · [Questions](questions.md) · [Construction plan](../design/plan.md)

- Subsequent semantic corrections: [clinical-time and dictionary review](semantic_review.md). Specimen collection now precedes receipt and summaries are signed after discharge.
