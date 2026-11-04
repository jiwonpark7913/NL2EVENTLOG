# hospitalflow: questions and Gold DFGs

**EVALUATION ONLY — NEVER PROVIDE TO A MODEL.**

Source commit: `ed132438b2a634a39da997e733751ccf1aa6322c`. Open index.html for search, review notes and complete case traces.

Node counts = event occurrences. Edge counts = adjacent selected events within a case. Dashed amber edges touch timestamp ties and depend on the tie-break rule. DFGs are projections of the selected log, not causal models.

## H01 — Q1

For each hospital admission, extract Order Entered, Order Reviewed and Order Cancelled events.

Events: **194** · Cases with events: **15** · Activities: **3** · Edges: **8**

![H01 Gold DFG](graphs/H01.svg)

[Gold CSV](../../../datasets/hospitalflow/private/gold_logs/H01.csv)

## H01P — Q2

For every hospital stay, build a timeline of when its orders were placed, checked and, if applicable, cancelled.

Events: **194** · Cases with events: **15** · Activities: **3** · Edges: **8**

![H01P Gold DFG](graphs/H01.svg)

[Gold CSV](../../../datasets/hospitalflow/private/gold_logs/H01P.csv)

## H02 — Q1

For each hospital admission, extract Lab Result Available, Medication Administered and Procedure Completed events.

Events: **124** · Cases with events: **14** · Activities: **3** · Edges: **9**

![H02 Gold DFG](graphs/H02.svg)

[Gold CSV](../../../datasets/hospitalflow/private/gold_logs/H02.csv)

## H02P — Q2

For every hospital stay, show when laboratory findings became available, medicines were given and procedures finished.

Events: **124** · Cases with events: **14** · Activities: **3** · Edges: **9**

![H02P Gold DFG](graphs/H02.svg)

[Gold CSV](../../../datasets/hospitalflow/private/gold_logs/H02P.csv)

## H03 — Q1

For each laboratory order, extract Specimen Collected, Lab Result Available and Lab Results Verified events.

Events: **154** · Cases with events: **30** · Activities: **3** · Edges: **4**

![H03 Gold DFG](graphs/H03.svg)

[Gold CSV](../../../datasets/hospitalflow/private/gold_logs/H03.csv)

## H03P — Q2

For every laboratory request, show when specimens were collected, when results became available and when those results were verified.

Events: **154** · Cases with events: **30** · Activities: **3** · Edges: **4**

![H03P Gold DFG](graphs/H03.svg)

[Gold CSV](../../../datasets/hospitalflow/private/gold_logs/H03P.csv)

## H04 — Q1

For each medication order, extract Medication Dispensed, Medication Administered, Medication Not Given and Medication Stopped events.

Events: **126** · Cases with events: **28** · Activities: **4** · Edges: **11**

![H04 Gold DFG](graphs/H04.svg)

[Gold CSV](../../../datasets/hospitalflow/private/gold_logs/H04.csv)

## H04P — Q2

Create a timeline for each medication order covering dispensing, each dose given or not given, and the stopping of the medication.

Events: **126** · Cases with events: **28** · Activities: **4** · Edges: **11**

![H04P Gold DFG](graphs/H04.svg)

[Gold CSV](../../../datasets/hospitalflow/private/gold_logs/H04P.csv)

## H05 — Q1

For each procedure order, extract Procedure Preparation Completed, Procedure Started and Procedure Completed events.

Events: **55** · Cases with events: **13** · Activities: **3** · Edges: **4**

![H05 Gold DFG](graphs/H05.svg)

[Gold CSV](../../../datasets/hospitalflow/private/gold_logs/H05.csv)

## H05P — Q2

For every procedure order, show when preparation finished and when each procedure occurrence began and ended.

Events: **55** · Cases with events: **13** · Activities: **3** · Edges: **4**

![H05P Gold DFG](graphs/H05.svg)

[Gold CSV](../../../datasets/hospitalflow/private/gold_logs/H05P.csv)

## H06 — Q1

For each hospital admission, extract Emergency Department Registered, Hospital Admitted, Discharge Authorized and Hospital Discharged events.

Events: **49** · Cases with events: **15** · Activities: **4** · Edges: **3**

![H06 Gold DFG](graphs/H06.svg)

[Gold CSV](../../../datasets/hospitalflow/private/gold_logs/H06.csv)

## H06P — Q2

For every hospital stay, show arrival registration in the emergency department, admission, authorization to leave and actual discharge.

Events: **49** · Cases with events: **15** · Activities: **4** · Edges: **3**

![H06P Gold DFG](graphs/H06.svg)

[Gold CSV](../../../datasets/hospitalflow/private/gold_logs/H06P.csv)

## H07 — Q1

For each patient, extract Hospital Admitted, Lab Result Available, Medication Administered, Procedure Completed and Hospital Discharged events.

Events: **158** · Cases with events: **11** · Activities: **5** · Edges: **18**

