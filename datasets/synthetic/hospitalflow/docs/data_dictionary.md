# HospitalFlow — current data dictionary

Generated from the model-visible `input/data_dictionary.json`. HospitalFlow uses wholly synthetic records and MIMIC-IV-inspired structural terms.

| Physical table | Description | PK |
|---|---|---|
| `patients` | MIMIC-IV-compatible patient demographics and anchor metadata (synthetic). | subject_id |

## `patients`

| Column | Type | Business definition |
|---|---|---|
| `subject_id` | INTEGER | Identifier of the patient represented by this row. |
| `gender` | TEXT | Synthetic demographic category recorded for the patient. |
| `anchor_age` | INTEGER | Age in synthetic anchor_year; not an event. |
| `anchor_year` | INTEGER | Synthetic de-identified reference year. |
| `anchor_year_group` | TEXT | Approximate original-year group (synthetic). |
| `dod` | TEXT | Date of death if known; not an assumed process event. |

| `admissions` | Synthetic hospital stay using original MIMIC-IV admissions time-column names. | hadm_id |

## `admissions`

| Column | Type | Business definition |
|---|---|---|
| `hadm_id` | INTEGER | Identifier of this particular hospital admission, distinct from the patient identifier. |
| `subject_id` | INTEGER | Patient to whom this hospital admission belongs. |
| `edregtime` | TEXT | Time of emergency department registration associated with this admission. |
| `admittime` | TEXT | Time when the patient was admitted for this hospital stay. |
| `dischtime` | TEXT | Time when the patient actually left this hospital stay. |
| `deathtime` | TEXT | Actual death timestamp if observed during this admission; NULL in current synthetic cohort. |
| `edouttime` | TEXT | Time the patient departed the emergency department, as in MIMIC-IV. |
| `admission_type` | TEXT | Type of admission; administrative attribute, not event. |
| `admit_provider_id` | TEXT | Admission provider reference. |
| `admission_location` | TEXT | Location from which admission occurred. |
| `discharge_location` | TEXT | Discharge destination. |
| `insurance` | TEXT | Recorded payor category. |
| `language` | TEXT | Admission-level language preference, not a patient master attribute. |
| `marital_status` | TEXT | Marital status at admission. |
| `race` | TEXT | Recorded demographic classification at admission. |
| `hospital_expire_flag` | INTEGER | Whether death occurred during admission (all zero in synthetic sample). |

| `admission_detail` | Recorded signed discharge summaries associated with hospital admissions. | hadm_id |

## `admission_detail`

| Column | Type | Business definition |
|---|---|---|
| `hadm_id` | INTEGER | Identifier of the same hospital stay represented in admissions.hadm_id. |
| `discharge_summary_signed_at` | TEXT | Time when the discharge summary for this admission was signed; signing may occur after the patient has left the hospital. |

| `lab_order` | Laboratory request; multiple measurements can fulfill it. subject_id identifies the patient even when hadm_id is NULL for a request outside an admission. | order_id |

## `lab_order`

| Column | Type | Business definition |
|---|---|---|
| `order_id` | INTEGER | Identifier of this laboratory request in the laboratory-order identifier namespace. |
| `subject_id` | INTEGER | Patient for this laboratory request, including requests not associated with a hospital admission. |
| `hadm_id` | INTEGER | Optional hospital admission associated with this laboratory request. |
| `specimen_received_at` | TEXT | Time when specimens associated with this laboratory request were received by the laboratory. |
| `results_verified_at` | TEXT | Time when the recorded results for this laboratory order were verified. |

| `medication_order` | One medication prescription, including its stop time. Dispensing is recorded separately in pharmacy. | order_id |

## `medication_order`

| Column | Type | Business definition |
|---|---|---|
| `order_id` | INTEGER | Identifier of this medication request in the medication-order identifier namespace. |
| `hadm_id` | INTEGER | Hospital admission under which this medication request was made. |
| `medication` | TEXT | Generic medication name for synthetic records; not a treatment recommendation. |
| `stopped_at` | TEXT | Time when medication under this request was stopped. |

| `procedure_order` | Distinct procedure order; repeated execution episodes belong to one order. | order_id |

## `procedure_order`

| Column | Type | Business definition |
|---|---|---|
| `order_id` | INTEGER | Identifier of this procedure request in the procedure-order identifier namespace. |
| `hadm_id` | INTEGER | Hospital admission under which this procedure request was made. |
| `procedure_name` | TEXT | Fictional procedure label associated with this synthetic procedure request. |
| `preparation_completed_at` | TEXT | Time when preparation for this procedure request was completed. |

