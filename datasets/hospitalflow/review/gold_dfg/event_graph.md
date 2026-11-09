# Hospitalflow — Gold source inventory

**Author annotations.** One identity OT per physical table; event-to-object attribution is a separate relation.

| Physical table | Gold Object Type | Gold activity source labels |
|---|---|---|
| admission_detail | Hospital Admission | Discharge Summary Signed |
| admissions | Hospital Admission | Emergency Department Departed, Emergency Department Registered, Hospital Admitted, Hospital Discharged |
| emar | Medication Administration | Medication Administered, Medication Not Given |
| lab_order | Laboratory Order | Lab Results Verified, Specimen Received |
| labevents | Lab Measurement | Lab Result Available, Specimen Collected |
| medication_order | Medication Order | Medication Stopped |
| order_history | Order History Record | Order Cancelled, Order Entered, Order Reviewed |
| patients | Patient | — |
| pharmacy | Pharmacy Dispensing | Medication Dispensed |
| procedure_episode | Procedure Episode | Procedure Completed, Procedure Started |
| procedure_order | Procedure Order | Procedure Preparation Completed |
| transfers | Care Unit Transfer | Care Unit Transferred |

This is a source-binding projection. The model is not given this file.

[Gold diagram](../database/gold_evidence_graph.svg) · [Gold DFGs](README.md)
