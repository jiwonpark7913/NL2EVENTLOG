# MIMIC-IV Demo 2.2 — Data Dictionary

Candidate relationships are not declared PK/FK constraints. Timestamp colors indicate candidates, not Gold events.

Tables: 31 · Rows: 1398500 · Columns: 342

## admissions
Rows: 275

| Column | SQLite type | Temporal class |
|---|---|---|
| subject_id | TEXT | other |
| hadm_id | TEXT | other |
| admittime | TEXT | temporal |
| dischtime | TEXT | temporal |
| deathtime | TEXT | temporal |
| admission_type | TEXT | other |
| admit_provider_id | TEXT | other |
| admission_location | TEXT | other |
| discharge_location | TEXT | other |
| insurance | TEXT | other |
| language | TEXT | other |
| marital_status | TEXT | other |
| race | TEXT | other |
| edregtime | TEXT | temporal |
| edouttime | TEXT | temporal |
| hospital_expire_flag | TEXT | other |

## caregiver
Rows: 15468

| Column | SQLite type | Temporal class |
|---|---|---|
| caregiver_id | TEXT | other |

## chartevents
Rows: 668862

| Column | SQLite type | Temporal class |
|---|---|---|
| subject_id | TEXT | other |
| hadm_id | TEXT | other |
| stay_id | TEXT | other |
| caregiver_id | TEXT | other |
| charttime | TEXT | temporal |
| storetime | TEXT | maintenance |
| itemid | TEXT | other |
| value | TEXT | other |
| valuenum | TEXT | other |
| valueuom | TEXT | other |
| warning | TEXT | other |

## d_hcpcs
Rows: 89200

| Column | SQLite type | Temporal class |
|---|---|---|
| code | TEXT | other |
| category | TEXT | other |
| long_description | TEXT | other |
| short_description | TEXT | other |

## d_icd_diagnoses
Rows: 109775

| Column | SQLite type | Temporal class |
|---|---|---|
| icd_code | TEXT | other |
| icd_version | TEXT | other |
| long_title | TEXT | other |

## d_icd_procedures
Rows: 85257

| Column | SQLite type | Temporal class |
|---|---|---|
| icd_code | TEXT | other |
| icd_version | TEXT | other |
| long_title | TEXT | other |

## d_items
Rows: 4014

| Column | SQLite type | Temporal class |
|---|---|---|
| itemid | TEXT | other |
| label | TEXT | other |
| abbreviation | TEXT | other |
| linksto | TEXT | other |
| category | TEXT | other |
| unitname | TEXT | other |
| param_type | TEXT | other |
| lownormalvalue | TEXT | other |
| highnormalvalue | TEXT | other |

## d_labitems
Rows: 1622

| Column | SQLite type | Temporal class |
|---|---|---|
| itemid | TEXT | other |
| label | TEXT | other |
| fluid | TEXT | other |
| category | TEXT | other |

## datetimeevents
Rows: 15280

| Column | SQLite type | Temporal class |
|---|---|---|
| subject_id | TEXT | other |
| hadm_id | TEXT | other |
| stay_id | TEXT | other |
| caregiver_id | TEXT | other |
| charttime | TEXT | temporal |
| storetime | TEXT | maintenance |
| itemid | TEXT | other |
| value | TEXT | other |
| valueuom | TEXT | other |
| warning | TEXT | other |

## diagnoses_icd
Rows: 4506

| Column | SQLite type | Temporal class |
|---|---|---|
| subject_id | TEXT | other |
| hadm_id | TEXT | other |
| seq_num | TEXT | other |
| icd_code | TEXT | other |
| icd_version | TEXT | other |

## drgcodes
Rows: 454

| Column | SQLite type | Temporal class |
|---|---|---|
| subject_id | TEXT | other |
| hadm_id | TEXT | other |
| drg_type | TEXT | other |
| drg_code | TEXT | other |
| description | TEXT | other |
| drg_severity | TEXT | other |
| drg_mortality | TEXT | other |

## emar
Rows: 35835

