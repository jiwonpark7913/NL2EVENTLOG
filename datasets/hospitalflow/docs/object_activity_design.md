# Objects, types and activity scopes

| Object Type | Instances | Activity types | Activity scope |
| --- | --- | --- | --- |
| Patient | 12 | 20 | Discharge Authorized, Discharge Summary Signed, Emergency Department Registered, Hospital Admitted, Hospital Discharged, Lab Measurement Charted, Lab Result Available, Lab Results Verified, Medication Administered, Medication Dispensed, Medication Not Given, Medication Stopped, Order Cancelled, Order Entered, Order Reviewed, Patient Profile Verified, Procedure Completed, Procedure Preparation Completed, Procedure Started, Specimen Received |
| Hospital Admission | 15 | 19 | Discharge Authorized, Discharge Summary Signed, Emergency Department Registered, Hospital Admitted, Hospital Discharged, Lab Measurement Charted, Lab Result Available, Lab Results Verified, Medication Administered, Medication Dispensed, Medication Not Given, Medication Stopped, Order Cancelled, Order Entered, Order Reviewed, Procedure Completed, Procedure Preparation Completed, Procedure Started, Specimen Received |
| Laboratory Order | 15 | 6 | Lab Measurement Charted, Lab Result Available, Lab Results Verified, Order Entered, Order Reviewed, Specimen Received |
| Medication Order | 15 | 6 | Medication Administered, Medication Dispensed, Medication Not Given, Medication Stopped, Order Entered, Order Reviewed |
| Procedure Order | 15 | 6 | Order Cancelled, Order Entered, Order Reviewed, Procedure Completed, Procedure Preparation Completed, Procedure Started |
| Order History Record | 102 | 3 | Order Cancelled, Order Entered, Order Reviewed |
| Lab Measurement | 33 | 2 | Lab Measurement Charted, Lab Result Available |
| Medication Administration | 45 | 2 | Medication Administered, Medication Not Given |
| Procedure Episode | 15 | 2 | Procedure Completed, Procedure Started |

- Eleven Physical Objects map to nine expected identity-compatible Object Type groups. History/measurement/dose/episode records retain independent occurrence identities.
- Individual instances may contain fewer activities due to cancellation, ongoing care or missing records.
