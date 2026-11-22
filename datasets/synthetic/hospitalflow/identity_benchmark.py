"""Author identity ground truth and documentation; never infer groups or run Step 2."""
import json,itertools
from pathlib import Path

def write_identity_gold(p,con,physical,sources):
 def js(n,v):(p/n).write_text(json.dumps(v,indent=2)+'\n')
 groups={}
 for t,(typ,prefix,key) in physical.items():groups.setdefault(typ,[]).append(dict(table=t,primary_key=[key],canonical_key_prefix=prefix))
 pairs=[]
 for a,b in itertools.combinations(physical,2):
  ta,_,ka=physical[a];tb,_,kb=physical[b];sa={r[0] for r in con.execute('SELECT '+ka+' FROM '+a)};sb={r[0] for r in con.execute('SELECT '+kb+' FROM '+b)};n=len(sa&sb);same=ta==tb
  pairs.append(dict(tables=[a,b],primary_keys=[[ka],[kb]],expected_same_object_type='YES' if same else 'NO',expected_same_key_namespace='YES' if same else 'NO',expected_decision='MERGE' if same else 'SEPARATE',evidence_refs=['dictionary:'+a+'.'+ka,'dictionary:'+b+'.'+kb,'dictionary:table:'+a,'dictionary:table:'+b],reason='Explicit definitions identify the same actual patient/admission in the same identifier namespace; supplementary rows are optional.' if same else 'The complete primary keys identify different business entities or occurrence records. Equal integer values or foreign keys do not establish instance identity.',key_statistics=dict(count_A=len(sa),count_B=len(sb),intersection_count=n,overlap_min=n/min(len(sa),len(sb)) if sa and sb else None,coverage_A=n/len(sa) if sa else None,coverage_B=n/len(sb) if sb else None,scope='Full key sets, no sampling; complete single-column PKs, exact comparison, no lossy normalization.')))
 js('private/identity_gold.json',dict(scope='Author-assigned evaluation ground truth, not predictions from an implemented identity judge.',physical_object_count=len(physical),expected_group_count=len(groups),expected_group_reduction=len(physical)-len(groups),groups=[dict(object_type=k,members=v) for k,v in groups.items()],pair_count=len(pairs),expected_decision_counts={d:sum(x['expected_decision']==d for x in pairs) for d in ['MERGE','SEPARATE','UNRESOLVED']},pairs=pairs))
 js('private/identity_edge_cases.json',dict(scope='Isolated authored test specifications; not extra live HospitalFlow tables or measured classifier results.',cases=[dict(name='independent_patient_namespace',same_object_type='YES',same_key_namespace='NO',mapping='ABSENT',expected_decision='UNRESOLVED',definition='Two patient systems independently allocate integer IDs; no correspondence is supplied.'),dict(name='partial_overlap_without_identity_documentation',same_object_type='UNKNOWN',same_key_namespace='UNKNOWN',mapping='ABSENT',expected_decision='UNRESOLVED',definition='Two full 1000-key sets share 300 keys; overlap alone is insufficient.'),dict(name='empty_identity_evidence',keys_A=[],keys_B=[],coverage_A=None,coverage_B=None,overlap_min=None,expected_decision='UNRESOLVED'),dict(name='composite_key_partial_match',pk_A=['patient_id','visit_sequence'],pk_B=['patient_id'],expected_decision='SEPARATE',definition='An admission is not its patient; do not discard visit_sequence.'),dict(name='mapping_group_conflict',edges=['A-B supported','B-C supported','A-C contradicted'],expected_decision='UNRESOLVED',definition='Do not take transitive closure through a conflict.')]))
 # Exact physical own-object contracts, separate from downstream case attribution.
 bindings=[]
 for source in sources:
  t=source['table'];bindings.append(dict(**source,physical_object=dict(table=t,primary_key=physical[t][2]),own_object_type=physical[t][0],own_path='Own physical row; grouping preserves complete PK and event occurrence identity.',fk_attribution={'emar':'emar.pharmacy_id → pharmacy.pharmacy_id → pharmacy.order_id → medication_order.order_id → admissions.hadm_id → patients.subject_id. Dose and dispensing identities remain separate.', 'pharmacy':'pharmacy.order_id → medication_order.order_id → admissions.hadm_id → patients.subject_id. Dispensing identity is distinct from prescription.', 'lab_order':'lab_order.subject_id → patients.subject_id; optional lab_order.hadm_id → admissions.hadm_id. NULL admission does not remove patient attribution.', 'labevents':'labevents.order_id → lab_order.order_id → patients.subject_id; optional admission via lab_order.hadm_id.'}.get(t,'Own identity preserved. Declared order FKs lead to admissions and patients; patient_profile and admission_detail use the documented shared parent namespace.')))
 js('private/event_binding_provenance.json',bindings)
 for old in ['docs/object_type_membership.json']:(p/old).unlink(missing_ok=True)

def write_docs(p,r,coverage,enc,stats):
 (p/'docs/object_type_verification.md').write_text('''# Physical Object → Object Type identity benchmark

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
''')
