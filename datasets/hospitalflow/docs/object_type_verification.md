# Physical Object → Object Type identity benchmark

- No generic object or object_type tables are used. Group labels are private evaluation answers.

| Physical Objects | Interpretation | Expected decision |
|---|---|---|
| patients / patient_profile | Same patient; same subject_id namespace; optional extension; no FK | MERGE |
| admissions / admission_detail | Same admission; same hadm_id namespace; optional extension; shared-PK FK | MERGE |
| lab_order / medication_order / procedure_order | Different requests; independent local ID namespaces | SEPARATE |
| order_history / any referenced order | History occurrence versus order instance | SEPARATE |
| labevents / lab_order | Measurement occurrence versus order instance | SEPARATE |

- These author-assigned expectations are grounded in input/data_dictionary.json. Overlap is supporting evidence rather than an automatic merge threshold.
- Profile coverage is 6/12 and summary coverage is 5/15; each pair has overlap_min=1.0. Neither requires bidirectional 95% coverage or equal key sets.
- Patient and Hospital Admission questions combine events from the corresponding split tables through compatible identities. Different occurrence events remain distinct, and other objects connect through explicit business FKs.

```sql
SELECT p.subject_id, p.gender, d.profile_verified_at
FROM patients p LEFT JOIN patient_profile d ON d.subject_id=p.subject_id;

SELECT a.hadm_id, a.admittime, d.discharge_summary_signed_at
FROM admissions a LEFT JOIN admission_detail d ON d.hadm_id=a.hadm_id;
```

- H09/H09P and H11/H11P test patient profile events; H10/H10P tests admission detail events. Full lifecycle pairs HF01/HF01P and HF02/HF02P cover the combined physical sources.
- Gold pair assignments: private/identity_gold.json. Isolated uncertain/boundary specifications: private/identity_edge_cases.json.
- These are executable extraction and dataset-consistency tests, not an implementation or evaluation of the separate Step 2 classifier.
