# MIMIC-IV Demo 2.2 — Data Dictionary

Source: [MIMIC-IV official documentation](https://mimic.mit.edu/docs/iv/) · [MIMIC-IV Demo 2.2](https://physionet.org/content/mimic-iv-demo/2.2/)

Column descriptions and native types come from the linked official table pages. Unknown descriptions are left blank; inferred links are not declared FKs.

## admissions

Official table documentation: [https://mimic.mit.edu/docs/iv/modules/hosp/admissions.html](https://mimic.mit.edu/docs/iv/modules/hosp/admissions.html)

The admissions table defines all hospitalizations in the database. Hospitalizations are assigned a unique random integer known as the hadm_id .

| Column | Native type | SQLite type | Description |
|---|---|---|---|
| `subject_id` | INTEGER NOT NULL | TEXT | Each row of this table contains a unique hadm_id , which represents a single patient’s admission to the hospital. hadm_id ranges from 2000000 - 2999999. It is possible for this table to have duplicate subject_id , indicating that a single patient had multiple admissions to the hospital. The ADMISSIONS table can be linked to the PATIENTS table using subject_id . |
| `hadm_id` | INTEGER NOT NULL | TEXT | Each row of this table contains a unique hadm_id , which represents a single patient’s admission to the hospital. hadm_id ranges from 2000000 - 2999999. It is possible for this table to have duplicate subject_id , indicating that a single patient had multiple admissions to the hospital. The ADMISSIONS table can be linked to the PATIENTS table using subject_id . |
| `admittime` | TIMESTAMP NOT NULL | TEXT | admittime provides the date and time the patient was admitted to the hospital, while dischtime provides the date and time the patient was discharged from the hospital. If applicable, deathtime provides the time of in-hospital death for the patient. Note that deathtime is only present if the patient died in-hospital, and is almost always the same as the patient’s dischtime . However, there can be some discrepancies due to typographical errors. |
| `dischtime` | TIMESTAMP | TEXT | admittime provides the date and time the patient was admitted to the hospital, while dischtime provides the date and time the patient was discharged from the hospital. If applicable, deathtime provides the time of in-hospital death for the patient. Note that deathtime is only present if the patient died in-hospital, and is almost always the same as the patient’s dischtime . However, there can be some discrepancies due to typographical errors. |
| `deathtime` | TIMESTAMP | TEXT | admittime provides the date and time the patient was admitted to the hospital, while dischtime provides the date and time the patient was discharged from the hospital. If applicable, deathtime provides the time of in-hospital death for the patient. Note that deathtime is only present if the patient died in-hospital, and is almost always the same as the patient’s dischtime . However, there can be some discrepancies due to typographical errors. |
| `admission_type` | VARCHAR(40) NOT NULL | TEXT | admission_type is useful for classifying the urgency of the admission. There are 9 possibilities: ‘AMBULATORY OBSERVATION’, ‘DIRECT EMER.’, ‘DIRECT OBSERVATION’, ‘ELECTIVE’, ‘EU OBSERVATION’, ‘EW EMER.’, ‘OBSERVATION ADMIT’, ‘SURGICAL SAME DAY ADMISSION’, ‘URGENT’. |
| `admit_provider_id` | VARCHAR(10) | TEXT | admit_provider_id provides an anonymous identifier for the provider who admitted the patient. Provider identifiers follow a consistent pattern: the letter “P”, followed by either three numbers, followed by two letters or two numbers. For example, “P003AB”, “P00102”, “P1248B”, etc. Provider identifiers are randomly generated and do not have any inherent meaning aside from uniquely identifying the same provider across the database. |
| `admission_location` | VARCHAR(60) | TEXT | admission_location provides information about the location of the patient prior to arriving at the hospital. Note that as the emergency room is technically a clinic, patients who are admitted via the emergency room usually have it as their admission location. Similarly, discharge_location is the disposition of the patient after they are discharged from the hospital. |
| `discharge_location` | VARCHAR(60) | TEXT | admission_location provides information about the location of the patient prior to arriving at the hospital. Note that as the emergency room is technically a clinic, patients who are admitted via the emergency room usually have it as their admission location. Similarly, discharge_location is the disposition of the patient after they are discharged from the hospital. |
| `insurance` | VARCHAR(255) | TEXT | The insurance , language , marital_status , and ethnicity columns provide information about patient demographics for the given hospitalization. Note that as this data is documented for each hospital admission, they may change from stay to stay. |
| `language` | VARCHAR(10) | TEXT | The insurance , language , marital_status , and ethnicity columns provide information about patient demographics for the given hospitalization. Note that as this data is documented for each hospital admission, they may change from stay to stay. |
| `marital_status` | VARCHAR(30) | TEXT | The insurance , language , marital_status , and ethnicity columns provide information about patient demographics for the given hospitalization. Note that as this data is documented for each hospital admission, they may change from stay to stay. |
| `race` | VARCHAR(80) | TEXT | *Not documented / not reliably matched* |
| `edregtime` | TIMESTAMP | TEXT | The date and time at which the patient was registered and discharged from the emergency department. |
| `edouttime` | TIMESTAMP | TEXT | The date and time at which the patient was registered and discharged from the emergency department. |
| `hospital_expire_flag` | SMALLINT | TEXT | This is a binary flag which indicates whether the patient died within the given hospitalization. 1 indicates death in the hospital, and 0 indicates survival to hospital discharge. |

## caregiver

Official table documentation: [https://mimic.mit.edu/docs/iv/modules/icu/caregiver.html](https://mimic.mit.edu/docs/iv/modules/icu/caregiver.html)

*No verified table summary*

| Column | Native type | SQLite type | Description |
|---|---|---|---|
| `caregiver_id` | VARCHAR(10) NOT NULL | TEXT | caregiver_id lists all possible identifiers for caregivers used in the ICU module. caregiver_id uniquely identifies a single caregiver who documented data in the ICU information system. |

## chartevents

Official table documentation: [https://mimic.mit.edu/docs/iv/modules/icu/chartevents.html](https://mimic.mit.edu/docs/iv/modules/icu/chartevents.html)

*No verified table summary*

| Column | Native type | SQLite type | Description |
|---|---|---|---|
| `subject_id` | INTEGER | TEXT | Identifiers which specify the patient: subject_id is unique to a patient, hadm_id is unique to a patient hospital stay and stay_id is unique to a patient ward stay. More information about these identifiers is available here . |
| `hadm_id` | INTEGER | TEXT | Identifiers which specify the patient: subject_id is unique to a patient, hadm_id is unique to a patient hospital stay and stay_id is unique to a patient ward stay. More information about these identifiers is available here . |
| `stay_id` | INTEGER | TEXT | Identifiers which specify the patient: subject_id is unique to a patient, hadm_id is unique to a patient hospital stay and stay_id is unique to a patient ward stay. More information about these identifiers is available here . |
| `caregiver_id` | INTEGER | TEXT | caregiver_id uniquely identifies a single caregiver who documented data in the ICU information system. |
| `charttime` | TIMESTAMP(0) | TEXT | charttime records the time at which an observation was made, and is usually the closest proxy to the time the data was actually measured. storetime records the time at which an observation was manually input or manually validated by a member of the clinical staff. |
| `storetime` | TIMESTAMP(0) | TEXT | charttime records the time at which an observation was made, and is usually the closest proxy to the time the data was actually measured. storetime records the time at which an observation was manually input or manually validated by a member of the clinical staff. |
| `itemid` | INTEGER | TEXT | Identifier for a single measurement type in the database. Each row associated with one itemid (e.g. 220045) corresponds to an instantiation of the same measurement (e.g. heart rate). |
| `value` | VARCHAR(200) | TEXT | value contains the value measured for the concept identified by the itemid . If this value is numeric, then valuenum contains the same data in a numeric format. If this data is not numeric, valuenum is null. In some cases (e.g. scores like Glasgow Coma Scale, Richmond Sedation Agitation Scale and Code Status), valuenum contains the score and value contains the score and text describing the meaning of the score. |
| `valuenum` | DOUBLE PRECISION | TEXT | value contains the value measured for the concept identified by the itemid . If this value is numeric, then valuenum contains the same data in a numeric format. If this data is not numeric, valuenum is null. In some cases (e.g. scores like Glasgow Coma Scale, Richmond Sedation Agitation Scale and Code Status), valuenum contains the score and value contains the score and text describing the meaning of the score. |
| `valueuom` | VARCHAR(20) | TEXT | valueuom is the unit of measurement for the value , if appropriate. |
| `warning` | SMALLINT | TEXT | warning specifies if a warning for this observation was manually documented by the care provider. |

## d_hcpcs

Official table documentation: [https://mimic.mit.edu/docs/iv/modules/hosp/d_hcpcs.html](https://mimic.mit.edu/docs/iv/modules/hosp/d_hcpcs.html)

*No verified table summary*

| Column | Native type | SQLite type | Description |
|---|---|---|---|
| `code` | CHAR(5) NOT NULL | TEXT | A five character code which uniquely represents the event. |
| `category` | SMALLINT | TEXT | Broad classification of the code. |
| `long_description` | TEXT | TEXT | Textual descriptions of the code listed for the given row. |
| `short_description` | VARCHAR(180) | TEXT | Textual descriptions of the code listed for the given row. |

## d_icd_diagnoses

Official table documentation: [https://mimic.mit.edu/docs/iv/modules/hosp/d_icd_diagnoses.html](https://mimic.mit.edu/docs/iv/modules/hosp/d_icd_diagnoses.html)

*No verified table summary*

| Column | Native type | SQLite type | Description |
|---|---|---|---|
| `icd_code` | CHAR(7) NOT NULL | TEXT | icd_code is the International Coding Definitions (ICD) code. There are two versions for this coding system: version 9 (ICD-9) and version 10 (ICD-10). These can be differentiated using the icd_version column. In general, ICD-10 codes are more detailed, though code mappings (or “cross-walks”) exist which convert ICD-9 codes to ICD-10 codes. Both ICD-9 and ICD-10 codes are often presented with a decimal. This decimal is not required for interpretation of an ICD code; i.e. the icd_code of ‘0010’ is equivalent to ‘001.0’. ICD-9 and ICD-10 codes have distinct formats: ICD-9 codes are 5 character long strings which are entirely numeric (with the exception of codes prefixed with “E” or “V” which are used for external  |
| `icd_version` | INTEGER NOT NULL | TEXT | icd_code is the International Coding Definitions (ICD) code. There are two versions for this coding system: version 9 (ICD-9) and version 10 (ICD-10). These can be differentiated using the icd_version column. In general, ICD-10 codes are more detailed, though code mappings (or “cross-walks”) exist which convert ICD-9 codes to ICD-10 codes. Both ICD-9 and ICD-10 codes are often presented with a decimal. This decimal is not required for interpretation of an ICD code; i.e. the icd_code of ‘0010’ is equivalent to ‘001.0’. ICD-9 and ICD-10 codes have distinct formats: ICD-9 codes are 5 character long strings which are entirely numeric (with the exception of codes prefixed with “E” or “V” which are used for external  |
| `long_title` | VARCHAR(255) | TEXT | The long_title provides the meaning of the ICD code. For example, the ICD-9 code 0010 has long_title “Cholera due to vibrio cholerae”. |

## d_icd_procedures

Official table documentation: [https://mimic.mit.edu/docs/iv/modules/hosp/d_icd_procedures.html](https://mimic.mit.edu/docs/iv/modules/hosp/d_icd_procedures.html)

*No verified table summary*

| Column | Native type | SQLite type | Description |
|---|---|---|---|
| `icd_code` | CHAR(7) NOT NULL | TEXT | icd_code is the International Coding Definitions (ICD) code. There are two versions for this coding system: version 9 (ICD-9) and version 10 (ICD-10). These can be differentiated using the icd_version column. In general, ICD-10 codes are more detailed, though code mappings (or “cross-walks”) exist which convert ICD-9 codes to ICD-10 codes. Both ICD-9 and ICD-10 codes are often presented with a decimal. This decimal is not required for interpretation of an ICD code; i.e. the icd_code of ‘0010’ is equivalent to ‘001.0’. |
| `icd_version` | INTEGER NOT NULL | TEXT | icd_code is the International Coding Definitions (ICD) code. There are two versions for this coding system: version 9 (ICD-9) and version 10 (ICD-10). These can be differentiated using the icd_version column. In general, ICD-10 codes are more detailed, though code mappings (or “cross-walks”) exist which convert ICD-9 codes to ICD-10 codes. Both ICD-9 and ICD-10 codes are often presented with a decimal. This decimal is not required for interpretation of an ICD code; i.e. the icd_code of ‘0010’ is equivalent to ‘001.0’. |
| `long_title` | VARCHAR(255) | TEXT | The title fields provide a brief definition for the given procedure code in ``. |

## d_items

Official table documentation: [https://mimic.mit.edu/docs/iv/modules/icu/d_items.html](https://mimic.mit.edu/docs/iv/modules/icu/d_items.html)

*No verified table summary*

| Column | Native type | SQLite type | Description |
|---|---|---|---|
| `itemid` | INTEGER | TEXT | As an alternate primary key to the table, itemid is unique to each row. |
| `label` | VARCHAR(200) | TEXT | The label column describes the concept which is represented by the itemid . The abbreviation column, only available in Metavision, lists a common abbreviation for the label. |
| `abbreviation` | VARCHAR(100) | TEXT | The label column describes the concept which is represented by the itemid . The abbreviation column, only available in Metavision, lists a common abbreviation for the label. |
| `linksto` | VARCHAR(50) | TEXT | linksto provides the table name which the data links to. For example, a value of ‘chartevents’ indicates that the itemid of the given row is contained in CHARTEVENTS. A single itemid is only used in one event table, that is, if an itemid is contained in CHARTEVENTS it will not be contained in any other event table (e.g. IOEVENTS, CHARTEVENTS, etc). |
| `category` | VARCHAR(100) | TEXT | category provides some information of the type of data the itemid corresponds to. Examples include ‘ABG’, which indicates the measurement is sourced from an arterial blood gas, ‘IV Medication’, which indicates that the medication is administered through an intravenous line, and so on. |
| `unitname` | VARCHAR(100) | TEXT | unitname specifies the unit of measurement used for the itemid . This column is not always available, and this may be because the unit of measurement varies, a unit of measurement does not make sense for the given data type, or the unit of measurement is simply missing. Note that there is sometimes additional information on the unit of measurement in the associated event table, e.g. the valueuom column in CHARTEVENTS. |
| `param_type` | VARCHAR(30) | TEXT | param_type describes the type of data which is recorded: a date, a number or a text field. |
| `lownormalvalue` | FLOAT | TEXT | These columns store reference ranges for the measurement. Note that a reference range encompasses the expected value of a measurement: values outside of this may still be physiologically plausible, but are considered unusual. |
| `highnormalvalue` | FLOAT | TEXT | These columns store reference ranges for the measurement. Note that a reference range encompasses the expected value of a measurement: values outside of this may still be physiologically plausible, but are considered unusual. |

## d_labitems

Official table documentation: [https://mimic.mit.edu/docs/iv/modules/hosp/d_labitems.html](https://mimic.mit.edu/docs/iv/modules/hosp/d_labitems.html)

*No verified table summary*

| Column | Native type | SQLite type | Description |
|---|---|---|---|
| `itemid` | INTEGER | TEXT | A unique identifier for a laboratory concept. itemid is unique to each row, and can be used to identify data in labevents associated with a specific concept. |
| `label` | VARCHAR(50) | TEXT | The label column describes the concept which is represented by the itemid . |
| `fluid` | VARCHAR(50) | TEXT | fluid describes the substance on which the measurement was made. For example, chemistry measurements are frequently performed on blood, which is listed in this column as ‘BLOOD’. Many of these measurements are also acquirable on other fluids, such as urine, and this column differentiates these distinct concepts. |
| `category` | VARCHAR(50) | TEXT | category provides higher level information as to the type of measurement. For example, a category of ‘ABG’ indicates that the measurement is an arterial blood gas. |

## datetimeevents

Official table documentation: [https://mimic.mit.edu/docs/iv/modules/icu/datetimesevents.html](https://mimic.mit.edu/docs/iv/modules/icu/datetimesevents.html)

*No verified table summary*

| Column | Native type | SQLite type | Description |
|---|---|---|---|
| `subject_id` | INTEGER | TEXT | Identifiers which specify the patient: subject_id is unique to a patient, hadm_id is unique to a patient hospital stay and stay_id is unique to a patient ward stay. |
| `hadm_id` | INTEGER | TEXT | Identifiers which specify the patient: subject_id is unique to a patient, hadm_id is unique to a patient hospital stay and stay_id is unique to a patient ward stay. |
| `stay_id` | INTEGER | TEXT | Identifiers which specify the patient: subject_id is unique to a patient, hadm_id is unique to a patient hospital stay and stay_id is unique to a patient ward stay. |
| `caregiver_id` | INTEGER | TEXT | caregiver_id uniquely identifies a single caregiver who documented data in the ICU information system. |
| `charttime` | TIMESTAMP(3) | TEXT | charttime records the time at which an observation was charted, and is usually the closest proxy to the time the data was actually measured. storetime records the time at which an observation was manually input or manually validated by a member of the clinical staff. |
| `storetime` | TIMESTAMP(3) | TEXT | charttime records the time at which an observation was charted, and is usually the closest proxy to the time the data was actually measured. storetime records the time at which an observation was manually input or manually validated by a member of the clinical staff. |
| `itemid` | INTEGER | TEXT | Identifier for a single measurement type in the database. Each row associated with one itemid (e.g. 212) corresponds to an instantiation of the same measurement (e.g. heart rate). |
| `value` | TIMESTAMP(3) | TEXT | The documented date - this is the value that corresponds to the concept referred to by itemid . For example, if querying for itemid : 225755 (“18 Gauge Insertion Date”), then the value column indicates the date the line was inserted. |
| `valueuom` | VARCHAR(20) | TEXT | The unit of measurement for the value - almost always the text string “Date”. |
| `warning` | SMALLINT | TEXT | warning specifies if a warning for this observation was manually documented by the care provider. |

## diagnoses_icd

Official table documentation: [https://mimic.mit.edu/docs/iv/modules/hosp/diagnoses_icd.html](https://mimic.mit.edu/docs/iv/modules/hosp/diagnoses_icd.html)

*No verified table summary*

| Column | Native type | SQLite type | Description |
|---|---|---|---|
| `subject_id` | INTEGER NOT NULL | TEXT | subject_id is a unique identifier which specifies an individual patient. Any rows associated with a single subject_id pertain to the same individual. |
| `hadm_id` | INTEGER NOT NULL | TEXT | hadm_id is an integer identifier which is unique for each patient hospitalization. |
| `seq_num` | INTEGER NOT NULL | TEXT | The priority assigned to the diagnoses. The priority can be interpreted as a ranking of which diagnoses are “important”, but many caveats to this broad statement exist. For example, patients who are diagnosed with sepsis must have sepsis as their 2nd billed condition. The 1st billed condition must be the infectious agent. There’s also less importance placed on ranking low priority diagnoses “correctly” (as there may be no correct ordering of the priority of the 5th - 10th diagnosis codes, for example). |
| `icd_code` | VARCHAR(7) | TEXT | icd_code is the International Coding Definitions (ICD) code. There are two versions for this coding system: version 9 (ICD-9) and version 10 (ICD-10). These can be differentiated using the icd_version column. In general, ICD-10 codes are more detailed, though code mappings (or “cross-walks”) exist which convert ICD-9 codes to ICD-10 codes. Both ICD-9 and ICD-10 codes are often presented with a decimal. This decimal is not required for interpretation of an ICD code; i.e. the icd_code of ‘0010’ is equivalent to ‘001.0’. |
| `icd_version` | INTEGER | TEXT | icd_code is the International Coding Definitions (ICD) code. There are two versions for this coding system: version 9 (ICD-9) and version 10 (ICD-10). These can be differentiated using the icd_version column. In general, ICD-10 codes are more detailed, though code mappings (or “cross-walks”) exist which convert ICD-9 codes to ICD-10 codes. Both ICD-9 and ICD-10 codes are often presented with a decimal. This decimal is not required for interpretation of an ICD code; i.e. the icd_code of ‘0010’ is equivalent to ‘001.0’. |

## drgcodes

Official table documentation: [https://mimic.mit.edu/docs/iv/modules/hosp/drgcodes.html](https://mimic.mit.edu/docs/iv/modules/hosp/drgcodes.html)

*No verified table summary*

| Column | Native type | SQLite type | Description |
|---|---|---|---|
| `subject_id` | INTEGER | TEXT | subject_id is a unique identifier which specifies an individual patient. Any rows associated with a single subject_id pertain to the same individual. |
| `hadm_id` | INTEGER | TEXT | hadm_id is an integer identifier which is unique for each patient hospitalization. |
| `drg_type` | VARCHAR(4) | TEXT | The specific DRG ontology used for the code. |
| `drg_code` | VARCHAR(10) | TEXT | The DRG code. |
| `description` | VARCHAR(195) | TEXT | A description for the given DRG code. |
| `drg_severity` | SMALLINT | TEXT | Some DRG ontologies further qualify the patient severity of illness and likelihood of mortality, which are recorded here. |
| `drg_mortality` | SMALLINT | TEXT | Some DRG ontologies further qualify the patient severity of illness and likelihood of mortality, which are recorded here. |

## emar

Official table documentation: [https://mimic.mit.edu/docs/iv/modules/hosp/emar.html](https://mimic.mit.edu/docs/iv/modules/hosp/emar.html)

*No verified table summary*

| Column | Native type | SQLite type | Description |
|---|---|---|---|
| `subject_id` | INTEGER NOT NULL | TEXT | subject_id is a unique identifier which specifies an individual patient. Any rows associated with a single subject_id pertain to the same individual. |
| `hadm_id` | INTEGER | TEXT | hadm_id is an integer identifier which is unique for each patient hospitalization. |
| `emar_id` | VARCHAR(25) NOT NULL | TEXT | Identifiers for the eMAR table. emar_id is a unique identifier for each order made in eMAR. emar_seq is a consecutive integer which numbers eMAR orders chronologically. emar_id is composed of subject_id and emar_seq in the following pattern: ‘ subject_id - emar_seq ’. |
| `emar_seq` | INTEGER NOT NULL | TEXT | Identifiers for the eMAR table. emar_id is a unique identifier for each order made in eMAR. emar_seq is a consecutive integer which numbers eMAR orders chronologically. emar_id is composed of subject_id and emar_seq in the following pattern: ‘ subject_id - emar_seq ’. |
| `poe_id` | VARCHAR(25) NOT NULL | TEXT | An identifier which links administrations in emar to orders in poe and prescriptions . |
| `pharmacy_id` | INTEGER | TEXT | An identifier which links administrations in emar to pharmacy information in the pharmacy table. |
| `enter_provider_id` | VARCHAR(10) | TEXT | enter_provider_id provides an anonymous identifier for the provider who entered the information into the eMAR system. Provider identifiers follow a consistent pattern: the letter “P”, followed by either three numbers, followed by two letters or two numbers. For example, “P003AB”, “P00102”, “P1248B”, etc. Provider identifiers are randomly generated and do not have any inherent meaning aside from uniquely identifying the same provider across the database. |
| `charttime` | TIMESTAMP NOT NULL | TEXT | The time at which the medication was administered. |
| `medication` | TEXT | TEXT | The name of the medication which was administered. |
| `event_txt` | VARCHAR(100) | TEXT | Information about the administration. Most frequently event_txt is ‘Administered’, but other possible values are ‘Applied’, ‘Confirmed’, ‘Delayed’, ‘Not Given’, and so on. |
| `scheduletime` | TIMESTAMP | TEXT | If present, the time at which the administration was scheduled. |
| `storetime` | TIMESTAMP NOT NULL | TEXT | The time at which the administration was documented in the eMAR table. |

## emar_detail

Official table documentation: [https://mimic.mit.edu/docs/iv/modules/hosp/emar_detail.html](https://mimic.mit.edu/docs/iv/modules/hosp/emar_detail.html)

*No verified table summary*

| Column | Native type | SQLite type | Description |
|---|---|---|---|
| `subject_id` | INTEGER NOT NULL | TEXT | subject_id is a unique identifier which specifies an individual patient. Any rows associated with a single subject_id pertain to the same individual. |
| `emar_id` | VARCHAR(25) NOT NULL | TEXT | Identifiers for the eMAR table. emar_id is a unique identifier for each order made in eMAR. emar_seq is a consecutive integer which numbers eMAR orders chronologically. emar_id is composed of subject_id and emar_seq in the following pattern: ‘ subject_id - emar_seq ’. |
| `emar_seq` | INTEGER NOT NULL | TEXT | Identifiers for the eMAR table. emar_id is a unique identifier for each order made in eMAR. emar_seq is a consecutive integer which numbers eMAR orders chronologically. emar_id is composed of subject_id and emar_seq in the following pattern: ‘ subject_id - emar_seq ’. |
| `parent_field_ordinal` | VARCHAR(10) | TEXT | parent_field_ordinal delineates multiple administrations for the same eMar event, e.g. multiple formulary doses for the full dose. As eMAR requires the administrating provider to scan a barcode for each formulary provided to the patient, it is often the case that multiple rows in emar_detail correspond to a single row in emar (e.g. multiple pills are administered which add up to the desired dose). The structure for emar_detail rows is as follows: There is one row per eMAR order with a NULL parent_field_ordinal : this row usually contains the desired dose for the administration. Afterward, if there are N formulary doses, parent_field_ordinal will take values ‘1.1’, ‘1.2’, …, ‘1.N’. The most common case occurs wh |
| `administration_type` | VARCHAR(50) | TEXT | The type of administration, including ‘IV Bolus’, ‘IV Infusion’, ‘Medication Infusion’, ‘Transdermal Patch’, and so on. |
| `pharmacy_id` | INTEGER | TEXT | An identifier which allows linking the eMAR order to pharmacy information provided in the pharmacy table. Note: rarely the same emar_id may have multiple distinct pharmacy_id across rows in the emar_detail table. |
| `barcode_type` | VARCHAR(4) | TEXT | *Not documented / not reliably matched* |
| `reason_for_no_barcode` | TEXT | TEXT | *Not documented / not reliably matched* |
| `complete_dose_not_given` | VARCHAR(5) | TEXT | *Not documented / not reliably matched* |
| `dose_due` | VARCHAR(100) | TEXT | *Not documented / not reliably matched* |
| `dose_due_unit` | VARCHAR(50) | TEXT | *Not documented / not reliably matched* |
| `dose_given` | VARCHAR(255) | TEXT | *Not documented / not reliably matched* |
| `dose_given_unit` | VARCHAR(50) | TEXT | *Not documented / not reliably matched* |
| `will_remainder_of_dose_be_given` | VARCHAR(5) | TEXT | *Not documented / not reliably matched* |
| `product_amount_given` | VARCHAR(30) | TEXT | *Not documented / not reliably matched* |
| `product_unit` | VARCHAR(30) | TEXT | *Not documented / not reliably matched* |
| `product_code` | VARCHAR(30) | TEXT | *Not documented / not reliably matched* |
| `product_description` | VARCHAR(255) | TEXT | *Not documented / not reliably matched* |
| `product_description_other` | VARCHAR(255) | TEXT | *Not documented / not reliably matched* |
| `prior_infusion_rate` | VARCHAR(40) | TEXT | *Not documented / not reliably matched* |
| `infusion_rate` | VARCHAR(40) | TEXT | *Not documented / not reliably matched* |
| `infusion_rate_adjustment` | VARCHAR(50) | TEXT | *Not documented / not reliably matched* |
| `infusion_rate_adjustment_amount` | VARCHAR(30) | TEXT | *Not documented / not reliably matched* |
| `infusion_rate_unit` | VARCHAR(30) | TEXT | *Not documented / not reliably matched* |
| `route` | VARCHAR(10) | TEXT | *Not documented / not reliably matched* |
| `infusion_complete` | VARCHAR(1) | TEXT | *Not documented / not reliably matched* |
| `completion_interval` | VARCHAR(50) | TEXT | *Not documented / not reliably matched* |
| `new_iv_bag_hung` | VARCHAR(1) | TEXT | *Not documented / not reliably matched* |
| `continued_infusion_in_other_location` | VARCHAR(1) | TEXT | *Not documented / not reliably matched* |
| `restart_interval` | TEXT | TEXT | *Not documented / not reliably matched* |
| `side` | VARCHAR(10) | TEXT | *Not documented / not reliably matched* |
| `site` | VARCHAR(255) | TEXT | *Not documented / not reliably matched* |
| `non_formulary_visual_verification` | VARCHAR(1) | TEXT | *Not documented / not reliably matched* |

## hcpcsevents

Official table documentation: [https://mimic.mit.edu/docs/iv/modules/hosp/hcpcsevents.html](https://mimic.mit.edu/docs/iv/modules/hosp/hcpcsevents.html)

*No verified table summary*

| Column | Native type | SQLite type | Description |
|---|---|---|---|
| `subject_id` | INTEGER NOT NULL | TEXT | subject_id is a unique identifier which specifies an individual patient. Any rows associated with a single subject_id pertain to the same individual. |
| `hadm_id` | INTEGER NOT NULL | TEXT | hadm_id is an integer identifier which is unique for each patient hospitalization. |
| `chartdate` | DATE | TEXT | The date associated with the coded event. |
| `hcpcs_cd` | CHAR(5) NOT NULL | TEXT | A five character code which uniquely represents the event. Link this to code in d_hcpcs for a longer description of the code. |
| `seq_num` | INTEGER NOT NULL | TEXT | An assigned order to HCPCS codes for an individual hospitalization. This order sometimes conveys meaning, e.g. sometimes higher priority, but this is not guaranteed across all codes. |
| `short_description` | VARCHAR(180) | TEXT | A short textual descriptions of the hcpcs_cd listed for the given row. |

## icustays

Official table documentation: [https://mimic.mit.edu/docs/iv/modules/icu/icustays.html](https://mimic.mit.edu/docs/iv/modules/icu/icustays.html)

*No verified table summary*

| Column | Native type | SQLite type | Description |
|---|---|---|---|
| `subject_id` | INT | TEXT | Identifiers which specify the patient: subject_id is unique to a patient, hadm_id is unique to a patient hospital stay and stay_id is unique to a patient ward stay. |
| `hadm_id` | INT | TEXT | Identifiers which specify the patient: subject_id is unique to a patient, hadm_id is unique to a patient hospital stay and stay_id is unique to a patient ward stay. |
| `stay_id` | INT | TEXT | Identifiers which specify the patient: subject_id is unique to a patient, hadm_id is unique to a patient hospital stay and stay_id is unique to a patient ward stay. |
| `first_careunit` | VARCHAR(20) | TEXT | FIRST_CAREUNIT and LAST_CAREUNIT contain, respectively, the first and last ICU type in which the patient was cared for. As an stay_id groups all ICU admissions within 24 hours of each other, it is possible for a patient to be transferred from one type of ICU to another and have the same stay_id . Care units are derived from the TRANSFERS table, and definition for the abbreviations can be found in the documentation for TRANSFERS. |
| `last_careunit` | VARCHAR(20) | TEXT | FIRST_CAREUNIT and LAST_CAREUNIT contain, respectively, the first and last ICU type in which the patient was cared for. As an stay_id groups all ICU admissions within 24 hours of each other, it is possible for a patient to be transferred from one type of ICU to another and have the same stay_id . Care units are derived from the TRANSFERS table, and definition for the abbreviations can be found in the documentation for TRANSFERS. |
| `intime` | TIMESTAMP(0) | TEXT | INTIME provides the date and time the patient was transferred into the ICU. OUTTIME provides the date and time the patient was transferred out of the ICU. |
| `outtime` | TIMESTAMP(0) | TEXT | INTIME provides the date and time the patient was transferred into the ICU. OUTTIME provides the date and time the patient was transferred out of the ICU. |
| `los` | DOUBLE PRECISION | TEXT | LOS is the length of stay for the patient for the given ICU stay, which may include one or more ICU units. The length of stay is measured in fractional days. |

## ingredientevents

Official table documentation: [https://mimic.mit.edu/docs/iv/modules/icu/ingredientevents.html](https://mimic.mit.edu/docs/iv/modules/icu/ingredientevents.html)

*No verified table summary*

| Column | Native type | SQLite type | Description |
|---|---|---|---|
| `subject_id` | INTEGER | TEXT | Identifiers which specify the patient: subject_id is unique to a patient, hadm_id is unique to a patient hospital stay and stay_id is unique to a patient ICU stay. |
| `hadm_id` | INTEGER | TEXT | Identifiers which specify the patient: subject_id is unique to a patient, hadm_id is unique to a patient hospital stay and stay_id is unique to a patient ICU stay. |
| `stay_id` | INTEGER | TEXT | Identifiers which specify the patient: subject_id is unique to a patient, hadm_id is unique to a patient hospital stay and stay_id is unique to a patient ICU stay. |
| `caregiver_id` | INTEGER | TEXT | caregiver_id uniquely identifies a single caregiver who documented data in the ICU information system. |
| `starttime` | TIMESTAMP(0) | TEXT | starttime and endtime record the start and end time of the event. |
| `endtime` | TIMESTAMP(0) | TEXT | starttime and endtime record the start and end time of the event. |
| `storetime` | TIMESTAMP(0) | TEXT | storetime records the time at which an observation was manually input or manually validated by a member of the clinical staff. |
| `itemid` | INTEGER | TEXT | Identifier for a single measurement type in the database. Each row associated with one itemid which corresponds to an instantiation of the same measurement (e.g. norepinephrine). |
| `amount` | DOUBLE PRECISION | TEXT | amount and amountuom list the amount of a drug or substance administered to the patient either between the starttime and endtime . |
| `amountuom` | VARCHAR(20) | TEXT | amount and amountuom list the amount of a drug or substance administered to the patient either between the starttime and endtime . |
| `rate` | DOUBLE PRECISION | TEXT | rate and rateuom list the rate at which the drug or substance was administered to the patient either between the starttime and endtime . |
| `rateuom` | VARCHAR(20) | TEXT | rate and rateuom list the rate at which the drug or substance was administered to the patient either between the starttime and endtime . |
| `orderid` | INTEGER | TEXT | orderid links multiple items contained in the same solution together. For example, when a solution of noradrenaline and normal saline is administered both noradrenaline and normal saline occur on distinct rows but will have the same orderid . linkorderid links the same order across multiple instantiations: for example, if the rate of delivery for the solution with noradrenaline and normal saline is changed, two new rows which share the same new orderid will be generated, but the linkorderid will be the same. |
| `linkorderid` | INTEGER | TEXT | orderid links multiple items contained in the same solution together. For example, when a solution of noradrenaline and normal saline is administered both noradrenaline and normal saline occur on distinct rows but will have the same orderid . linkorderid links the same order across multiple instantiations: for example, if the rate of delivery for the solution with noradrenaline and normal saline is changed, two new rows which share the same new orderid will be generated, but the linkorderid will be the same. |
| `statusdescription` | VARCHAR(20) | TEXT | statusdescription states the ultimate status of the item, or more specifically, row. It is used to indicate why the delivery of the compound has ended. There are only six possible statuses: Changed - The current delivery has ended as some aspect of it has changed (most frequently, the rate has been changed) Paused - The current delivery has been paused FinishedRunning - The delivery of the item has finished (most frequently, the bag containing the compound is empty) Stopped - The delivery of the item been terminated by the caregiver Rewritten - Incorrect information was input, and so the information in this row was rewritten (these rows are primarily useful for auditing purposes - the rates/amounts described we |
| `originalamount` | DOUBLE PRECISION | TEXT | Drugs are usually mixed within a solution and delivered continuously from the same bag. This column represents the amount of the compound contained in the bag at starttime . |
| `originalrate` | DOUBLE PRECISION | TEXT | This is the rate that was input by the care provider. Note that this may differ from rate because of various reasons: originalrate was the original planned rate, while the rate column will be the true rate delivered. |

## inputevents

Official table documentation: [https://mimic.mit.edu/docs/iv/modules/icu/inputevents.html](https://mimic.mit.edu/docs/iv/modules/icu/inputevents.html)

*No verified table summary*

| Column | Native type | SQLite type | Description |
|---|---|---|---|
| `subject_id` | INT | TEXT | Identifiers which specify the patient: subject_id is unique to a patient, hadm_id is unique to a patient hospital stay and stay_id is unique to a patient ICU stay. |
| `hadm_id` | INT | TEXT | Identifiers which specify the patient: subject_id is unique to a patient, hadm_id is unique to a patient hospital stay and stay_id is unique to a patient ICU stay. |
| `stay_id` | INT | TEXT | Identifiers which specify the patient: subject_id is unique to a patient, hadm_id is unique to a patient hospital stay and stay_id is unique to a patient ICU stay. |
| `caregiver_id` | INTEGER | TEXT | caregiver_id uniquely identifies a single caregiver who documented data in the ICU information system. |
| `starttime` | TIMESTAMP(0) | TEXT | starttime and endtime record the start and end time of an input/output event. |
| `endtime` | TIMESTAMP(0) | TEXT | starttime and endtime record the start and end time of an input/output event. |
| `storetime` | TIMESTAMP(0) | TEXT | storetime records the time at which an observation was manually input or manually validated by a member of the clinical staff. |
| `itemid` | INT | TEXT | Identifier for a single measurement type in the database. Each row associated with one itemid which corresponds to an instantiation of the same measurement (e.g. norepinephrine). |
| `amount` | DOUBLE PRECISION | TEXT | amount and amountuom list the amount of a drug or substance administered to the patient either between the starttime and endtime . |
| `amountuom` | VARCHAR(30) | TEXT | amount and amountuom list the amount of a drug or substance administered to the patient either between the starttime and endtime . |
| `rate` | DOUBLE PRECISION | TEXT | rate and rateuom list the rate at which the drug or substance was administered to the patient either between the starttime and endtime . |
| `rateuom` | VARCHAR(30) | TEXT | rate and rateuom list the rate at which the drug or substance was administered to the patient either between the starttime and endtime . |
| `orderid` | BIGINT | TEXT | orderid links multiple items contained in the same solution together. For example, when a solution of noradrenaline and normal saline is administered both noradrenaline and normal saline occur on distinct rows but will have the same orderid . linkorderid links the same order across multiple instantiations: for example, if the rate of delivery for the solution with noradrenaline and normal saline is changed, two new rows which share the same new orderid will be generated, but the linkorderid will be the same. |
| `linkorderid` | BIGINT | TEXT | orderid links multiple items contained in the same solution together. For example, when a solution of noradrenaline and normal saline is administered both noradrenaline and normal saline occur on distinct rows but will have the same orderid . linkorderid links the same order across multiple instantiations: for example, if the rate of delivery for the solution with noradrenaline and normal saline is changed, two new rows which share the same new orderid will be generated, but the linkorderid will be the same. |
| `ordercategoryname` | VARCHAR(100) | TEXT | These columns provide higher level information about the order the medication/solution is a part of. Categories represent the type of administration, while the ordercomponenttypedescription describes the role of the substance in the solution (i.e. main order parameter, additive, or mixed solution) |
| `secondaryordercategoryname` | VARCHAR(100) | TEXT | These columns provide higher level information about the order the medication/solution is a part of. Categories represent the type of administration, while the ordercomponenttypedescription describes the role of the substance in the solution (i.e. main order parameter, additive, or mixed solution) |
| `ordercomponenttypedescription` | VARCHAR(200) | TEXT | These columns provide higher level information about the order the medication/solution is a part of. Categories represent the type of administration, while the ordercomponenttypedescription describes the role of the substance in the solution (i.e. main order parameter, additive, or mixed solution) |
| `ordercategorydescription` | VARCHAR(50) | TEXT | These columns provide higher level information about the order the medication/solution is a part of. Categories represent the type of administration, while the ordercomponenttypedescription describes the role of the substance in the solution (i.e. main order parameter, additive, or mixed solution) |
| `patientweight` | DOUBLE PRECISION | TEXT | The patient weight in kilograms. |
| `totalamount` | DOUBLE PRECISION | TEXT | Intravenous administrations are usually given by hanging a bag of fluid at the bedside for continuous infusion over a certain period of time. These columns list the total amount of the fluid in the bag containing the solution. |
| `totalamountuom` | VARCHAR(50) | TEXT | Intravenous administrations are usually given by hanging a bag of fluid at the bedside for continuous infusion over a certain period of time. These columns list the total amount of the fluid in the bag containing the solution. |
| `isopenbag` | SMALLINT | TEXT | Whether the order was from an open bag. |
| `continueinnextdept` | Unverified | TEXT | If the order ended on patient transfer, this field indicates if it continued into the next department (e.g. a floor). |
| `statusdescription` | VARCHAR(30) | TEXT | statusdescription states the ultimate status of the item, or more specifically, row. It is used to indicate why the delivery of the compound has ended. There are only six possible statuses: Changed - The current delivery has ended as some aspect of it has changed (most frequently, the rate has been changed) Paused - The current delivery has been paused FinishedRunning - The delivery of the item has finished (most frequently, the bag containing the compound is empty) Stopped - The delivery of the item been terminated by the caregiver Flushed - A line was flushed. |
| `originalamount` | DOUBLE PRECISION | TEXT | Drugs are usually mixed within a solution and delivered continuously from the same bag. This column represents the amount of the drug contained in the bag at starttime . For the first infusion of a new bag, originalamount : totalamount . Later on, if the rate is changed, then the amount of the drug in the bag will be lower (as some has been administered to the patient). As a result, originalamount < totalamount , and originalamount will be the amount of drug leftover in the bag at that starttime . |
| `originalrate` | DOUBLE PRECISION | TEXT | This is the rate that was input by the care provider. Note that this may differ from rate because of various reasons: originalrate was the original planned rate, while the rate column will be the true rate delivered. For example, if a a bag is about to run out and the care giver decides to push the rest of the fluid, then rate > originalrate . However, these two columns are usually the same, but have minor non-clinically significant differences due to rounding error. |

## labevents

Official table documentation: [https://mimic.mit.edu/docs/iv/modules/hosp/labevents.html](https://mimic.mit.edu/docs/iv/modules/hosp/labevents.html)

*No verified table summary*

| Column | Native type | SQLite type | Description |
|---|---|---|---|
| `labevent_id` | INTEGER NOT NULL | TEXT | An integer which is unique for every row in the table. |
| `subject_id` | INTEGER NOT NULL | TEXT | subject_id is a unique identifier which specifies an individual patient. Any rows associated with a single subject_id pertain to the same individual. |
| `hadm_id` | INTEGER | TEXT | hadm_id is an integer identifier which is unique for each patient hospitalization. |
| `specimen_id` | INTEGER NOT NULL | TEXT | Uniquely denoted the specimen from which the lab measurement was made. Most lab measurements are made on patient derived samples (specimens) such as blood, urine, and so on. Often multiple measurements are made on the same sample. The specimen_id will group measurements made on the same sample, e.g. blood gas measurements made on the same sample of blood. |
| `itemid` | INTEGER NOT NULL | TEXT | An identifier which uniquely denotes laboratory concepts. |
| `order_provider_id` | VARCHAR(10) | TEXT | order_provider_id provides an anonymous identifier for the provider who ordered the laboratory measurement. Provider identifiers follow a consistent pattern: the letter “P”, followed by either three numbers, followed by two letters or two numbers. For example, “P003AB”, “P00102”, “P1248B”, etc. Provider identifiers are randomly generated and do not have any inherent meaning aside from uniquely identifying the same provider across the database. |
| `charttime` | TIMESTAMP(0) | TEXT | The time at which the laboratory measurement was charted. This is usually the time at which the specimen was acquired, and is usually significantly earlier than the time at which the measurement is available. |
| `storetime` | TIMESTAMP(0) | TEXT | The time at which the measurement was made available in the laboratory system. This is when the information would have been available to care providers. |
| `value` | VARCHAR(200) | TEXT | The result of the laboratory measurement and, if it is numeric, the value cast as a numeric data type. |
| `valuenum` | DOUBLE PRECISION | TEXT | The result of the laboratory measurement and, if it is numeric, the value cast as a numeric data type. |
| `valueuom` | VARCHAR(20) | TEXT | The unit of measurement for the laboratory concept. |
| `ref_range_lower` | DOUBLE PRECISION | TEXT | Upper and lower reference ranges indicating the normal range for the laboratory measurements. Values outside the reference ranges are considered abnormal. |
| `ref_range_upper` | DOUBLE PRECISION | TEXT | Upper and lower reference ranges indicating the normal range for the laboratory measurements. Values outside the reference ranges are considered abnormal. |
| `flag` | VARCHAR(10) | TEXT | A brief string mainly used to indicate if the laboratory measurement is abnormal. |
| `priority` | VARCHAR(7) | TEXT | The priority of the laboratory measurement: either routine or stat (urgent). |
| `comments` | TEXT | TEXT | Deidentified free-text comments associated with the laboratory measurement. Usually these provide information about the sample, whether any notifications were made to care providers regarding the results, considerations for interpretation, or in some cases the comments contain the result of the laboratory itself. Comments which have been fully deidentified (i.e. no information content retained) are present as three underscores: ___ . A NULL comment indicates no comment was made for the row. |

## microbiologyevents

Official table documentation: [https://mimic.mit.edu/docs/iv/modules/hosp/microbiologyevents.html](https://mimic.mit.edu/docs/iv/modules/hosp/microbiologyevents.html)

*No verified table summary*

| Column | Native type | SQLite type | Description |
|---|---|---|---|
| `microevent_id` | INTEGER NOT NULL | TEXT | A unique integer denoting the row. |
| `subject_id` | INTEGER NOT NULL | TEXT | subject_id is a unique identifier which specifies an individual patient. Any rows associated with a single subject_id pertain to the same individual. |
| `hadm_id` | INTEGER | TEXT | hadm_id is an integer identifier which is unique for each patient hospitalization. |
| `micro_specimen_id` | INTEGER NOT NULL | TEXT | Uniquely denoted the specimen from which the microbiology measurement was made. Most microbiology measurements are made on patient derived samples (specimens) such as blood, urine, and so on. Often multiple measurements are made on the same sample. The micro_specimen_id will group measurements made on the same sample, e.g. organisms which grew from the same blood sample. |
| `order_provider_id` | VARCHAR(10) | TEXT | order_provider_id provides an anonymous identifier for the provider who ordered the microbiology test. Provider identifiers follow a consistent pattern: the letter “P”, followed by either three numbers, followed by two letters or two numbers. For example, “P003AB”, “P00102”, “P1248B”, etc. Provider identifiers are randomly generated and do not have any inherent meaning aside from uniquely identifying the same provider across the database. |
| `chartdate` | TIMESTAMP(0) NOT NULL | TEXT | charttime records the time at which an observation was charted, and is usually the closest proxy to the time the data was actually measured. chartdate is the same as charttime , except there is no time available. chartdate was included as time information is not always available for microbiology measurements: in order to be clear about when this occurs, charttime is null, and chartdate contains the date of the measurement. In the cases where both charttime and chartdate exists, chartdate is equal to a truncated version of charttime (i.e. charttime without the timing information). Not all observations have a charttime , but all observations have a chartdate . |
| `charttime` | TIMESTAMP(0) | TEXT | charttime records the time at which an observation was charted, and is usually the closest proxy to the time the data was actually measured. chartdate is the same as charttime , except there is no time available. chartdate was included as time information is not always available for microbiology measurements: in order to be clear about when this occurs, charttime is null, and chartdate contains the date of the measurement. In the cases where both charttime and chartdate exists, chartdate is equal to a truncated version of charttime (i.e. charttime without the timing information). Not all observations have a charttime , but all observations have a chartdate . |
| `spec_itemid` | INTEGER NOT NULL | TEXT | The specimen which is tested for bacterial growth. The specimen is a sample derived from a patient; e.g. blood, urine, sputum, etc. |
| `spec_type_desc` | VARCHAR(100) NOT NULL | TEXT | The specimen which is tested for bacterial growth. The specimen is a sample derived from a patient; e.g. blood, urine, sputum, etc. |
| `test_seq` | INTEGER NOT NULL | TEXT | If multiple samples are drawn, the test_seq will delineate them. For example, if an aerobic and anerobic culture bottle are used for the same specimen, they will have distinct test_seq values (likely 1 and 2). |
| `storedate` | TIMESTAMP(0) | TEXT | The date ( storedate ) or date and time ( storetime ) of when the microbiology result was available. While many interim results are made available during the process of assessing a microbiology culture, the times here are the time of the last known update. |
| `storetime` | TIMESTAMP(0) | TEXT | The date ( storedate ) or date and time ( storetime ) of when the microbiology result was available. While many interim results are made available during the process of assessing a microbiology culture, the times here are the time of the last known update. |
| `test_itemid` | INTEGER | TEXT | The test performed on the given specimen. |
| `test_name` | VARCHAR(100) | TEXT | The test performed on the given specimen. |
| `org_itemid` | INTEGER | TEXT | The organism, if any, which grew when tested. If NULL, no organism grew (i.e. a negative culture). |
| `org_name` | VARCHAR(100) | TEXT | The organism, if any, which grew when tested. If NULL, no organism grew (i.e. a negative culture). |
| `isolate_num` | SMALLINT | TEXT | For testing antibiotics, the isolated colony (integer; starts at 1). |
| `quantity` | VARCHAR(50) | TEXT | *Not documented / not reliably matched* |
| `ab_itemid` | INTEGER | TEXT | If an antibiotic was tested against the given organism for sensitivity, the antibiotic is listed here. |
| `ab_name` | VARCHAR(30) | TEXT | If an antibiotic was tested against the given organism for sensitivity, the antibiotic is listed here. |
| `dilution_text` | VARCHAR(10) | TEXT | Dilution values when testing antibiotic sensitivity. |
| `dilution_comparison` | VARCHAR(20) | TEXT | Dilution values when testing antibiotic sensitivity. |
| `dilution_value` | DOUBLE PRECISION | TEXT | Dilution values when testing antibiotic sensitivity. |
| `interpretation` | VARCHAR(5) | TEXT | interpretation of the antibiotic sensitivity, and indicates the results of the test. “S” is sensitive, “R” is resistant, “I” is intermediate, and “P” is pending. |
| `comments` | TEXT | TEXT | Deidentified free-text comments associated with the microbiology measurement. Usually these provide information about the sample, whether any notifications were made to care providers regarding the results, considerations for interpretation, or in some cases the comments contain the result of the measurement itself. Comments which have been fully deidentified (i.e. no information content retained) are present as three underscores: ___ . A NULL comment indicates no comment was made for the row. |

## omr

Official table documentation: [https://mimic.mit.edu/docs/iv/modules/hosp/omr.html](https://mimic.mit.edu/docs/iv/modules/hosp/omr.html)

*No verified table summary*

| Column | Native type | SQLite type | Description |
|---|---|---|---|
| `subject_id` | INTEGER NOT NULL | TEXT | subject_id is a unique identifier which specifies an individual patient. Any rows associated with a single subject_id pertain to the same individual. |
| `chartdate` | DATE NOT NULL | TEXT | The date on which the observation was recorded. |
| `seq_num` | INTEGER NOT NULL | TEXT | An monotonically increasing integer which uniquely distinguishes results of the same type recorded on the same day. For example, if two blood pressure measurements occur on the same day, seq_num orders them chronologically. |
| `result_name` | VARCHAR(100) NOT NULL | TEXT | Each row provides detail regarding a single observation in the EHR. result_name provides a human interpretable description of the observation. As of MIMIC-IV v2.2, the following table lists the number of observations and the most common value. result_name number of observations example value eGFR 240 >60 Blood Pressure Lying 2764 120/70 Blood Pressure Sitting 3400 120/70 Blood Pressure Standing (1 min) 2560 90/60 Blood Pressure Standing 523 110/70 Blood Pressure Standing (3 mins) 626 80/50 BMI (kg/m2) 1662112 26.6 Weight (Lbs) 1889542 150 Blood Pressure 2169549 110/70 Height (Inches) 706906 64 BMI 554 25.0 Weight 354 150.00 Height 39 64.50 |
| `result_value` | TEXT NOT NULL | TEXT | result_value is the value associated with the given OMR observation. For example, for the result_name of ‘Blood Pressure’, the field_value column contains the recorded blood pressure (120/80, 130/70, and so on). |

## outputevents

Official table documentation: [https://mimic.mit.edu/docs/iv/modules/icu/outputevents.html](https://mimic.mit.edu/docs/iv/modules/icu/outputevents.html)

*No verified table summary*

| Column | Native type | SQLite type | Description |
|---|---|---|---|
| `subject_id` | INTEGER | TEXT | Identifiers which specify the patient: subject_id is unique to a patient, hadm_id is unique to a patient hospital stay and stay_id is unique to a patient ICU stay. |
| `hadm_id` | INTEGER | TEXT | Identifiers which specify the patient: subject_id is unique to a patient, hadm_id is unique to a patient hospital stay and stay_id is unique to a patient ICU stay. |
| `stay_id` | INTEGER | TEXT | Identifiers which specify the patient: subject_id is unique to a patient, hadm_id is unique to a patient hospital stay and stay_id is unique to a patient ICU stay. |
| `caregiver_id` | INTEGER | TEXT | caregiver_id uniquely identifies a single caregiver who documented data in the ICU information system. |
| `charttime` | TIMESTAMP(3) | TEXT | charttime is the time of an output event. |
| `storetime` | TIMESTAMP(3) | TEXT | storetime records the time at which an observation was manually input or manually validated by a member of the clinical staff. |
| `itemid` | INTEGER | TEXT | Identifier for a single measurement type in the database. Each row associated with one itemid (e.g. 212) corresponds to an instantiation of the same measurement (e.g. heart rate). |
| `value` | DOUBLE PRECISION | TEXT | value and valueuom list the amount of a substance at the charttime (when the exact start time is unknown, but usually up to an hour before). |
| `valueuom` | VARCHAR(20) | TEXT | value and valueuom list the amount of a substance at the charttime (when the exact start time is unknown, but usually up to an hour before). |

## patients

Official table documentation: [https://mimic.mit.edu/docs/iv/modules/hosp/patients.html](https://mimic.mit.edu/docs/iv/modules/hosp/patients.html)

*No verified table summary*

| Column | Native type | SQLite type | Description |
|---|---|---|---|
| `subject_id` | INTEGER NOT NULL | TEXT | subject_id is a unique identifier which specifies an individual patient. Any rows associated with a single subject_id pertain to the same individual. As subject_id is the primary key for the table, it is unique for each row. |
| `gender` | VARCHAR(1) NOT NULL | TEXT | gender is the genotypical sex of the patient. |
| `anchor_age` | INTEGER NOT NULL | TEXT | These columns provide information regarding the actual patient year for the patient admission, and the patient’s age at that time. anchor_year is a shifted year for the patient. anchor_year_group is a range of years - the patient’s anchor_year occurred during this range. anchor_age is the patient’s age in the anchor_year . If a patient’s anchor_age is over 89 in the anchor_year then their anchor_age is set to 91, regardless of how old they actually were. Example: a patient has an anchor_year of 2153, anchor_year_group of 2008 - 2010, and an anchor_age of 60. The year 2153 for the patient corresponds to 2008, 2009, or 2010. The patient was 60 in the shifted year of 2153, i.e. they were 60 in 2008, 2009, or 2010. |
| `anchor_year` | INTEGER NOT NULL | TEXT | These columns provide information regarding the actual patient year for the patient admission, and the patient’s age at that time. anchor_year is a shifted year for the patient. anchor_year_group is a range of years - the patient’s anchor_year occurred during this range. anchor_age is the patient’s age in the anchor_year . If a patient’s anchor_age is over 89 in the anchor_year then their anchor_age is set to 91, regardless of how old they actually were. Example: a patient has an anchor_year of 2153, anchor_year_group of 2008 - 2010, and an anchor_age of 60. The year 2153 for the patient corresponds to 2008, 2009, or 2010. The patient was 60 in the shifted year of 2153, i.e. they were 60 in 2008, 2009, or 2010. |
| `anchor_year_group` | VARCHAR(255) NOT NULL | TEXT | These columns provide information regarding the actual patient year for the patient admission, and the patient’s age at that time. anchor_year is a shifted year for the patient. anchor_year_group is a range of years - the patient’s anchor_year occurred during this range. anchor_age is the patient’s age in the anchor_year . If a patient’s anchor_age is over 89 in the anchor_year then their anchor_age is set to 91, regardless of how old they actually were. Example: a patient has an anchor_year of 2153, anchor_year_group of 2008 - 2010, and an anchor_age of 60. The year 2153 for the patient corresponds to 2008, 2009, or 2010. The patient was 60 in the shifted year of 2153, i.e. they were 60 in 2008, 2009, or 2010. |
| `dod` | TIMESTAMP(0) | TEXT | The de-identified date of death for the patient. Date of death is extracted from two sources: the hospital information system and the Massachusetts State Registry of Vital Records and Statistics . Individual patient records from MIMIC were matched to the vital records using a custom algorithm based on identifiers including name, social security number, and date of birth. As a result of the linkage, out of hospital mortality is available for MIMIC-IV patients up to one year post-hospital discharge . All patient deaths occurring more than one year after hospital discharge are censored. Survival studies should incorporate this into their design. |

## pharmacy

Official table documentation: [https://mimic.mit.edu/docs/iv/modules/hosp/pharmacy.html](https://mimic.mit.edu/docs/iv/modules/hosp/pharmacy.html)

*No verified table summary*

| Column | Native type | SQLite type | Description |
|---|---|---|---|
| `subject_id` | INTEGER NOT NULL | TEXT | subject_id is a unique identifier which specifies an individual patient. Any rows associated with a single subject_id pertain to the same individual. |
| `hadm_id` | INTEGER NOT NULL | TEXT | hadm_id is an integer identifier which is unique for each patient hospitalization. |
| `pharmacy_id` | INTEGER NOT NULL | TEXT | A unique identifier for the given pharmacy entry. Each row of the pharmacy table has a unique pharmacy_id . This identifier can be used to link the pharmacy information to the provider order (in poe or prescriptions ) or to the administration of the medication (in emar ). |
| `poe_id` | VARCHAR(25) | TEXT | A foreign key which links to the provider order entry order in the prescriptions table associated with this pharmacy record. |
| `starttime` | TIMESTAMP(3) | TEXT | The start and stop times for the given prescribed medication. |
| `stoptime` | TIMESTAMP(3) | TEXT | The start and stop times for the given prescribed medication. |
| `medication` | TEXT | TEXT | The name of the medication provided. |
| `proc_type` | VARCHAR(50) NOT NULL | TEXT | The type of order: “IV Piggyback”, “Non-formulary”, “Unit Dose”, and so on. |
| `status` | VARCHAR(50) | TEXT | Whether the prescription is active, inactive, or discontinued. |
| `entertime` | TIMESTAMP(3) NOT NULL | TEXT | The date and time at which the prescription was entered into the pharmacy system. |
| `verifiedtime` | TIMESTAMP(3) | TEXT | The date and time at which the prescription was verified by a physician. |
| `route` | VARCHAR(50) | TEXT | The intended route of administration for the prescription. |
| `frequency` | VARCHAR(50) | TEXT | The frequency at which the medication should be administered to the patient. Many commonly used short hands are used in the frequency column. Q# indicates every # hours; e.g. “Q6” or “Q6H” is every 6 hours. |
| `disp_sched` | VARCHAR(255) | TEXT | The hours of the day at which the medication should be administered, e.g. “08, 20” would indicate the medication should be administered at 8:00 AM and 8:00 PM, respectively. |
| `infusion_type` | VARCHAR(15) | TEXT | A coded letter describing the type of infusion: ‘B’, ‘C’, ‘N’, ‘N1’, ‘O’, or ‘R’. |
| `sliding_scale` | VARCHAR(1) | TEXT | Indicates whether the medication should be given on a sliding scale: either ‘Y’ or ‘N’. |
| `lockout_interval` | VARCHAR(50) | TEXT | The time the patient must wait until providing themselves with another dose; often used with patient controlled analgesia. |
| `basal_rate` | REAL | TEXT | The rate at which the medication is given over 24 hours. |
| `one_hr_max` | VARCHAR(10) | TEXT | The maximum dose that may be given in a single hour. |
| `doses_per_24_hrs` | REAL | TEXT | The number of expected doses per 24 hours. Note that this column can be misleading for continuously infused medications as they are usually only “dosed” once per day, despite continuous administration. |
| `duration` | REAL | TEXT | duration is the numeric duration of the given dose, while duration_interval can be considered as the unit of measurement for the given duration. For example, often duration is 1 and duration_interval is “Doses”. Alternatively, duration could be 8 and the duration_interval could be “Weeks”. |
| `duration_interval` | VARCHAR(50) | TEXT | duration is the numeric duration of the given dose, while duration_interval can be considered as the unit of measurement for the given duration. For example, often duration is 1 and duration_interval is “Doses”. Alternatively, duration could be 8 and the duration_interval could be “Weeks”. |
| `expiration_value` | INTEGER | TEXT | If the drug has a relevant expiry date, these columns detail when this occurs. expiration_value and expiration_unit provide a length of time until the drug expires, e.g. 30 days, 72 hours, and so on. expirationdate provides the deidentified date of expiry. |
| `expiration_unit` | VARCHAR(50) | TEXT | If the drug has a relevant expiry date, these columns detail when this occurs. expiration_value and expiration_unit provide a length of time until the drug expires, e.g. 30 days, 72 hours, and so on. expirationdate provides the deidentified date of expiry. |
| `expirationdate` | TIMESTAMP(3) | TEXT | If the drug has a relevant expiry date, these columns detail when this occurs. expiration_value and expiration_unit provide a length of time until the drug expires, e.g. 30 days, 72 hours, and so on. expirationdate provides the deidentified date of expiry. |
| `dispensation` | VARCHAR(50) | TEXT | The source of dispensation for the medication. |
| `fill_quantity` | VARCHAR(50) | TEXT | What proportion of the formulary to fill. |

## poe

Official table documentation: [https://mimic.mit.edu/docs/iv/modules/hosp/poe.html](https://mimic.mit.edu/docs/iv/modules/hosp/poe.html)

*No verified table summary*

| Column | Native type | SQLite type | Description |
|---|---|---|---|
| `poe_id` | VARCHAR(25) NOT NULL | TEXT | A unique identifier for the given order. poe_id is composed of subject_id and a monotonically increasing integer, poe_seq , in the following format: subject_id - poe_seq . |
| `poe_seq` | INTEGER NOT NULL | TEXT | A monotonically increasing integer which chronologically sorts the POE orders. That is, POE orders can be ordered sequentially by poe_seq . |
| `subject_id` | INTEGER NOT NULL | TEXT | subject_id is a unique identifier which specifies an individual patient. Any rows associated with a single subject_id pertain to the same individual. |
| `hadm_id` | INTEGER | TEXT | hadm_id is an integer identifier which is unique for each patient hospitalization. |
| `ordertime` | TIMESTAMP(0) NOT NULL | TEXT | The date and time at which the provider order was made. |
| `order_type` | VARCHAR(25) NOT NULL | TEXT | The type of provider order. One of the following: ADT orders Blood Bank Cardiology Consults Critical Care General Care Hemodialysis IV therapy Lab Medications Neurology Nutrition OB Radiology Respiratory TPN |
| `order_subtype` | VARCHAR(50) | TEXT | Further detail on the type of order made by the provider. The order_subtype is best interpreted alongside the order_type , e.g. order_type: 'Cardiology' with order_subtype: 'Holter Monitor' . |
| `transaction_type` | VARCHAR(15) | TEXT | The action which the provider performed when performing this order. One of the following: Change Co D/C H New T |
| `discontinue_of_poe_id` | VARCHAR(25) | TEXT | If this order discontinues a previous order, then discontinue_of_poe_id will link to the previous order which was discontinued. Conversely, if this order was later discontinued by a distinct order, then discontinued_by_poe_id will link to that future order. |
| `discontinued_by_poe_id` | VARCHAR(25) | TEXT | If this order discontinues a previous order, then discontinue_of_poe_id will link to the previous order which was discontinued. Conversely, if this order was later discontinued by a distinct order, then discontinued_by_poe_id will link to that future order. |
| `order_provider_id` | VARCHAR(10) | TEXT | order_provider_id provides an anonymous identifier for the provider who made the order. Provider identifiers follow a consistent pattern: the letter “P”, followed by either three numbers, followed by two letters or two numbers. For example, “P003AB”, “P00102”, “P1248B”, etc. Provider identifiers are randomly generated and do not have any inherent meaning aside from uniquely identifying the same provider across the database. |
| `order_status` | VARCHAR(15) | TEXT | Whether the order is still active (‘Active’) or whether it has been inactivated (‘Inactive’). |

## poe_detail

Official table documentation: [https://mimic.mit.edu/docs/iv/modules/hosp/poe_detail.html](https://mimic.mit.edu/docs/iv/modules/hosp/poe_detail.html)

*No verified table summary*

| Column | Native type | SQLite type | Description |
|---|---|---|---|
| `poe_id` | VARCHAR(25) NOT NULL | TEXT | A unique identifier for the given order. poe_id is composed of subject_id and a monotonically increasing integer, poe_seq , in the following format: subject_id - poe_seq . |
| `poe_seq` | INTEGER NOT NULL | TEXT | A monotonically increasing integer which chronologically sorts the POE orders. That is, POE orders can be ordered sequentially by poe_seq . |
| `subject_id` | INTEGER NOT NULL | TEXT | subject_id is a unique identifier which specifies an individual patient. Any rows associated with a single subject_id pertain to the same individual. |
| `field_name` | VARCHAR(255) NOT NULL | TEXT | Each row provides detail regarding a particular aspect of a POE order. field_name is the name given to that aspect. As of MIMIC-IV v2.2, the following table lists the possible values and the most common entry for it in field_value . field_name number of rows most frequent field_value observation Admit to 881522 Medicine Indication 27190 Antibiotics Code status 197932 Resuscitate (Full code) Transfer to 161707 Medicine Admit category 1093726 Admit to inpatient Consult Status 36591 Accepted Discharge When 431642 Discharge Now Level of Urgency 45617 Routine (within 24 hours) Discharge Planning 475428 Finalized Consult Status Time 36591 2149-12-03 09:00:01 Tubes & Drains type 491472 Indwelling urinary catheter (IUC |
| `field_value` | TEXT | TEXT | field_value is the value associated with the given POE order and field_name . For example, for the field_name of ‘Admit to’, the field_value column contains the type of unit the patient was admitted to (Psychiatry, GYN, and so on). |

## prescriptions

Official table documentation: [https://mimic.mit.edu/docs/iv/modules/hosp/prescriptions.html](https://mimic.mit.edu/docs/iv/modules/hosp/prescriptions.html)

*No verified table summary*

| Column | Native type | SQLite type | Description |
|---|---|---|---|
| `subject_id` | INTEGER NOT NULL | TEXT | subject_id is a unique identifier which specifies an individual patient. Any rows associated with a single subject_id pertain to the same individual. |
| `hadm_id` | INTEGER NOT NULL | TEXT | hadm_id is an integer identifier which is unique for each patient hospitalization. |
| `pharmacy_id` | INTEGER NOT NULL | TEXT | An identifier which links administrations in emar to pharmacy information in the pharmacy table. |
| `poe_id` | VARCHAR(25) | TEXT | These columns allow linking prescriptions to associated orders in the poe table. |
| `poe_seq` | INTEGER | TEXT | These columns allow linking prescriptions to associated orders in the poe table. |
| `order_provider_id` | VARCHAR(10) | TEXT | order_provider_id provides an anonymous identifier for the provider who initiated the order. Provider identifiers follow a consistent pattern: the letter “P”, followed by either three numbers, followed by two letters or two numbers. For example, “P003AB”, “P00102”, “P1248B”, etc. Provider identifiers are randomly generated and do not have any inherent meaning aside from uniquely identifying the same provider across the database. |
| `starttime` | TIMESTAMP(3) | TEXT | The prescribed start and stop time for the medication. |
| `stoptime` | TIMESTAMP(3) | TEXT | The prescribed start and stop time for the medication. |
| `drug_type` | VARCHAR(20) NOT NULL | TEXT | The component of the prescription which the drug occupies. Can be one of ‘MAIN’, ‘BASE’, or ‘ADDITIVE’. |
| `drug` | VARCHAR(255) NOT NULL | TEXT | A free-text description of the medication administered. |
| `formulary_drug_cd` | VARCHAR(50) | TEXT | A hospital specific ontology used to order drugs from the formulary. |
| `gsn` | VARCHAR(255) | TEXT | The Generic Sequence Number (GSN), a coded identifier used for medications. |
| `ndc` | VARCHAR(25) | TEXT | The National Drug Code (NDC), a coded identifier which uniquely identifiers medications. |
| `prod_strength` | VARCHAR(255) | TEXT | A free-text description of the composition of the prescribed medication (e.g. ‘12 mg / 0.8 mL Oral Syringe’, ‘12.5mg Tablet’, etc). |
| `form_rx` | VARCHAR(25) | TEXT | The container in which the formulary dose is delivered (e.g. ‘TABLET’, ‘VIAL’, etc). |
| `dose_val_rx` | VARCHAR(100) | TEXT | The prescribed dose for the patient intended to be administered over the given time period. |
| `dose_unit_rx` | VARCHAR(50) | TEXT | The unit of measurement for the dose. |
| `form_val_disp` | VARCHAR(50) | TEXT | The amount of the medication which is contained in a single formulary dose. |
| `form_unit_disp` | VARCHAR(50) | TEXT | The unit of measurement used for the formulary dosage. |
| `doses_per_24_hrs` | REAL | TEXT | The number of doses per 24 hours for which the medication is to be given. A daily dose would result in doses_per_24_hrs : 1, bidaily (BID) would be 2, and so on. |
| `route` | VARCHAR(50) | TEXT | The route of administration for the medication. |

## procedureevents

Official table documentation: [https://mimic.mit.edu/docs/iv/modules/icu/procedureevents.html](https://mimic.mit.edu/docs/iv/modules/icu/procedureevents.html)

*No verified table summary*

| Column | Native type | SQLite type | Description |
|---|---|---|---|
| `subject_id` | INTEGER | TEXT | Identifiers which specify the patient: subject_id is unique to a patient, hadm_id is unique to a patient hospital stay and stay_id is unique to a patient ICU stay. |
| `hadm_id` | INTEGER | TEXT | Identifiers which specify the patient: subject_id is unique to a patient, hadm_id is unique to a patient hospital stay and stay_id is unique to a patient ICU stay. |
| `stay_id` | INTEGER | TEXT | Identifiers which specify the patient: subject_id is unique to a patient, hadm_id is unique to a patient hospital stay and stay_id is unique to a patient ICU stay. |
| `caregiver_id` | INTEGER | TEXT | caregiver_id uniquely identifies a single caregiver who documented data in the ICU information system. |
| `starttime` | TIMESTAMP | TEXT | starttime and endtime record the start and end time of an event. |
| `endtime` | TIMESTAMP | TEXT | starttime and endtime record the start and end time of an event. |
| `storetime` | TIMESTAMP | TEXT | storetime specifies the time when the event was recorded in the system. |
| `itemid` | INTEGER | TEXT | Identifier for a single measurement type in the database. Each row associated with one itemid (e.g. 212) corresponds to a type of measurement (e.g. heart rate). The d_items table may be joined on this field. For any itemid appearing in the procedureevents table, d_items linksto column will have the value ‘procedureevents’. |
| `value` | DOUBLE PRECISION | TEXT | In the procedureevents table, this identifies the duration of the procedure (if applicable). For example, if querying for itemid 225794 (“Non-invasive Ventilation”), then the value column indicates the duration of ventilation therapy. |
| `valueuom` | VARCHAR(20) | TEXT | The unit of measurement for the value. Most frequently “None” (no value recorded); otherwise one of “day”, “hour”, or “min”. A query for itemiid 225794 (“Non-invasive Ventilation”) returning a value of 461 and valueuom of ‘min’ would correspond to non-invasive ventilation provided for 461 minutes; this value is expected to match the difference between the starttime and endtime fields for the record. A procedure with valueuom equal to “None” corresponds to a procedure which is instantaneous (e.g. intubation, patient transfer) or whose duration is not relevant (e.g. imaging procedures). For these records, there will be a difference of one second between starttime and endtime values. |
| `location` | VARCHAR(100) | TEXT | location and locationcategory provide information about where on the patient’s body the procedure is taking place. For example, the location might be ‘Left Upper Arm’ and the locationcategory might be ‘Invasive Venous’. |
| `locationcategory` | VARCHAR(50) | TEXT | location and locationcategory provide information about where on the patient’s body the procedure is taking place. For example, the location might be ‘Left Upper Arm’ and the locationcategory might be ‘Invasive Venous’. |
| `orderid` | INTEGER | TEXT | These columns link procedures to specific physician orders. Unlike in the mimic_icu.inputevents table, most procedures in procedureevents are ordered independently. There are a limited number of records for which the same procedure was performed again at a later date under the same original order. When a procedure was repeated under the same original order, the linkorderid field of the record for the later procedure will be set to the orderid field of the earlier record. In all other cases, orderid = linkorderid . |
| `linkorderid` | INTEGER | TEXT | These columns link procedures to specific physician orders. Unlike in the mimic_icu.inputevents table, most procedures in procedureevents are ordered independently. There are a limited number of records for which the same procedure was performed again at a later date under the same original order. When a procedure was repeated under the same original order, the linkorderid field of the record for the later procedure will be set to the orderid field of the earlier record. In all other cases, orderid = linkorderid . |
| `ordercategoryname` | VARCHAR(50) | TEXT | These columns provide higher level information about the medication/solution order. Categories represent the type of administration. |
| `ordercategorydescription` | VARCHAR(30) | TEXT | These columns provide higher level information about the medication/solution order. Categories represent the type of administration. |
| `patientweight` | DOUBLE PRECISION | TEXT | The patient weight in kilograms. |
| `isopenbag` | SMALLINT | TEXT | Whether the order was from an open bag. |
| `continueinnextdept` | SMALLINT | TEXT | If the order ended on patient transfer, this field indicates if it continued into the next department (e.g. a floor). |
| `statusdescription` | VARCHAR(20) | TEXT | statusdescription states the ultimate status of the procedure referred to in the row. The statuses appearing on the procedureevents table are: Paused - The current delivery has been paused. FinishedRunning - The delivery of the item has finished (most frequently, the bag containing the compound is empty). Stopped - The delivery of the item been terminated by the caregiver. Nearly all procedures recorded in procedureevents have a status of FinishedRunning . |
| `ORIGINALAMOUNT` | DOUBLE PRECISION | TEXT | These fields are present in the table and never null, but have no clear meaning. In particular, “originalrate” is either 0 or 1 for all records. |
| `ORIGINALRATE` | DOUBLE PRECISION | TEXT | These fields are present in the table and never null, but have no clear meaning. In particular, “originalrate” is either 0 or 1 for all records. |

## procedures_icd

Official table documentation: [https://mimic.mit.edu/docs/iv/modules/hosp/procedures_icd.html](https://mimic.mit.edu/docs/iv/modules/hosp/procedures_icd.html)

*No verified table summary*

| Column | Native type | SQLite type | Description |
|---|---|---|---|
| `subject_id` | INTEGER NOT NULL | TEXT | subject_id is a unique identifier which specifies an individual patient. Any rows associated with a single subject_id pertain to the same individual. |
| `hadm_id` | INTEGER NOT NULL | TEXT | hadm_id is an integer identifier which is unique for each patient hospitalization. |
| `seq_num` | INTEGER NOT NULL | TEXT | An assigned priority for procedures which occurred within the hospital stay. |
| `chartdate` | DATE NOT NULL | TEXT | The date of the associated procedures. Date does not strictly correlate with seq_num . |
| `icd_code` | VARCHAR(7) | TEXT | icd_code is the International Coding Definitions (ICD) code. There are two versions for this coding system: version 9 (ICD-9) and version 10 (ICD-10). These can be differentiated using the icd_version column. In general, ICD-10 codes are more detailed, though code mappings (or “cross-walks”) exist which convert ICD-9 codes to ICD-10 codes. Both ICD-9 and ICD-10 codes are often presented with a decimal. This decimal is not required for interpretation of an ICD code; i.e. the icd_code of ‘0010’ is equivalent to ‘001.0’. |
| `icd_version` | INTEGER | TEXT | icd_code is the International Coding Definitions (ICD) code. There are two versions for this coding system: version 9 (ICD-9) and version 10 (ICD-10). These can be differentiated using the icd_version column. In general, ICD-10 codes are more detailed, though code mappings (or “cross-walks”) exist which convert ICD-9 codes to ICD-10 codes. Both ICD-9 and ICD-10 codes are often presented with a decimal. This decimal is not required for interpretation of an ICD code; i.e. the icd_code of ‘0010’ is equivalent to ‘001.0’. |

## provider

Official table documentation: [https://mimic.mit.edu/docs/iv/modules/hosp/provider.html](https://mimic.mit.edu/docs/iv/modules/hosp/provider.html)

*No verified table summary*

| Column | Native type | SQLite type | Description |
|---|---|---|---|
| `provider_id` | VARCHAR(10) NOT NULL | TEXT | provider_id lists all possible identifiers for providers used throughout the database. Provider identifiers follow a consistent pattern: the letter “P”, followed by either three numbers, followed by two letters or two numbers. For example, “P003AB”, “P00102”, “P1248B”, etc. Provider identifiers are randomly generated and do not have any inherent meaning aside from uniquely identifying the same provider across the database. |

## services

Official table documentation: [https://mimic.mit.edu/docs/iv/modules/hosp/services.html](https://mimic.mit.edu/docs/iv/modules/hosp/services.html)

*No verified table summary*

| Column | Native type | SQLite type | Description |
|---|---|---|---|
| `subject_id` | INT | TEXT | subject_id is a unique identifier which specifies an individual patient. Any rows associated with a single subject_id pertain to the same individual. |
| `hadm_id` | INT | TEXT | hadm_id is an integer identifier which is unique for each patient hospitalization. |
| `transfertime` | TIMESTAMP(0) | TEXT | transfertime is the time at which the patient moved from the prev_service (if present) to the curr_service . |
| `prev_service` | VARCHAR(20) | TEXT | prev_service and curr_service are the previous and current service that the patient resides under. |
| `curr_service` | VARCHAR(20) | TEXT | prev_service and curr_service are the previous and current service that the patient resides under. |

## transfers

Official table documentation: [https://mimic.mit.edu/docs/iv/modules/hosp/transfers.html](https://mimic.mit.edu/docs/iv/modules/hosp/transfers.html)

*No verified table summary*

| Column | Native type | SQLite type | Description |
|---|---|---|---|
| `subject_id` | INTEGER NOT NULL | TEXT | Identifiers which specify the patient: subject_id is unique to a patient, hadm_id is unique to a patient hospital stay, and transfer_id is unique to a patient physical location. Note that stay_id present in the icustays and edstays tables is derived from transfer_id . For example, three contiguous ICU stays will have three separate transfer_id for each distinct physical location (e.g. a patient could move from one bed to another). The entire stay will have a single stay_id , whih will be equal to the transfer_id of the first physical location. |
| `hadm_id` | INTEGER | TEXT | Identifiers which specify the patient: subject_id is unique to a patient, hadm_id is unique to a patient hospital stay, and transfer_id is unique to a patient physical location. Note that stay_id present in the icustays and edstays tables is derived from transfer_id . For example, three contiguous ICU stays will have three separate transfer_id for each distinct physical location (e.g. a patient could move from one bed to another). The entire stay will have a single stay_id , whih will be equal to the transfer_id of the first physical location. |
| `transfer_id` | INTEGER NOT NULL | TEXT | Identifiers which specify the patient: subject_id is unique to a patient, hadm_id is unique to a patient hospital stay, and transfer_id is unique to a patient physical location. Note that stay_id present in the icustays and edstays tables is derived from transfer_id . For example, three contiguous ICU stays will have three separate transfer_id for each distinct physical location (e.g. a patient could move from one bed to another). The entire stay will have a single stay_id , whih will be equal to the transfer_id of the first physical location. |
| `eventtype` | VARCHAR(10) | TEXT | eventtype describes what transfer event occurred: ‘ed’ for an emergency department stay, ‘admit’ for an admission to the hospital, ‘transfer’ for an intra-hospital transfer and ‘discharge’ for a discharge from the hospital. |
| `careunit` | VARCHAR(255) | TEXT | The type of unit or ward in which the patient is physically located. Examples of care units include medical ICUs, surgical ICUs, medical wards, new baby nurseries, and so on. |
| `intime` | TIMESTAMP(0) | TEXT | intime provides the date and time the patient was transferred into the current care unit ( careunit ) from the previous care unit. outtime provides the date and time the patient was transferred out of the current physical location. |
| `outtime` | TIMESTAMP(0) | TEXT | intime provides the date and time the patient was transferred into the current care unit ( careunit ) from the previous care unit. outtime provides the date and time the patient was transferred out of the current physical location. |

