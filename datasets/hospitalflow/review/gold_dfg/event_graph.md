# HospitalFlow — Gold source inventory

**Author annotations.** One identity OT per physical table; event-to-object attribution is a separate relation.

| Physical table | Gold Object Type | Gold activity source labels |
|---|---|---|
| admission_detail | Hospital Admission | — |
| admissions | Hospital Admission | — |
| emar | Medication Administration | — |
| lab_order | Laboratory Order | — |
| labevents | Lab Measurement | — |
| medication_order | Medication Order | — |
| order_history | Order History Record | — |
| patients | Patient | — |
| pharmacy | Pharmacy Dispensing | — |
| procedure_episode | Procedure Episode | — |
| procedure_order | Procedure Order | — |
| transfers | Care Unit Transfer | — |

This is a source-binding projection. The model is not given this file.

[Gold diagram](../database/gold_evidence_graph.svg) · [Gold DFGs](README.md)
