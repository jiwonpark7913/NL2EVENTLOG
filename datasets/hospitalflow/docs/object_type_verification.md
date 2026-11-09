# HospitalFlow — object identity Gold

A physical table belongs to exactly one OT. Do not conflate FK associations with equal business-object identity.

| Object Type | Member physical tables | Identity evidence |
|---|---|---|
| Patient | patients | Distinct record grain and primary key |
| Hospital Admission | admissions, admission_detail | Shared hadm_id, enforced shared-PK FK |
| Care Unit Transfer | transfers | Distinct record grain and primary key |
| Laboratory Order | lab_order | Distinct record grain and primary key |
| Medication Order | medication_order | Distinct record grain and primary key |
| Procedure Order | procedure_order | Distinct record grain and primary key |
| Order History Record | order_history | Distinct record grain and primary key |
| Lab Measurement | labevents | Distinct record grain and primary key |
| Medication Administration | emar | Distinct record grain and primary key |
| Procedure Episode | procedure_episode | Distinct record grain and primary key |
| Pharmacy Dispensing | pharmacy | Distinct record grain and primary key |

**Decision:** Keep 11 OTs. Merge only admissions with admission_detail. Order history, lab measurements, medication administrations, pharmacy dispensing and transfer records have independent occurrence identities.

Clinical grouping in the diagram is presentation only, not an ontology merge.

