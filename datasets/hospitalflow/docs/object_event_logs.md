# Full lifecycle Gold logs

| Population | Q3 | Q4 | Objects | Cases without events |
| --- | --- | --- | --- | --- |
| Patient | HF01 | HF01P | 12 | 1 |
| Hospital Admission | HF02 | HF02P | 15 | 0 |
| Clinical Order | HF03 | HF03P | 45 | 0 |
| Laboratory Order | HF04 | HF04P | 15 | 0 |
| Medication Order | HF05 | HF05P | 15 | 0 |
| Procedure Order | HF06 | HF06P | 15 | 0 |

- Gold CSVs contain events only. Empty cases remain in ES.case_population and the task scope catalog.
- Query-specific CSVs are case-based logs, not OCEL. Shared events may occur under different cases in different process views.