| Column | SQLite type | Temporal class |
|---|---|---|
| subject_id | TEXT | other |
| hadm_id | TEXT | other |
| emar_id | TEXT | other |
| emar_seq | TEXT | other |
| poe_id | TEXT | other |
| pharmacy_id | TEXT | other |
| enter_provider_id | TEXT | other |
| charttime | TEXT | temporal |
| medication | TEXT | other |
| event_txt | TEXT | other |
| scheduletime | TEXT | temporal |
| storetime | TEXT | maintenance |

## emar_detail
Rows: 72018

| Column | SQLite type | Temporal class |
|---|---|---|
| subject_id | TEXT | other |
| emar_id | TEXT | other |
| emar_seq | TEXT | other |
| parent_field_ordinal | TEXT | other |
| administration_type | TEXT | other |
| pharmacy_id | TEXT | other |
| barcode_type | TEXT | other |
| reason_for_no_barcode | TEXT | other |
| complete_dose_not_given | TEXT | other |
| dose_due | TEXT | other |
| dose_due_unit | TEXT | other |
| dose_given | TEXT | other |
| dose_given_unit | TEXT | other |
| will_remainder_of_dose_be_given | TEXT | other |
| product_amount_given | TEXT | other |
| product_unit | TEXT | other |
| product_code | TEXT | other |
| product_description | TEXT | other |
| product_description_other | TEXT | other |
| prior_infusion_rate | TEXT | other |
| infusion_rate | TEXT | other |
| infusion_rate_adjustment | TEXT | other |
| infusion_rate_adjustment_amount | TEXT | other |
| infusion_rate_unit | TEXT | other |
| route | TEXT | other |
| infusion_complete | TEXT | other |
| completion_interval | TEXT | other |
| new_iv_bag_hung | TEXT | other |
| continued_infusion_in_other_location | TEXT | other |
| restart_interval | TEXT | other |
| side | TEXT | other |
| site | TEXT | other |
| non_formulary_visual_verification | TEXT | other |

## hcpcsevents
Rows: 61

| Column | SQLite type | Temporal class |
|---|---|---|
| subject_id | TEXT | other |
| hadm_id | TEXT | other |
| chartdate | TEXT | temporal |
| hcpcs_cd | TEXT | other |
| seq_num | TEXT | other |
| short_description | TEXT | other |

## icustays
Rows: 140

| Column | SQLite type | Temporal class |
|---|---|---|
| subject_id | TEXT | other |
| hadm_id | TEXT | other |
| stay_id | TEXT | other |
| first_careunit | TEXT | other |
| last_careunit | TEXT | other |
| intime | TEXT | temporal |
| outtime | TEXT | temporal |
| los | TEXT | other |

## ingredientevents
Rows: 25728

| Column | SQLite type | Temporal class |
|---|---|---|
| subject_id | TEXT | other |
| hadm_id | TEXT | other |
| stay_id | TEXT | other |
| caregiver_id | TEXT | other |
| starttime | TEXT | temporal |
| endtime | TEXT | temporal |
| storetime | TEXT | maintenance |
| itemid | TEXT | other |
| amount | TEXT | other |
| amountuom | TEXT | other |
| rate | TEXT | other |
| rateuom | TEXT | other |
| orderid | TEXT | other |
| linkorderid | TEXT | other |
| statusdescription | TEXT | other |
| originalamount | TEXT | other |
| originalrate | TEXT | other |

## inputevents
Rows: 20404

| Column | SQLite type | Temporal class |
|---|---|---|
| subject_id | TEXT | other |
| hadm_id | TEXT | other |
| stay_id | TEXT | other |
| caregiver_id | TEXT | other |
| starttime | TEXT | temporal |
| endtime | TEXT | temporal |
| storetime | TEXT | maintenance |
| itemid | TEXT | other |
| amount | TEXT | other |
| amountuom | TEXT | other |
| rate | TEXT | other |
| rateuom | TEXT | other |
| orderid | TEXT | other |
| linkorderid | TEXT | other |
| ordercategoryname | TEXT | other |
| secondaryordercategoryname | TEXT | other |
| ordercomponenttypedescription | TEXT | other |
| ordercategorydescription | TEXT | other |
| patientweight | TEXT | other |
| totalamount | TEXT | other |
| totalamountuom | TEXT | other |
| isopenbag | TEXT | other |
| continueinnextdept | TEXT | other |
| statusdescription | TEXT | other |
| originalamount | TEXT | other |
| originalrate | TEXT | other |

