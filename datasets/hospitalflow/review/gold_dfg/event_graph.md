# hospitalflow · Event graph inventory

**EVALUATION ONLY.** [Back to question and DFG review](README.md).

This page shows the authored benchmark graph. Table bindings identify where events are recorded. Object links identify which activities are attributed to an object, including activities recorded in other tables.

OT groups use the authored identity annotations. For each split-table member, the object section projects canonical event links onto the keys present in that table.
Every physical object without an explicit group gets a singleton OT. Table-named singletons have no authored object-view attribution. See Events produced for their source activities.

## Tables and event sources

| Table | Event classification | Carrier column | Selected event timestamps | Physical object (table · PK) | OT group | Events produced |
|---|---|---|---|---|---|---|
| `admission_detail` | Event · non-carrier | — | `discharge_summary_signed_at` | `admission_detail` · `hadm_id` | Hospital Admission | Discharge Summary Signed |
| `admissions` | Event · non-carrier | — | `admittime`, `discharge_authorized_at`, `dischtime`, `edregtime` | `admissions` · `hadm_id` | Hospital Admission | Discharge Authorized, Emergency Department Registered, Hospital Admitted, Hospital Discharged |
| `emar` | Event · carrier | `event_txt` | `charttime` | `emar` · `emar_id` | Medication Administration | Medication Administered, Medication Not Given |
| `lab_order` | Event · non-carrier | — | `results_verified_at`, `specimen_received_at` | `lab_order` · `order_id` | Laboratory Order | Lab Results Verified, Specimen Received |
| `labevents` | Event · non-carrier | — | `charttime`, `storetime` | `labevents` · `labevent_id` | Lab Measurement | Lab Result Available, Specimen Collected |
| `medication_order` | Event · non-carrier | — | `stopped_at` | `medication_order` · `order_id` | Medication Order | Medication Stopped |
| `order_history` | Event · carrier | `action` | `occurred_at` | `order_history` · `history_id` | Order History Record | Order Cancelled, Order Entered, Order Reviewed |
| `patient_profile` | Event · non-carrier | — | `profile_verified_at` | `patient_profile` · `subject_id` | Patient | Patient Profile Verified |
| `patients` | Non-event | — | — | `patients` · `subject_id` | Patient | — |
| `pharmacy` | Event · non-carrier | — | `dispensed_at` | `pharmacy` · `pharmacy_id` | Pharmacy Dispensing | Medication Dispensed |
| `procedure_episode` | Event · non-carrier | — | `endtime`, `starttime` | `procedure_episode` · `procedureevent_id` | Procedure Episode | Procedure Completed, Procedure Started |
| `procedure_order` | Event · non-carrier | — | `preparation_completed_at` | `procedure_order` · `order_id` | Procedure Order | Procedure Preparation Completed |

## Object types and attributed activities

| OT group | Member physical objects | Activities linked to OT |
|---|---|---|
| Patient | `patients`, `patient_profile` | Discharge Authorized, Discharge Summary Signed, Emergency Department Registered, Hospital Admitted, Hospital Discharged, Lab Result Available, Lab Results Verified, Medication Administered, Medication Dispensed, Medication Not Given, Medication Stopped, Order Cancelled, Order Entered, Order Reviewed, Patient Profile Verified, Procedure Completed, Procedure Preparation Completed, Procedure Started, Specimen Collected, Specimen Received |
| Hospital Admission | `admissions`, `admission_detail` | Discharge Authorized, Discharge Summary Signed, Emergency Department Registered, Hospital Admitted, Hospital Discharged, Lab Result Available, Lab Results Verified, Medication Administered, Medication Dispensed, Medication Not Given, Medication Stopped, Order Cancelled, Order Entered, Order Reviewed, Procedure Completed, Procedure Preparation Completed, Procedure Started, Specimen Collected, Specimen Received |
| Laboratory Order | `lab_order` | Lab Result Available, Lab Results Verified, Order Entered, Order Reviewed, Specimen Collected, Specimen Received |
| Medication Order | `medication_order` | Medication Administered, Medication Dispensed, Medication Not Given, Medication Stopped, Order Entered, Order Reviewed |
| Procedure Order | `procedure_order` | Order Cancelled, Order Entered, Order Reviewed, Procedure Completed, Procedure Preparation Completed, Procedure Started |
| Order History Record | `order_history` | Order Cancelled, Order Entered, Order Reviewed |
| Lab Measurement | `labevents` | Lab Result Available, Specimen Collected |
| Medication Administration | `emar` | Medication Administered, Medication Not Given |
| Procedure Episode | `procedure_episode` | Procedure Completed, Procedure Started |
| Pharmacy Dispensing | `pharmacy` | Medication Administered, Medication Dispensed, Medication Not Given |

## Physical objects and attributed activities

| Physical object | OT group | Activities linked to this object |
|---|---|---|
| `admission_detail` | Hospital Admission | Discharge Authorized, Discharge Summary Signed, Emergency Department Registered, Hospital Admitted, Hospital Discharged, Lab Result Available, Lab Results Verified, Medication Administered, Medication Dispensed, Medication Not Given, Medication Stopped, Order Cancelled, Order Entered, Order Reviewed, Procedure Completed, Procedure Preparation Completed, Procedure Started, Specimen Collected, Specimen Received |
| `admissions` | Hospital Admission | Discharge Authorized, Discharge Summary Signed, Emergency Department Registered, Hospital Admitted, Hospital Discharged, Lab Result Available, Lab Results Verified, Medication Administered, Medication Dispensed, Medication Not Given, Medication Stopped, Order Cancelled, Order Entered, Order Reviewed, Procedure Completed, Procedure Preparation Completed, Procedure Started, Specimen Collected, Specimen Received |
| `emar` | Medication Administration | Medication Administered, Medication Not Given |
| `lab_order` | Laboratory Order | Lab Result Available, Lab Results Verified, Order Entered, Order Reviewed, Specimen Collected, Specimen Received |
| `labevents` | Lab Measurement | Lab Result Available, Specimen Collected |
| `medication_order` | Medication Order | Medication Administered, Medication Dispensed, Medication Not Given, Medication Stopped, Order Entered, Order Reviewed |
| `order_history` | Order History Record | Order Cancelled, Order Entered, Order Reviewed |
| `patient_profile` | Patient | Discharge Authorized, Discharge Summary Signed, Emergency Department Registered, Hospital Admitted, Hospital Discharged, Lab Result Available, Lab Results Verified, Medication Administered, Medication Dispensed, Medication Not Given, Medication Stopped, Order Cancelled, Order Entered, Order Reviewed, Patient Profile Verified, Procedure Completed, Procedure Preparation Completed, Procedure Started, Specimen Collected, Specimen Received |
| `patients` | Patient | Discharge Authorized, Discharge Summary Signed, Emergency Department Registered, Hospital Admitted, Hospital Discharged, Lab Result Available, Lab Results Verified, Medication Administered, Medication Dispensed, Medication Not Given, Medication Stopped, Order Cancelled, Order Entered, Order Reviewed, Patient Profile Verified, Procedure Completed, Procedure Preparation Completed, Procedure Started, Specimen Collected, Specimen Received |
| `pharmacy` | Pharmacy Dispensing | Medication Administered, Medication Dispensed, Medication Not Given |
| `procedure_episode` | Procedure Episode | Procedure Completed, Procedure Started |
| `procedure_order` | Procedure Order | Order Cancelled, Order Entered, Order Reviewed, Procedure Completed, Procedure Preparation Completed, Procedure Started |
