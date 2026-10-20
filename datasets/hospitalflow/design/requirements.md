# HospitalFlow authored requirements

- Evaluate same business type AND compatible instance identity across Physical Objects. This is not common-supertype classification.
- Use ordinary hospital tables; remove object/object_type registries and the clinical_order parent.
- Same-patient positive: patients / patient_profile, identical documented subject_id namespace, optional 6/12 coverage, intentionally no FK. Profile verification supplies an event from the second physical representation.
- Same-admission positive: admissions / admission_detail, identical documented hadm_id namespace, optional 5/15 coverage, shared-PK FK. Summary signing supplies a distinct event.
- Negative: different order kinds use independent local ID namespaces; history, measurement, administration and procedure episode PKs identify their own occurrences. FKs preserve attribution, not identity equivalence.
- Gold grouping and full-set overlap statistics belong in private/identity_gold.json; no object/type membership answer table is exposed in the DB. The dictionary remains legitimate semantic evidence.
- Eleven Physical Objects yield nine expected identity-compatible groups. These are author-assigned answers, not measured predictions from Step 2.
- Preserve existing 361 event occurrence identities and add only six profile-verification and five summary-signing events; do not collapse events during grouping.
- Retain row, column and mixed event storage, deterministic generation and own-versus-FK provenance.
- Freeze revised Q1/Q3 seeds then create matching assistant-LLM Q2/Q4 paraphrases, saving prompts and outputs.
- Validate all SQL/CSV against independent histories, split-source cases, optional extensions, no-FK identity, duplicate avoidance, repeat occurrences, own/FK paths, exact pairs and source provenance.
- UNRESOLVED and conflict cases are isolated private test specifications; not extra main-schema tables or an executed semantic judge.
- Public MIMIC documentation provides source concepts only. New split tables, exact keys/constraints and simulation are authored. No real patient records are used.
