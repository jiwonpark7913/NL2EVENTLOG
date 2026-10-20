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
  t=source['table'];bindings.append(dict(**source,physical_object=dict(table=t,primary_key=physical[t][2]),own_object_type=physical[t][0],own_path='Own physical row; grouping preserves complete PK and event occurrence identity.',fk_attribution='FK to the corresponding order, then its admission and patient. Own-row history/measurement/dose/episode identities remain separate.' if t in ['order_history','labevents','emar','procedureevents'] else 'Own identity; orders use their declared admission FK, and admissions use subject_id. Split profile/admission detail share the explicitly documented parent namespace.'))
 js('private/event_binding_provenance.json',bindings)
 for old in ['docs/object_type_membership.json']:(p/old).unlink(missing_ok=True)

def write_docs(p,r,coverage,enc,stats):
 def table(h,rows):return '| '+' | '.join(h)+' |\n| '+' | '.join(['---']*len(h))+' |\n'+''.join('| '+' | '.join(map(str,row))+' |\n' for row in rows)
 intro='''# HospitalFlow dataset

- **Purpose:** evaluate whether different Physical Objects represent the SAME business object type with compatible instance identity.
- **Source:** public MIMIC-IV documentation with wholly synthetic records. Split-storage extensions are authored, not original MIMIC tables.
- The database contains ordinary hospital business tables. It has no object, object_type or clinical_order registry/supertype table and no persisted generic object/type identifier.

'''
 t=r['timestamp_summary'];intro+=table(['Dataset','Tables','Object / case types','Activity types','Timestamp columns','Event timestamp columns','Distinct events','Questions','Gold CSVs'],[['HospitalFlow',len(r['table_rows']),r['semantic_object_types'],len(r['activity_counts']),t['timestamp_columns'],t['event_timestamp_columns'],r['events'],r['total_questions'],r['answerable_questions']]])
 intro+=f"\n- **Physical Objects:** {r['physical_objects']} table/PK representations. **Expected identity-compatible groups:** {r['identity_groups']}. **Distinct business/occurrence instances:** {r['object_instances']}.\n"
 intro+='''
## Identity grouping scenarios

- patients and patient_profile store different information about the SAME patient. The subject_id namespace is shared; 6 of 12 patients have profile rows. There is intentionally no FK between these tables; the dictionary explicitly documents the identifier relationship.
- admissions and admission_detail store different information about the SAME hospital stay. Their hadm_id namespace is shared, corroborated by a shared-PK FK; 5 of 15 admissions have supplementary summary records.
- Patient Profile Verified originates in patient_profile; admission events originate in admissions and Discharge Summary Signed originates in admission_detail. Grouping does not erase the physical source or collapse different events.
- lab_order, medication_order and procedure_order identify different requests. Their local order_id values overlap deliberately; this does not justify grouping them as one identity-compatible type.
- order_history.history_id identifies a history occurrence. Its order FK does not make it the same object as an order. Measurement, dose and procedure episode records also keep their own identities.
- **Gold grouping:** 11 Physical Objects → 9 groups, with exactly two expected MERGE pairs. The pair labels are reference answers, not results of running the user's Step 2 implementation.
- [Grouping examples and evaluation boundary](docs/object_type_verification.md)

## Scenarios and activities

'''+(p/'docs/object_activity_design.md').read_text().split('\n\n',1)[1]
 intro+='\n## Event storage\n\n'+table(['Table','Encoding'],enc.items())+'''
- Row tables preserve repeat actions. Column tables store actual one-time milestones. Mixed tables preserve repeat occurrences and distinct milestone times within each occurrence.
- Only identical case/event occurrences are deduplicated; grouping never merges different event IDs.

## Question types and pairs

'''+stats+'''
- Q1/Q3 seeds are frozen before the assistant LLM creates Q2/Q4. Prompts, outputs and review notes are stored in source/llm_paraphrases.json. No external API call is claimed.
- Each pair has identical scope, answerability, ES and Gold. Unsupported pairs have no CSV.
- [Questions, counts and requested activities](docs/questions.md)

## Model input and evaluation answers

- Model inputs: input/database.sqlite, input/schema.sql, input/data_dictionary.json and input/model_questions.jsonl.
- Optional input/task_scope_catalog.json declares default activity scopes only. It omits table memberships, namespace answers and instance populations. Evaluating identity without a scope catalog is also possible.
- private/identity_gold.json contains author-assigned table/PK grouping answers and full-key statistics. It must not be provided to the identity judge.
- private/event_binding_provenance.json records each source table, complete PK and own versus FK attribution. private/case_population.json and private/object_event_links.json are Gold annotations.
- design/, docs/ and this README include construction explanations and answers; exclude them from model inputs. The data dictionary is legitimate input evidence and explicitly describes identifier semantics without supplying final MERGE/SEPARATE labels.
- Main-schema gold pairs cover two positive split-storage cases and distinct-identity negatives. UNRESOLVED and group-conflict scenarios are separately specified in private/identity_edge_cases.json; these are not claimed live-table cases or executed semantic-judge tests.

## Build and validation

- Run `python datasets/hospitalflow/build.py`, `python make_docs.py`, `python question_summary.py`, `python validate_lifecycles.py` and `python validate_timestamp_columns.py` from the repository root.
- SQL/CSV outputs are compared with independent generation-time histories. Tests check identity groups, optional extensions, no-FK identity evidence, order/history separation, own/FK provenance, time order, repeated occurrences, empty cases and frozen question pairs.
- The NL2EventLog Step 2 identity classifier is not present in this dataset repository. This provides test inputs and Gold answers; it does not claim measured classifier accuracy, LLM identity decisions or candidate/decision audit statistics.
- [Construction plan](design/plan.md)
- [Source mapping](design/source_mapping.json)
- [Source references](source/references.md)
- [Object-specific Gold logs](docs/object_event_logs.md)
'''
 (p/'README.md').write_text(intro)
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
