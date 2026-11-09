# HospitalFlow — legacy Entity Type candidates and direct event sources

Activities shown here are recorded in table rows; downstream Gold case attribution can associate them with additional business objects.

| OT | Physical source table | Direct source activities |
|---|---|---|
| Patient | patients | — |
| Hospital Admission | admissions | Emergency Department Departed, Emergency Department Registered, Hospital Admitted, Hospital Discharged |
| Hospital Admission | admission_detail | Discharge Summary Signed |
| Care Unit Transfer | transfers | Care Unit Transferred |
| Laboratory Order | lab_order | Lab Results Verified, Specimen Received |
| Medication Order | medication_order | Medication Stopped |
| Procedure Order | procedure_order | Procedure Preparation Completed |
| Order History Record | order_history | Order Cancelled, Order Entered, Order Reviewed |
| Lab Measurement | labevents | Lab Result Available, Specimen Collected |
| Medication Administration | emar | Medication Administered, Medication Not Given |
| Procedure Episode | procedure_episode | Procedure Completed, Procedure Started |
| Pharmacy Dispensing | pharmacy | Medication Dispensed |
