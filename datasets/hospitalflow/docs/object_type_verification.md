# HospitalFlow — object identity Gold

A physical table is one **Entity Representation (ER)**. Its displayed **Entity Type (ET) candidate** comes from legacy Gold annotations. ET semantic grouping and cross-ER instance identity resolution must be validated independently. FK reachability alone does not establish Case Attribution or Lifecycle Membership.

| Entity Type | Member physical tables | Identity evidence |
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

**Legacy annotation:** 11 identity groups; only admissions and admission_detail share a supported primary-key identity. Semantic ET group review may regroup different entity populations without merging instances. Order history, lab measurements, medication administrations, pharmacy dispensing and transfer records have independent occurrence identities.

Domain grouping is visual only, not evidence of semantic ET equality or shared instance identity.