## labevents
Rows: 107727

| Column | SQLite type | Temporal class |
|---|---|---|
| labevent_id | TEXT | other |
| subject_id | TEXT | other |
| hadm_id | TEXT | other |
| specimen_id | TEXT | other |
| itemid | TEXT | other |
| order_provider_id | TEXT | other |
| charttime | TEXT | temporal |
| storetime | TEXT | maintenance |
| value | TEXT | other |
| valuenum | TEXT | other |
| valueuom | TEXT | other |
| ref_range_lower | TEXT | other |
| ref_range_upper | TEXT | other |
| flag | TEXT | other |
| priority | TEXT | other |
| comments | TEXT | other |

## microbiologyevents
Rows: 2899

| Column | SQLite type | Temporal class |
|---|---|---|
| microevent_id | TEXT | other |
| subject_id | TEXT | other |
| hadm_id | TEXT | other |
| micro_specimen_id | TEXT | other |
| order_provider_id | TEXT | other |
| chartdate | TEXT | temporal |
| charttime | TEXT | temporal |
| spec_itemid | TEXT | other |
| spec_type_desc | TEXT | other |
| test_seq | TEXT | other |
| storedate | TEXT | temporal |
| storetime | TEXT | maintenance |
| test_itemid | TEXT | other |
| test_name | TEXT | other |
| org_itemid | TEXT | other |
| org_name | TEXT | other |
| isolate_num | TEXT | other |
| quantity | TEXT | other |
| ab_itemid | TEXT | other |
| ab_name | TEXT | other |
| dilution_text | TEXT | other |
| dilution_comparison | TEXT | other |
| dilution_value | TEXT | other |
| interpretation | TEXT | other |
| comments | TEXT | other |

## omr
Rows: 2964

| Column | SQLite type | Temporal class |
|---|---|---|
| subject_id | TEXT | other |
| chartdate | TEXT | temporal |
| seq_num | TEXT | other |
| result_name | TEXT | other |
| result_value | TEXT | other |

## outputevents
Rows: 9362

| Column | SQLite type | Temporal class |
|---|---|---|
| subject_id | TEXT | other |
| hadm_id | TEXT | other |
| stay_id | TEXT | other |
| caregiver_id | TEXT | other |
| charttime | TEXT | temporal |
| storetime | TEXT | maintenance |
| itemid | TEXT | other |
| value | TEXT | other |
| valueuom | TEXT | other |

## patients
Rows: 100

| Column | SQLite type | Temporal class |
|---|---|---|
| subject_id | TEXT | other |
| gender | TEXT | other |
| anchor_age | TEXT | other |
| anchor_year | TEXT | other |
| anchor_year_group | TEXT | other |
| dod | TEXT | temporal |

## pharmacy
Rows: 15306

| Column | SQLite type | Temporal class |
|---|---|---|
| subject_id | TEXT | other |
| hadm_id | TEXT | other |
| pharmacy_id | TEXT | other |
| poe_id | TEXT | other |
| starttime | TEXT | temporal |
| stoptime | TEXT | temporal |
| medication | TEXT | other |
| proc_type | TEXT | other |
| status | TEXT | other |
| entertime | TEXT | temporal |
| verifiedtime | TEXT | temporal |
| route | TEXT | other |
| frequency | TEXT | other |
| disp_sched | TEXT | other |
| infusion_type | TEXT | other |
| sliding_scale | TEXT | other |
| lockout_interval | TEXT | other |
| basal_rate | TEXT | other |
| one_hr_max | TEXT | other |
| doses_per_24_hrs | TEXT | other |
| duration | TEXT | other |
| duration_interval | TEXT | other |
| expiration_value | TEXT | other |
| expiration_unit | TEXT | other |
| expirationdate | TEXT | temporal |
| dispensation | TEXT | other |
| fill_quantity | TEXT | other |