| `order_history` | Recorded actions on laboratory, medication or procedure requests, including repeated reviews. | history_id |

## `order_history`

| Column | Type | Business definition |
|---|---|---|
| `history_id` | INTEGER | Identifier of one order-action occurrence; separate reviews of an order have separate identifiers. |
| `lab_order_id` | INTEGER | Laboratory order on which this action was performed, when the action concerns a laboratory request. |
| `medication_order_id` | INTEGER | Medication order on which this action was performed, when the action concerns a medication request. |
| `procedure_order_id` | INTEGER | Procedure order on which this action was performed, when the action concerns a procedure request. |
| `action` | TEXT | Physical business-action code in order_history; E = Entered; R = Reviewed; C = Cancelled. Recorded occurrence time is given by the corresponding event timestamp; the code alone is not proof of occurrence. |
| `occurred_at` | TEXT | Time when this particular order action occurred. |

| `labevents` | Laboratory measurement results with specimen collection and result-availability times. charttime denotes specimen collection, not measurement execution. | labevent_id |

## `labevents`

| Column | Type | Business definition |
|---|---|---|
| `labevent_id` | INTEGER | Identifier of this individual laboratory measurement occurrence. |
| `order_id` | INTEGER | Laboratory order to which this measurement belongs. |
| `itemid` | INTEGER | Authored laboratory concept: 1001 Creatinine (mg/dL), 1002 Sodium (mmol/L), 1003 Hemoglobin (g/dL). Not original MIMIC codes. |
| `charttime` | TEXT | Time when the specimen used for this laboratory measurement was collected. This column does not store measurement execution time. |
| `storetime` | TEXT | Time when this laboratory result became available in the laboratory system. |
| `valuenum` | REAL | Numeric result recorded for this laboratory measurement. |
| `valueuom` | TEXT | Measurement unit; mg/dL for Creatinine, mmol/L for Sodium, g/dL for Hemoglobin. |

| `emar` | Medication administration or omission records associated with pharmacy dispensing records. | emar_id |

## `emar`

| Column | Type | Business definition |
|---|---|---|
| `emar_id` | INTEGER | Local integer identifier of this administration or omission record; it is not the original MIMIC formatted eMAR identifier. |
| `pharmacy_id` | INTEGER | Dispensing record associated with this administration or omission. |
| `charttime` | TEXT | Time when the administration or omission documented by this dose record occurred. |
| `event_txt` | TEXT | Recorded disposition of this medication dose, indicating administration or omission. |
| `storetime` | TEXT | Time when the dose record was documented in the medication system. |

| `procedure_episode` | Hospital-level procedure execution episodes; the ICU stay_id hierarchy is excluded. | procedureevent_id |

## `procedure_episode`

| Column | Type | Business definition |
|---|---|---|
| `procedureevent_id` | INTEGER | Local synthetic identifier of one procedure execution episode; repeat episodes have separate identifiers. |
| `order_id` | INTEGER | Procedure order executed in this episode. |
| `starttime` | TEXT | Time when this procedure execution episode began. |
| `endtime` | TEXT | Time when this procedure execution episode ended. |
| `storetime` | TEXT | Time when this episode was recorded in the procedure system. |

| `pharmacy` | One distinct dispensing record for a medication prescription; repeated dispensing records can fulfill the same prescription. | pharmacy_id |

## `pharmacy`

| Column | Type | Business definition |
|---|---|---|
| `pharmacy_id` | INTEGER | Identifier of a single pharmacy dispensing record, distinct from prescription and administration identifiers. |
| `order_id` | INTEGER | Medication prescription fulfilled by this dispensing record. |
| `dispensed_at` | TEXT | Time of the individual dispensing represented by this pharmacy record. This is not the first dispensing time for the prescription; each additional dispensing has its own pharmacy_id and row. |

| `transfers` | One patient physical-location interval per record, following the MIMIC-IV transfers table shape. | transfer_id |

## `transfers`

| Column | Type | Business definition |
|---|---|---|
| `subject_id` | INTEGER | Patient whose physical-location history this record describes. |
| `hadm_id` | INTEGER | Hospital admission associated with this location interval. |
| `transfer_id` | INTEGER | Unique location record identifier. |
| `eventtype` | TEXT | ed, admit, transfer or discharge interval type. Only transfer is a distinct transfer activity. |
| `careunit` | TEXT | Care unit occupied during this location interval. |
| `intime` | TEXT | Actual entry time into the recorded care unit. |
| `outtime` | TEXT | Actual departure time from the recorded care unit. |

