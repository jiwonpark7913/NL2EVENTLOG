# HospitalFlow — Gold source inventory

**Author annotations (legacy ET candidates).** One ER per physical table. Event-to-entity attribution is a separate relation and same-ET does not imply same entity instance.

| Physical table | Entity Type candidate | Gold activity source labels |
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

This is a source-binding projection. This is a reviewer-only candidate grouping and is not provided to the model.

[Gold diagram](../database/gold_evidence_graph.svg) · [Gold DFGs](README.md)

[Entity Representation and namespace candidates](entity_model_candidates.json) — review-only; **not validated semantic ET Gold**.