![H07 Gold DFG](graphs/H07.svg)

[Gold CSV](../../../datasets/hospitalflow/private/gold_logs/H07.csv)

## H07P — Q2

For each patient, collect the recorded hospital entries and departures, availability of laboratory findings, medicine administrations and finishes of procedures.

Events: **158** · Cases with events: **11** · Activities: **5** · Edges: **18**

![H07P Gold DFG](graphs/H07.svg)

[Gold CSV](../../../datasets/hospitalflow/private/gold_logs/H07P.csv)

## H08 — Q1

For each hospital admission, extract Insurance Claim Paid events.

**No Gold log:** No claim or payment records/timestamps exist in this DB; no Gold CSV is emitted.

## H08P — Q2

For each hospital stay, show when its insurance claim was settled by payment.

**No Gold log:** No claim or payment records/timestamps exist in this DB; no Gold CSV is emitted.

## HF01 — Q3

Extract the full recorded lifecycle for each patient.

Events: **628** · Cases with events: **11** · Activities: **20** · Edges: **132**

![HF01 Gold DFG](graphs/HF01.svg)

[Gold CSV](../../../datasets/hospitalflow/private/gold_logs/HF01.csv)

## HF01P — Q4

Build a complete timeline of all recorded care events for every patient.

Events: **628** · Cases with events: **11** · Activities: **20** · Edges: **132**

![HF01P Gold DFG](graphs/HF01.svg)

[Gold CSV](../../../datasets/hospitalflow/private/gold_logs/HF01P.csv)

## HF02 — Q3

Extract the full recorded lifecycle for each hospital admission.

Events: **595** · Cases with events: **15** · Activities: **19** · Edges: **127**

![HF02 Gold DFG](graphs/HF02.svg)

[Gold CSV](../../../datasets/hospitalflow/private/gold_logs/HF02.csv)

## HF02P — Q4

Show the entire recorded history of each individual hospital stay.

Events: **595** · Cases with events: **15** · Activities: **19** · Edges: **127**

![HF02P Gold DFG](graphs/HF02.svg)

[Gold CSV](../../../datasets/hospitalflow/private/gold_logs/HF02P.csv)

## HF03 — Q3

Extract the full recorded lifecycle for each order history record.

Events: **203** · Cases with events: **203** · Activities: **3** · Edges: **0**

![HF03 Gold DFG](graphs/HF03.svg)

[Gold CSV](../../../datasets/hospitalflow/private/gold_logs/HF03.csv)

## HF03P — Q4

Show the complete recorded history of every individual order history record.

Events: **203** · Cases with events: **203** · Activities: **3** · Edges: **0**

![HF03P Gold DFG](graphs/HF03.svg)

[Gold CSV](../../../datasets/hospitalflow/private/gold_logs/HF03P.csv)

## HF04 — Q3

Extract the full recorded lifecycle for each laboratory order.

Events: **267** · Cases with events: **34** · Activities: **6** · Edges: **8**

![HF04 Gold DFG](graphs/HF04.svg)

[Gold CSV](../../../datasets/hospitalflow/private/gold_logs/HF04.csv)

## HF04P — Q4

Show everything recorded over the life of each laboratory order.

Events: **267** · Cases with events: **34** · Activities: **6** · Edges: **8**

![HF04P Gold DFG](graphs/HF04.svg)

[Gold CSV](../../../datasets/hospitalflow/private/gold_logs/HF04P.csv)

## HF05 — Q3

Extract the full recorded lifecycle for each medication order.

Events: **198** · Cases with events: **29** · Activities: **6** · Edges: **15**

![HF05 Gold DFG](graphs/HF05.svg)

[Gold CSV](../../../datasets/hospitalflow/private/gold_logs/HF05.csv)

## HF05P — Q4

Build the complete recorded history of each medication order.

Events: **198** · Cases with events: **29** · Activities: **6** · Edges: **15**

![HF05P Gold DFG](graphs/HF05.svg)

[Gold CSV](../../../datasets/hospitalflow/private/gold_logs/HF05P.csv)

## HF06 — Q3

Extract the full recorded lifecycle for each procedure order.

Events: **103** · Cases with events: **17** · Activities: **6** · Edges: **8**

![HF06 Gold DFG](graphs/HF06.svg)

[Gold CSV](../../../datasets/hospitalflow/private/gold_logs/HF06.csv)

## HF06P — Q4

Trace the whole recorded lifecycle of every procedure order.

Events: **103** · Cases with events: **17** · Activities: **6** · Edges: **8**

![HF06P Gold DFG](graphs/HF06.svg)

[Gold CSV](../../../datasets/hospitalflow/private/gold_logs/HF06P.csv)

## H09 — Q1

For each patient, extract Patient Profile Verified events.

Events: **6** · Cases with events: **6** · Activities: **1** · Edges: **0**

![H09 Gold DFG](graphs/H09.svg)

[Gold CSV](../../../datasets/hospitalflow/private/gold_logs/H09.csv)

