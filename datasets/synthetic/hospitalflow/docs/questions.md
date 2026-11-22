# hospitalflow — Question definitions and Gold review

[Interactive question / DFG / source-row review](../review/gold_dfg/index.html)

Q1: explicit; Q2: explicit paraphrase; Q3: lifecycle; Q4: lifecycle paraphrase. Pairs retain the same scope and Gold log. Revised requests and paraphrases are author edits following the 2026-11-20 audit.

| ID | Type | Pair | Case | Process focus | Answerability | Supported activities | Observed activities | Events | Question |
|---|---|---|---|---|---|---:|---:|---:|---|
| H01 | Q1 | H01P | Hospital Admission |  | answerable | 3 | 3 | 194 | For each hospital admission, extract Order Entered, Order Reviewed and Order Cancelled events. |
| H01P | Q2 | H01 | Hospital Admission |  | answerable | 3 | 3 | 194 | For every hospital stay, build a timeline of when its orders were placed, checked and, if applicable, cancelled. |
| H02 | Q1 | H02P | Hospital Admission |  | answerable | 3 | 3 | 124 | For each hospital admission, extract Lab Result Available, Medication Administered and Procedure Completed events. |
| H02P | Q2 | H02 | Hospital Admission |  | answerable | 3 | 3 | 124 | For every hospital stay, show when laboratory findings became available, medicines were given and procedures finished. |
| H03 | Q1 | H03P | Laboratory Order |  | answerable | 3 | 3 | 154 | For each laboratory order, extract Specimen Collected, Lab Result Available and Lab Results Verified events. |
| H03P | Q2 | H03 | Laboratory Order |  | answerable | 3 | 3 | 154 | For every laboratory request, show when specimens were collected, when results became available and when those results were verified. |
| H04 | Q1 | H04P | Medication Order |  | answerable | 4 | 4 | 126 | For each medication order, extract Medication Dispensed, Medication Administered, Medication Not Given and Medication Stopped events. |
| H04P | Q2 | H04 | Medication Order |  | answerable | 4 | 4 | 126 | Create a timeline for each medication order covering dispensing, each dose given or not given, and the stopping of the medication. |
| H05 | Q1 | H05P | Procedure Order |  | answerable | 3 | 3 | 55 | For each procedure order, extract Procedure Preparation Completed, Procedure Started and Procedure Completed events. |
| H05P | Q2 | H05 | Procedure Order |  | answerable | 3 | 3 | 55 | For every procedure order, show when preparation finished and when each procedure occurrence began and ended. |
| H06 | Q1 | H06P | Hospital Admission |  | answerable | 4 | 4 | 44 | For each hospital admission, extract Emergency Department Registered, Hospital Admitted, Emergency Department Departed and Hospital Discharged events. |
| H06P | Q2 | H06 | Hospital Admission |  | answerable | 4 | 4 | 44 | For every hospital stay, show arrival registration in the emergency department, admission, departure from the emergency department and actual discharge. |
| H07 | Q1 | H07P | Patient |  | answerable | 5 | 5 | 158 | For each patient, extract Hospital Admitted, Lab Result Available, Medication Administered, Procedure Completed and Hospital Discharged events. |
| H07P | Q2 | H07 | Patient |  | answerable | 5 | 5 | 158 | For each patient, collect the recorded hospital entries and departures, availability of laboratory findings, medicine administrations and finishes of procedures. |
| HF01 | Q3 | HF01P | Patient |  | answerable | 20 | 20 | 627 | Extract the full recorded lifecycle for each patient. |
| HF01P | Q4 | HF01 | Patient |  | answerable | 20 | 20 | 627 | Build a complete timeline of all recorded care events for every patient. |
| HF02 | Q3 | HF02P | Hospital Admission |  | answerable | 20 | 20 | 600 | Extract the full recorded lifecycle for each hospital admission. |
| HF02P | Q4 | HF02 | Hospital Admission |  | answerable | 20 | 20 | 600 | Show the entire recorded history of each individual hospital stay. |
| HF03 | Q3 | HF03P | Hospital Admission | laboratory testing | answerable | 7 | 6 | 240 | Extract the full recorded laboratory-testing lifecycle for each hospital admission. |
| HF03P | Q4 | HF03 | Hospital Admission | laboratory testing | answerable | 7 | 6 | 240 | For every hospital stay, reconstruct the entire recorded history of its laboratory testing. |
| HF04 | Q3 | HF04P | Laboratory Order |  | answerable | 6 | 6 | 267 | Extract the full recorded lifecycle for each laboratory order. |
| HF04P | Q4 | HF04 | Laboratory Order |  | answerable | 6 | 6 | 267 | Show everything recorded over the life of each laboratory order. |
| HF05 | Q3 | HF05P | Medication Order |  | answerable | 6 | 6 | 198 | Extract the full recorded lifecycle for each medication order. |
| HF05P | Q4 | HF05 | Medication Order |  | answerable | 6 | 6 | 198 | Build the complete recorded history of each medication order. |
| HF06 | Q3 | HF06P | Procedure Order |  | answerable | 6 | 6 | 103 | Extract the full recorded lifecycle for each procedure order. |
| HF06P | Q4 | HF06 | Procedure Order |  | answerable | 6 | 6 | 103 | Trace the whole recorded lifecycle of every procedure order. |
| H09 | Q1 | H09P | Patient |  | answerable | 1 | 1 | 10 | For each patient, extract Care Unit Transferred events. |
| H09P | Q2 | H09 | Patient |  | answerable | 1 | 1 | 10 | Show when each patient moved to a different hospital care unit. |
| H11 | Q1 | H11P | Patient |  | answerable | 2 | 2 | 25 | For each patient, extract Hospital Admitted and Care Unit Transferred events. |
| H11P | Q2 | H11 | Patient |  | answerable | 2 | 2 | 25 | Build a timeline for every patient showing their entries into hospital and their moves to a different hospital care unit. |
| HF07 | Q3 | HF07P | Lab Measurement |  | answerable | 2 | 2 | 124 | Extract the full recorded lifecycle for each lab measurement. |
| HF07P | Q4 | HF07 | Lab Measurement |  | answerable | 2 | 2 | 124 | Show the entire recorded history of each individual laboratory measurement. |
| HF08 | Q3 | HF08P | Patient | medication treatment | answerable | 7 | 6 | 198 | Extract the full recorded medication-treatment lifecycle for each patient. |
| HF08P | Q4 | HF08 | Patient | medication treatment | answerable | 7 | 6 | 198 | For every patient, reconstruct the complete recorded history of their medication treatment. |
| HF09 | Q3 | HF09P | Procedure Episode |  | answerable | 2 | 2 | 42 | Extract the full recorded lifecycle for each procedure episode. |
| HF09P | Q4 | HF09 | Procedure Episode |  | answerable | 2 | 2 | 42 | Trace each individual procedure episode through its whole recorded lifecycle. |
| HF10 | Q3 | HF10P | Pharmacy Dispensing |  | answerable | 3 | 3 | 101 | Extract the full recorded lifecycle for each pharmacy dispensing record. |
| HF10P | Q4 | HF10 | Pharmacy Dispensing |  | answerable | 3 | 3 | 101 | Show the complete recorded course associated with each individual pharmacy dispensing record. |
| H12 | Q1 | H12P | Pharmacy Dispensing |  | answerable | 3 | 3 | 101 | For each pharmacy dispensing record, extract Medication Dispensed, Medication Administered and Medication Not Given events. |
| H12P | Q2 | H12 | Pharmacy Dispensing |  | answerable | 3 | 3 | 101 | Group the medication dispensing, subsequent doses given and doses not given by the pharmacy dispensing record they refer to. |
