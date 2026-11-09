# HospitalFlow — authored Gold source bindings

Evaluation only; **not a model-generated Evidence Graph**.

| Physical Table | One Gold OT | Directly recorded Gold activities | Event timestamp columns |
|---|---|---|---|
| admission_detail | Hospital Admission | Discharge Summary Signed | discharge_summary_signed_at |
| admissions | Hospital Admission | Emergency Department Departed, Emergency Department Registered, Hospital Admitted, Hospital Discharged | admittime, dischtime, edouttime, edregtime |
| emar | Medication Administration | Medication Administered, Medication Not Given | charttime |
| lab_order | Laboratory Order | Lab Results Verified, Specimen Received | results_verified_at, specimen_received_at |
| labevents | Lab Measurement | Lab Result Available, Specimen Collected | charttime, storetime |
| medication_order | Medication Order | Medication Stopped | stopped_at |
| order_history | Order History Record | Order Cancelled, Order Entered, Order Reviewed | occurred_at |
| patients | Patient | — | — |
| pharmacy | Pharmacy Dispensing | Medication Dispensed | dispensed_at |
| procedure_episode | Procedure Episode | Procedure Completed, Procedure Started | endtime, starttime |
| procedure_order | Procedure Order | Procedure Preparation Completed | preparation_completed_at |
| transfers | Care Unit Transfer | Care Unit Transferred | intime |

The attribution of an event to cases or linked objects is defined by the corresponding Gold SQL; it is not equivalent to table OT membership.

[Diagram with OT on left](../database/gold_evidence_graph.svg) · [Question Gold DFG](README.md)