## poe
Rows: 45154

| Column | SQLite type | Temporal class |
|---|---|---|
| poe_id | TEXT | other |
| poe_seq | TEXT | other |
| subject_id | TEXT | other |
| hadm_id | TEXT | other |
| ordertime | TEXT | temporal |
| order_type | TEXT | other |
| order_subtype | TEXT | other |
| transaction_type | TEXT | other |
| discontinue_of_poe_id | TEXT | other |
| discontinued_by_poe_id | TEXT | other |
| order_provider_id | TEXT | other |
| order_status | TEXT | other |

## poe_detail
Rows: 3795

| Column | SQLite type | Temporal class |
|---|---|---|
| poe_id | TEXT | other |
| poe_seq | TEXT | other |
| subject_id | TEXT | other |
| field_name | TEXT | other |
| field_value | TEXT | other |

## prescriptions
Rows: 18087

| Column | SQLite type | Temporal class |
|---|---|---|
| subject_id | TEXT | other |
| hadm_id | TEXT | other |
| pharmacy_id | TEXT | other |
| poe_id | TEXT | other |
| poe_seq | TEXT | other |
| order_provider_id | TEXT | other |
| starttime | TEXT | temporal |
| stoptime | TEXT | temporal |
| drug_type | TEXT | other |
| drug | TEXT | other |
| formulary_drug_cd | TEXT | other |
| gsn | TEXT | other |
| ndc | TEXT | other |
| prod_strength | TEXT | other |
| form_rx | TEXT | other |
| dose_val_rx | TEXT | other |
| dose_unit_rx | TEXT | other |
| form_val_disp | TEXT | other |
| form_unit_disp | TEXT | other |
| doses_per_24_hrs | TEXT | other |
| route | TEXT | other |

## procedureevents
Rows: 1468

| Column | SQLite type | Temporal class |
|---|---|---|
| subject_id | TEXT | other |
| hadm_id | TEXT | other |
| stay_id | TEXT | other |
| caregiver_id | TEXT | other |
| starttime | TEXT | temporal |
| endtime | TEXT | temporal |
| storetime | TEXT | maintenance |
| itemid | TEXT | other |
| value | TEXT | other |
| valueuom | TEXT | other |
| location | TEXT | other |
| locationcategory | TEXT | other |
| orderid | TEXT | other |
| linkorderid | TEXT | other |
| ordercategoryname | TEXT | other |
| ordercategorydescription | TEXT | other |
| patientweight | TEXT | other |
| isopenbag | TEXT | other |
| continueinnextdept | TEXT | other |
| statusdescription | TEXT | other |
| ORIGINALAMOUNT | TEXT | other |
| ORIGINALRATE | TEXT | other |

## procedures_icd
Rows: 722

| Column | SQLite type | Temporal class |
|---|---|---|
| subject_id | TEXT | other |
| hadm_id | TEXT | other |
| seq_num | TEXT | other |
| chartdate | TEXT | temporal |
| icd_code | TEXT | other |
| icd_version | TEXT | other |

## provider
Rows: 40508

| Column | SQLite type | Temporal class |
|---|---|---|
| provider_id | TEXT | other |

## services
Rows: 319

| Column | SQLite type | Temporal class |
|---|---|---|
| subject_id | TEXT | other |
| hadm_id | TEXT | other |
| transfertime | TEXT | temporal |
| prev_service | TEXT | other |
| curr_service | TEXT | other |

## transfers
Rows: 1190

| Column | SQLite type | Temporal class |
|---|---|---|
| subject_id | TEXT | other |
| hadm_id | TEXT | other |
| transfer_id | TEXT | other |
| eventtype | TEXT | other |
| careunit | TEXT | other |
| intime | TEXT | temporal |
| outtime | TEXT | temporal |

