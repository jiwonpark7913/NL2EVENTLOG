"""Business-only dictionary and structural ERD; author answers live in README."""
from pathlib import Path
import json,runpy,sqlite3,csv
SHARED=runpy.run_path(str(Path(__file__).resolve().parents[1]/'plateflow/documentation.py'))
mdtable=SHARED['mdtable']
render_dictionary=SHARED['render_dictionary']

def render(p,con,d,report,questions,coverage,classification):
 render_dictionary(p,con,d)
 order=[['warehouse','goods','worker'],['receiving_request','work_code','dispatch_order'],['goods_receipt','request_action','warehouse_audit'],['goods_movement','warehouse_task_history','handling_history']]
 SHARED['diagram'](p,con,d,order=order)
 stats=[]
 for typ in ['Q1','Q2','Q3','Q4']:
  qs=[q for q in questions if q['question_type']==typ];stats.append([typ,len(qs),sum(q['answerability']=='answerable' for q in qs),sum(q['answerability']!='answerable' for q in qs),f"{sum(q['requested_activity_count'] for q in qs)/len(qs):.2f}"])
 statstable=mdtable(['Type','Questions','Answerable','Non-answerable','Avg. requested activity labels'],stats)
 (p/'docs/questions.md').write_text('# WarehouseFlow New questions\n\n## Question types and pairs\n\n'+statstable+'\n- Start/completion labels are counted separately here; base work identity is preserved separately in private event metadata. Averages include unsupported requests.\n- Q1/Q3 seeds are frozen before the assistant LLM creates Q2/Q4. Each pair has the same scope, phase selection, ES and CSV.\n\n'+mdtable(['ID','Type','Paired with','Answerability','Requested labels','Extractable labels','Requested base activities','Extractable base activities','Question'],[[q['question_id'],q['question_type'],q['pair_of'],q['answerability'],q['requested_activity_count'],q['extractable_activity_count'],q['requested_base_activity_count'],q['extractable_base_activity_count'],q['text']] for q in questions]))
 scope=mdtable(['Case type','Cases','Base activity types','Phase-specific labels','Empty cases','Default recorded scope'],[[c['case_concept'],c['case_count'],c['base_activity_count'],c['activity_count'],c['cases_without_events'],', '.join(c['activities'])] for c in coverage]);(p/'docs/object_activity_design.md').write_text('# Objects, activities and situations\n\n'+scope+'\n- Warehouse and goods views aggregate independent jobs. Worker views include only directly recorded work/receipt/audit/action participation.\n- Work and audit records retain their own identities and their separate start and completion instants. No completion is fabricated for an open occurrence.\n')
 (p/'docs/object_event_logs.md').write_text('# Full recorded lifecycle Gold logs\n\n'+mdtable(['Case type','Q3','Q4','Cases','Event rows'],[[c['case_concept'],'WF'+str(i).zfill(2),'WF'+str(i).zfill(2)+'P',c['case_count'],c['event_rows']] for i,c in enumerate(coverage,1)])+'\n- Empty cases remain in private/case_population.json and Gold ES populations. CSV files are case-based logs, not OCEL.\n')
 inv=json.loads((p/'docs/timestamp_columns.json').read_text());(p/'docs/timestamp_columns.md').write_text('# Timestamp inventory — author evaluation material\n\n'+mdtable(['Table','Column','Role','Selected as Gold time','Non-null rows'],[[r['table'],r['column'],r['role'],r['used_as_event_time'],r['non_null_rows']] for r in inv['columns']]))
 count=mdtable(['Dataset','Tables','Object / case types','Activity types','Timestamp columns','Event timestamp columns','Distinct events','Questions','Gold CSVs'],[['WarehouseFlow New',len(report['table_rows']),report['semantic_object_types'],report['activity_type_count'],inv['timestamp_columns'],inv['event_timestamp_columns'],report['events'],report['total_questions'],report['answerable_questions']]])
 answers=mdtable(['Table','Case A–D','Base activity identity','Activity carrier','Stored and emitted phase'],[[t,*classification[t]] for t in dnames(d)])
 readme='''# WarehouseFlow New dataset

- **Purpose:** evaluate timestamp-bearing event candidates using two separate axes: physical identification of base activity, and occurrence timestamp phase.
- **Domain:** synthetic warehouse receiving, dispatch, stock movement, handling and audits. Original WarehouseFlow/RSchema warehouse, goods and worker roles informed the domain; new table structures and all rows are authored.
- **Build:** `python datasets/warehouseflow_new/build.py`. **Validate:** `python datasets/warehouseflow_new/validate.py` from the repository root. Standard-library simulation; PyMuPDF for PNG rendering.

'''+count+f"\n- **Base activity identities:** {len(report['base_activity_counts'])}. **Phase-specific display labels:** {len(report['activity_counts'])}. These are different counts; they must not be conflated.\n"+'''
## Table classification and activity carriers — author reference only

- Timestamp presence proposes a candidate; technical warehouse/worker maintenance times are not business occurrences.
- A code is an activity carrier only if its values select different kinds of action. Goods category, worker role, dispatch urgency, goods condition, audit result and task outcome are not carriers.
- Base activity identity and occurrence phase remain separate. Case D uses Row identity with start/complete timestamp bindings; it may be described as a mixed representation only if both axes are retained.
- This dataset deliberately has 2 tables for each case A–D plus 4 context/reference tables. There is no classification or carrier answer in the model-facing dictionary.

'''+answers+'''
- **A:** receiving_request and goods_receipt each have one actual timestamp and no activity carrier. A receipt condition code does not change the fixed receipt-registration activity.
- **B:** dispatch_order stores separate request/approval milestones without an activity carrier. warehouse_audit stores the start and completion of one Stock Audit occurrence; PASS/RECOUNT are outcomes, not extra activity kinds.
- **C:** goods_movement.movement_code selects inbound/outbound work using one occurred_at. request_action.action_code selects checking/holding/releasing using one occurred_at.
- **D:** warehouse_task_history.task_code selects Putaway/Picking/Packing and handling_history.handling_code selects Unloading/Loading; each occurrence has started_at and optional completed_at. Both actual phases are emitted.
- Fixed code_family values provide namespace context, not a second varying activity selector.
- A context table may still define a case population: warehouse, goods and worker timelines obtain actual occurrences through business-key paths from other tables.

## Phase and occurrence contract

- `base_activity` identifies the work kind, e.g. Picking. `lifecycle_phase` is start, complete or point. `occurrence_id` identifies the original work/audit occurrence. These evaluator fields are in private/canonical_history.jsonl and Gold bindings.
- Display labels such as Picking Started and Picking Completed share the same base_activity and occurrence_id but have different event_id values. They are not duplicate events or two unrelated work kinds.
- Exported CSV columns remain event_id, case_id, activity, timestamp. Phase identity is never reconstructed by stripping label suffixes during validation; it comes from independent simulation and source bindings.
- An unfinished occurrence produces its recorded start, not a fabricated completion. A repeated picking attempt has a new task_id and occurrence_id, even if its base activity and parent order are the same.
- Start/end handling is intentional in this variant. The existing PlateFlow New variant retains its earlier completion-only extraction contract; its README explains the resulting A–D coverage gaps.

## Objects, activities and situations

'''+scope+'''
- Scenarios include held receiving requests, repeat checks, unfinished unloading and putaway, unapproved dispatches, repeat picking, unfinished packing/loading, completed/recount/pending audits and idle warehouses/goods/workers.
- Each request/order concerns one goods type. This controlled sample excludes line-item splitting, invoicing and carrier delivery.
- Stock receipts and dispatches are separate from receipt registration. They are distinct recorded business actions with distinct occurrence IDs. Stock never becomes negative or exceeds warehouse capacity.
- Full lifecycle means the declared scope in input/task_context.md. A request/order connects to work through real FK paths; workers connect only through recorded participation. Case scopes do not automatically include all actions of a shared warehouse or worker.
- [Object-specific Gold logs](docs/object_event_logs.md)

## Question types and pairs

'''+statstable+'''
- Q1/Q2 explicitly name or paraphrase requested activity labels and phases. Q3/Q4 ask for the full recorded lifecycle without listing activities.
- Pairs preserve base-work and phase scope, case population, answerability, ES and exact CSV contents. Average requested labels include unsupported requests.
- [Questions and counts](docs/questions.md) · [Frozen LLM prompts and outputs](source/llm_paraphrases.json)

## Model input boundary

- Supply only input/model_input_manifest.json's allowlist: database, SQL schema, ordinary business dictionary, source-agnostic task context and question text.
- No event-table classification, row/column labels, carrier annotations, phase-selection answers, case bindings or Gold scope catalog are exported in dictionary JSON/Markdown/CSV.
- The dictionary legitimately describes what codes, business times and outcomes mean. The model must infer which codes select activity and which times represent occurrence phases from that evidence.
- README, source, design, docs, private, build code and validation reports are author/evaluation material. private/questions.jsonl carries question-type/answerability/count annotations; private/gold.jsonl and mappings are extraction answers. Exclude them from model context.

## Schema and documentation

![Schema](docs/schema.png)

- [Editable draw.io diagram](docs/schema.drawio)
- [Table inventory and FK relationships](docs/schema_overview.md)
- [Three-part business dictionary](docs/data_dictionary.md) · [Dictionary CSV](docs/data_dictionary.csv) · [Table definitions CSV](docs/table_definitions.csv)
- [Author timestamp inventory](docs/timestamp_columns.md)
- [Source adaptation](design/source_mapping.json) · [Validation report](validation_report.json)

## Validation scope

- Compare every SQL/CSV against independently emitted simulation history. Check source PK, code meaning, phase time, own/FK attribution, same-occurrence phase pairs, repeat attempts, unfinished starts, stock balance, key constraints, input leakage and frozen question pairs.
- This validates dataset consistency and the A–D test cases. No learned or LLM classifier has been executed, and no discovery/classification accuracy is claimed.
'''
 (p/'README.md').write_text(readme)
def dnames(d):return [t['table'] for t in d['tables']]
if __name__=='__main__':
 from build import CLASSIFICATION
 p=Path(__file__).resolve().parent;con=sqlite3.connect(p/'input/database.sqlite');con.row_factory=sqlite3.Row;d=json.loads((p/'input/data_dictionary.json').read_text());r=json.loads((p/'validation_report.json').read_text());q=[json.loads(s) for s in (p/'private/questions.jsonl').read_text().splitlines()];render(p,con,d,r,q,r['object_view_coverage'],CLASSIFICATION);con.close()
