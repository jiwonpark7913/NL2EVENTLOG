# HospitalFlow questions

## Question types and pairs

| Type | Questions | Answerable | Non-answerable | Avg. requested activity types |
| --- | --- | --- | --- | --- |
| Q1 | 8 | 7 | 1 | 3.25 |
| Q2 | 8 | 7 | 1 | 3.25 |
| Q3 | 6 | 6 | 0 | 11.33 |
| Q4 | 6 | 6 | 0 | 11.33 |

- Average includes all requests in the type, including unsupported activity requests.
- Process View includes the case concept and activity scope. Q3/Q4 leave the scope implicit via the catalog.
- Each P question is an assistant-LLM paraphrase of the frozen seed; prompts and outputs are saved in source/llm_paraphrases.json.

| ID | Type | Paired with | Answerability | Requested activities | Extractable activities | Question |
| --- | --- | --- | --- | --- | --- | --- |
| H01 | Q1 | H01P | Answerable | 3 | 3 | For each clinical order, extract Order Entered, Order Reviewed and Order Cancelled events. |
| H01P | Q2 | H01 | Answerable | 3 | 3 | Build a separate timeline for every clinical order showing when it was placed, checked and, if applicable, cancelled. |
| H02 | Q1 | H02P | Answerable | 3 | 3 | For each clinical order, extract Lab Result Available, Medication Administered and Procedure Completed events. |
| H02P | Q2 | H02 | Answerable | 3 | 3 | For every clinical order, show the recorded times when its laboratory findings became available, its medicine was given or its procedure finished, as applicable. |
| H03 | Q1 | H03P | Answerable | 3 | 3 | For each laboratory order, extract Lab Measurement Charted, Lab Result Available and Lab Results Verified events. |
| H03P | Q2 | H03 | Answerable | 3 | 3 | For every laboratory order, show when each measurement was charted, when its findings became accessible and when the order's results were verified. |
| H04 | Q1 | H04P | Answerable | 4 | 4 | For each medication order, extract Medication Dispensed, Medication Administered, Medication Not Given and Medication Stopped events. |
| H04P | Q2 | H04 | Answerable | 4 | 4 | Create a timeline for each medication order covering dispensing, each dose given or not given, and the stopping of the medication. |
| H05 | Q1 | H05P | Answerable | 3 | 3 | For each procedure order, extract Procedure Preparation Completed, Procedure Started and Procedure Completed events. |
| H05P | Q2 | H05 | Answerable | 3 | 3 | For every procedure order, show when preparation finished and when each procedure occurrence began and ended. |
| H06 | Q1 | H06P | Answerable | 4 | 4 | For each hospital admission, extract Emergency Department Registered, Hospital Admitted, Discharge Authorized and Hospital Discharged events. |
| H06P | Q2 | H06 | Answerable | 4 | 4 | For every hospital stay, show arrival registration in the emergency department, admission, authorization to leave and actual discharge. |
| H07 | Q1 | H07P | Answerable | 5 | 5 | For each patient, extract Hospital Admitted, Lab Result Available, Medication Administered, Procedure Completed and Hospital Discharged events. |
| H07P | Q2 | H07 | Answerable | 5 | 5 | For each patient, collect the recorded hospital entries and departures, availability of laboratory findings, medicine administrations and finishes of procedures. |
| H08 | Q1 | H08P | Non-answerable | 1 | 0 | For each clinical order, extract Insurance Claim Paid events. |
| H08P | Q2 | H08 | Non-answerable | 1 | 0 | For every clinical order, show when its insurance claim was settled by payment. |
| HF01 | Q3 | HF01P | Answerable | 18 | 18 | Extract the full recorded lifecycle for each patient. |
| HF01P | Q4 | HF01 | Answerable | 18 | 18 | Build a complete timeline of all recorded care events for every patient. |
| HF02 | Q3 | HF02P | Answerable | 18 | 18 | Extract the full recorded lifecycle for each hospital admission. |
| HF02P | Q4 | HF02 | Answerable | 18 | 18 | Show the entire recorded history of each individual hospital stay. |
| HF03 | Q3 | HF03P | Answerable | 14 | 14 | Extract the full recorded lifecycle for each clinical order. |
| HF03P | Q4 | HF03 | Answerable | 14 | 14 | Trace each clinical order through its complete recorded history. |
| HF04 | Q3 | HF04P | Answerable | 6 | 6 | Extract the full recorded lifecycle for each laboratory order. |
| HF04P | Q4 | HF04 | Answerable | 6 | 6 | Show everything recorded over the life of each laboratory order. |
| HF05 | Q3 | HF05P | Answerable | 6 | 6 | Extract the full recorded lifecycle for each medication order. |
| HF05P | Q4 | HF05 | Answerable | 6 | 6 | Build the complete recorded history of each medication order. |
| HF06 | Q3 | HF06P | Answerable | 6 | 6 | Extract the full recorded lifecycle for each procedure order. |
| HF06P | Q4 | HF06 | Answerable | 6 | 6 | Trace the whole recorded lifecycle of every procedure order. |