## H09P — Q2

For each patient, show when their supplementary personal information was verified.

Events: **6** · Cases with events: **6** · Activities: **1** · Edges: **0**

![H09P Gold DFG](graphs/H09.svg)

[Gold CSV](../../../datasets/hospitalflow/private/gold_logs/H09P.csv)

## H10 — Q1

For each hospital admission, extract Discharge Summary Signed events.

Events: **5** · Cases with events: **5** · Activities: **1** · Edges: **0**

![H10 Gold DFG](graphs/H10.svg)

[Gold CSV](../../../datasets/hospitalflow/private/gold_logs/H10.csv)

## H10P — Q2

For each hospital stay, show when its discharge summary was signed.

Events: **5** · Cases with events: **5** · Activities: **1** · Edges: **0**

![H10P Gold DFG](graphs/H10.svg)

[Gold CSV](../../../datasets/hospitalflow/private/gold_logs/H10P.csv)

## H11 — Q1

For each patient, extract Patient Profile Verified and Hospital Admitted events.

Events: **21** · Cases with events: **11** · Activities: **2** · Edges: **2**

![H11 Gold DFG](graphs/H11.svg)

[Gold CSV](../../../datasets/hospitalflow/private/gold_logs/H11.csv)

## H11P — Q2

Build a timeline for every patient showing verification of their supplementary personal information and their entries into hospital.

Events: **21** · Cases with events: **11** · Activities: **2** · Edges: **2**

![H11P Gold DFG](graphs/H11.svg)

[Gold CSV](../../../datasets/hospitalflow/private/gold_logs/H11P.csv)

## HF07 — Q3

Extract the full recorded lifecycle for each lab measurement.

Events: **124** · Cases with events: **62** · Activities: **2** · Edges: **1**

![HF07 Gold DFG](graphs/HF07.svg)

[Gold CSV](../../../datasets/hospitalflow/private/gold_logs/HF07.csv)

## HF07P — Q4

Show the entire recorded history of each individual laboratory measurement.

Events: **124** · Cases with events: **62** · Activities: **2** · Edges: **1**

![HF07P Gold DFG](graphs/HF07.svg)

[Gold CSV](../../../datasets/hospitalflow/private/gold_logs/HF07P.csv)

## HF08 — Q3

Extract the full recorded lifecycle for each medication administration.

Events: **67** · Cases with events: **67** · Activities: **2** · Edges: **0**

![HF08 Gold DFG](graphs/HF08.svg)

[Gold CSV](../../../datasets/hospitalflow/private/gold_logs/HF08.csv)

## HF08P — Q4

Build the complete recorded history of every individual medication administration record.

Events: **67** · Cases with events: **67** · Activities: **2** · Edges: **0**

![HF08P Gold DFG](graphs/HF08.svg)

[Gold CSV](../../../datasets/hospitalflow/private/gold_logs/HF08P.csv)

## HF09 — Q3

Extract the full recorded lifecycle for each procedure episode.

Events: **42** · Cases with events: **23** · Activities: **2** · Edges: **1**

![HF09 Gold DFG](graphs/HF09.svg)

[Gold CSV](../../../datasets/hospitalflow/private/gold_logs/HF09.csv)

## HF09P — Q4

Trace each individual procedure episode through its whole recorded lifecycle.

Events: **42** · Cases with events: **23** · Activities: **2** · Edges: **1**

![HF09P Gold DFG](graphs/HF09.svg)

[Gold CSV](../../../datasets/hospitalflow/private/gold_logs/HF09P.csv)

## HF10 — Q3

Extract the full recorded lifecycle for each pharmacy dispensing record.

Events: **101** · Cases with events: **34** · Activities: **3** · Edges: **5**

![HF10 Gold DFG](graphs/HF10.svg)

[Gold CSV](../../../datasets/hospitalflow/private/gold_logs/HF10.csv)

## HF10P — Q4

Show the complete recorded course associated with each individual pharmacy dispensing record.

Events: **101** · Cases with events: **34** · Activities: **3** · Edges: **5**

![HF10P Gold DFG](graphs/HF10.svg)

[Gold CSV](../../../datasets/hospitalflow/private/gold_logs/HF10P.csv)

## H12 — Q1

For each pharmacy dispensing record, extract Medication Dispensed, Medication Administered and Medication Not Given events.

Events: **101** · Cases with events: **34** · Activities: **3** · Edges: **5**

![H12 Gold DFG](graphs/HF10.svg)

[Gold CSV](../../../datasets/hospitalflow/private/gold_logs/H12.csv)

## H12P — Q2

Group the medication dispensing, subsequent doses given and doses not given by the pharmacy dispensing record they refer to.

Events: **101** · Cases with events: **34** · Activities: **3** · Edges: **5**

![H12P Gold DFG](graphs/HF10.svg)

[Gold CSV](../../../datasets/hospitalflow/private/gold_logs/H12P.csv)
