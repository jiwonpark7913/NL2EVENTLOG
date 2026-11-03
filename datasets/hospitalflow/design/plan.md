# HospitalFlow construction plan

- Model ordinary hospital records, with no generic object or object_type registry in the input DB.
- Preserve the two documented same-identity split-storage cases: patients/patient_profile and admissions/admission_detail. Twelve physical representations yield ten identity-compatible groups; the two MERGE pairs are authored Gold, not classifier predictions.
- Keep separate laboratory, medication and procedure requests as an intentional departure from MIMIC poe. Share a few independent local ID values across these tables, but never equate an order ID with an admission ID.
- Use 15 admissions for 11 patients, plus one patient with no recorded events. Add four laboratory requests with known patients and no admission. Vary admission-level order counts from zero to seven, with a longer tail deliberately covered in this small sample.
- Separate a medication prescription (medication_order), dispensing (pharmacy) and administration/omission (emar). A prescription may have zero or multiple dispensings and each dispensing zero or multiple dose records.
- Name hospital-level execution records procedure_episode. Do not represent them as the MIMIC ICU procedureevents table or claim ICU coverage.
- Generate minute-scale timestamps from illustrative distributions using seed 20261103: bounded lognormal stays and variable admission, turnaround, documentation and readmission intervals. Resolve incidental simulation collisions with explicitly audited second offsets before Gold extraction. No event-order inference is encoded in Gold sorting.
- Retain clean FK/time consistency, multiple incomplete stays/prescriptions/episodes, pending laboratory orders, cancellation, repetition and empty cases. A deliberately corrupted/noisy variant, transfers and ICU stay hierarchy are deferred.
- Identify Row activity identities by an actual carrier (order_history.action, emar.event_txt). Multiple timestamp phases on repeated lab/procedure rows remain Column at the declared generic activity granularity. Put classification answers only in author documentation, never the business dictionary.
- Freeze Q1/Q3 seeds and preserve existing pairs. Add a pharmacy explicit pair and full-lifecycle pair; save assistant LLM paraphrases and provenance separately. Each pair shares exact ES and Gold scope.
- Compare every persisted SQL/CSV with a separately emitted generation-time history; verify own/FK links and outpatient exclusion from admission views. Probe intentionally wrong ID joins and unrelated fan-out, rather than only testing correct SQL.
- Rebuild business definitions, all HospitalFlow Gold outputs and PNG/draw.io ERD together. Other datasets and their Gold records are outside this revision.
- Wholly synthetic records and illustrative parameters are used. No actual MIMIC records, fitted population distributions or measured identity-classifier accuracy are claimed.
