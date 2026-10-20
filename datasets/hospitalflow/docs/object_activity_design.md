# Objects, types and activity scopes

| Case population | Semantic type | Objects | Activity types | Activity scope |
| --- | --- | --- | --- | --- |
| Patient | PATIENT | 12 | 18 | Discharge Authorized, Emergency Department Registered, Hospital Admitted, Hospital Discharged, Lab Measurement Charted, Lab Result Available, Lab Results Verified, Medication Administered, Medication Dispensed, Medication Not Given, Medication Stopped, Order Cancelled, Order Entered, Order Reviewed, Procedure Completed, Procedure Preparation Completed, Procedure Started, Specimen Received |
| Hospital Admission | ADMISSION | 15 | 18 | Discharge Authorized, Emergency Department Registered, Hospital Admitted, Hospital Discharged, Lab Measurement Charted, Lab Result Available, Lab Results Verified, Medication Administered, Medication Dispensed, Medication Not Given, Medication Stopped, Order Cancelled, Order Entered, Order Reviewed, Procedure Completed, Procedure Preparation Completed, Procedure Started, Specimen Received |
| Clinical Order | CLINICAL_ORDER | 45 | 14 | Lab Measurement Charted, Lab Result Available, Lab Results Verified, Medication Administered, Medication Dispensed, Medication Not Given, Medication Stopped, Order Cancelled, Order Entered, Order Reviewed, Procedure Completed, Procedure Preparation Completed, Procedure Started, Specimen Received |
| Laboratory Order | CLINICAL_ORDER | 15 | 6 | Lab Measurement Charted, Lab Result Available, Lab Results Verified, Order Entered, Order Reviewed, Specimen Received |
| Medication Order | CLINICAL_ORDER | 15 | 6 | Medication Administered, Medication Dispensed, Medication Not Given, Medication Stopped, Order Entered, Order Reviewed |
| Procedure Order | CLINICAL_ORDER | 15 | 6 | Order Cancelled, Order Entered, Order Reviewed, Procedure Completed, Procedure Preparation Completed, Procedure Started |

- Six case population scopes use three semantic object types; subtype scopes are not additional semantic types.
- Individual instances may have fewer activities due to cancellation, ongoing care or no records.
