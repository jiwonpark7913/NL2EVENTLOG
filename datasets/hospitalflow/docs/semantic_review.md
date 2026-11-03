# Clinical-time and business-dictionary review

- Revision: 2026-11-03-semantics-revision. Applies to the current 12-table, 52-variable database; it supersedes earlier dictionary interpretations. All records remain synthetic. Validation also checks that its probes do not mutate the published DB or Gold.
- The review's 33-measurement and aligned-order-ID observations describe an earlier construction. The immediately preceding GitHub revision already had 62 measurements, randomized order IDs, separate dispensing records and procedure_episode. The remaining clinical-time and NULL issues were confirmed against that newer revision.

| Issue | Current resolution |
| --- | --- |
| Laboratory charttime | Specimen collection time, following the usual acquisition-time interpretation in MIMIC. It is not measurement execution time. Every result row now follows collection < receipt < result availability < verification. |
| Activity label | Specimen Collected replaces Lab Measurement Charted. H03/Q2, full-lifecycle scopes, ES, SQL and all affected Gold logs were regenerated. Physical LABEV:<id>:chart occurrence identifiers continue to identify the charttime source column. |
| NULL clinical timestamps | Exactly one interpretation: no time is recorded; occurrence status is unknown. No inference that discharge, completion or ED registration did or did not happen is authorized by NULL alone. |
| NULL structural references | lab_order.hadm_id means no associated admission; an unused order_history FK means another order category applies. These are not missing clinical occurrence times. |
| Creation-language leakage | Removed the simulation phrasing from variable definitions and NULL meanings. Construction guidance and documentation-method commentary are in author docs, not the model dictionary. |
| Dispensing grain | Each pharmacy row is one individual dispensing with its own pharmacy_id and dispensed_at. A prescription can have multiple rows; this is not a first-dispensing summary timestamp. |
| Constant summary_status | Removed the constant SIGNED column. admission_detail stores signed summaries; draft documents are outside the table. |
| Summary signing sequence | All five summaries are signed after the associated discharge, with variable delays. No new draft workflow was added. |
| ICU source interpretation | Hospital-level procedure_episode remains distinct from MIMIC ICU procedureevents. Its definitions and source notes explicitly exclude the ICU stay_id hierarchy. |
| Discharge CHECK and NULL | Documented that a NULL authorization time produces UNKNOWN and passes SQLite CHECK even when discharge is recorded. Authorization is not a mandatory field for discharge. The NULL branch was exercised on an in-memory copy of the exact executable schema. |
| Identifier overlap | Revalidated: order_id never equals its admission ID. The three independent order namespaces retain three intentionally shared local values; these link to different requests. |
| Identity evidence and ablation | Full business evidence remains available, with repeated order-identity warning sentences removed. Concise and no-dictionary inputs are generated alongside it using identical data, questions and Gold. No classifier result is claimed. |
| Dictionary meta text | Moved documentation guidance and standardization caveats to data_dictionary_profile.md. The model-facing full JSON omits documentation_basis; business MD retains only short basic context, table/column definitions and business rules. |

## Column-specific NULL meanings

| Table | Variable | NULL interpretation |
| --- | --- | --- |
| admissions | edregtime | No emergency department registration time is recorded. Whether an ED registration occurred is unknown. |
| admissions | discharge_authorized_at | No discharge authorization time is recorded. Whether authorization occurred is unknown. |
| admissions | dischtime | No discharge time is recorded. Whether discharge occurred is unknown; an ongoing stay cannot be inferred from NULL alone. |
| lab_order | hadm_id | No hospital admission is associated with this request, as in outpatient testing. |
| lab_order | specimen_received_at | No specimen receipt time is recorded. Whether receipt occurred is unknown. |
| lab_order | results_verified_at | No results-verification time is recorded. Whether verification occurred is unknown. |
| medication_order | stopped_at | No prescription stop time is recorded. Whether stopping occurred is unknown. |
| procedure_order | preparation_completed_at | No preparation completion time is recorded. Whether completion occurred is unknown. |
| order_history | lab_order_id | The action concerns another order category; exactly one order-reference column is non-NULL. |
| order_history | medication_order_id | The action concerns another order category; exactly one order-reference column is non-NULL. |
| order_history | procedure_order_id | The action concerns another order category; exactly one order-reference column is non-NULL. |
| labevents | valuenum | No numeric measurement result is recorded. |
| labevents | valueuom | No measurement unit is specified. |
| procedure_episode | endtime | No procedure completion time is recorded. Whether completion occurred is unknown; an ongoing procedure cannot be inferred from NULL alone. |

## Executed checks

- All 62 laboratory rows satisfy the four-stage temporal order.
- All five discharge summaries are signed after discharge.
- All 42 persisted Gold CSVs match their SQL results and independently emitted generation histories; Q1/Q2 and Q3/Q4 remain exact scope pairs.
- Full dictionary matches the executable schema. Concise dictionary is derived from the reviewed business facts; no-dictionary input contains no dictionary file.
- Existing wrong-ID-join and unrelated fan-out controls still detect their specified errors.
- [Machine-readable checks](realism_validation.json) · [Dictionary ablation inputs](dictionary_ablation_inputs.json) · [Business dictionary](data_dictionary.md)

## Sources

- [MIMIC labevents charttime](https://mimic.mit.edu/docs/iv/modules/hosp/labevents.html#charttime): charted time is usually specimen acquisition; storetime is result availability. HospitalFlow explicitly adopts collection time rather than claiming that every real MIMIC record obeys this clean ordering.
- [MIMIC ICU procedureevents](https://mimic.mit.edu/docs/iv/modules/icu/procedureevents.html): timing concepts only; HospitalFlow omits the ICU stay hierarchy and uses the separately named hospital-level procedure_episode table.
- [SQLite CHECK constraints](https://www.sqlite.org/lang_createtable.html#check_constraints): NULL does not violate a CHECK expression.
