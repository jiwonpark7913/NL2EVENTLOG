"""English, schema-informed PlateFlow v2. Python 3.10+, standard library."""
import json,csv,sqlite3,random
from pathlib import Path
from datetime import datetime,timedelta,timezone
from collections import Counter
P=Path(__file__).resolve().parent
def write(n,s):
 p=P/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s,encoding="utf-8")
def js(n,o):write(n,json.dumps(o,indent=2)+"\n")
def jl(n,o):write(n,"".join(json.dumps(r)+"\n" for r in o))
def c(n,ty,co,d,orig=None):return dict(name=n,type=ty,constraints=co,definition=d,source_column=orig)
T={}
def table(n,source,definition,cols):T[n]=dict(table=n,source_table=source,definition=definition,columns=cols)
table("slab_material","TB_M2EA08_C_MTL060","Slab material and charge genealogy; no upstream operation timestamps in this subset",[
 c("slab_id","TEXT","PRIMARY KEY","Synthetic slab identity","MTL_NO"),
 c("charge_id","TEXT","NOT NULL","Upstream charge identity, contextual attribute","CHARGE_NO")])
table("planned_rolling_instruction","TB_M2LB01_D_PLANINST010","Scheduled rolling instruction; plan times do not prove execution",[
 c("plan_id","TEXT","PRIMARY KEY","Plan identity","PLATE_HR_WORK_DIR_ID"),
 c("slab_id","TEXT","NOT NULL REFERENCES slab_material(slab_id)","Planned input slab","SLAB_NO"),
 c("planned_reheat_at","TEXT","NOT NULL","Scheduled furnace charging time","PLT_RF_CH_SCHE_DT")])
table("rolling_instruction","TB_M2LM01_D_INST010","Released rolling work instruction, separate from planning",[
 c("instruction_id","TEXT","PRIMARY KEY","Synthetic row identity","WIP_ENTITY_ID"),
 c("plan_id","TEXT","NOT NULL UNIQUE REFERENCES planned_rolling_instruction(plan_id)","Synthetic explicit link to plan"),
 c("released_at","TEXT","NOT NULL","Actual instruction release time","OP_INDI_RELEASE_DT")])
table("as_rolled_material","TB_M2LM01_E_MTRL010","As-rolled mother material with milestone columns and latest-operation snapshot",[
 c("material_id","TEXT","PRIMARY KEY","Mother material identity","MTL_NO"),
 c("as_rolled_plate_no","TEXT","NOT NULL UNIQUE","Mother as-rolled plate number","AS_ROLLED_PLATE_NO"),
 c("slab_id","TEXT","NOT NULL UNIQUE REFERENCES slab_material(slab_id)","Source slab","SLAB_NO"),
 c("instruction_id","TEXT","NOT NULL UNIQUE REFERENCES rolling_instruction(instruction_id)","Synthetic explicit link to released instruction"),
 c("furnace_charged_at","TEXT","","Actual furnace material charging","RF_CH_DT"),
 c("crop_shear_passed_at","TEXT","","Actual crop-shear passage","PLT_CS_PPLT_DT"),
 c("latest_operation_completed_at","TEXT","","Snapshot of latest mother-material operation, not always rolling completion","PLT_AC_OP_END_OP_DT"),
 c("created_at","TEXT","NOT NULL","Technical database creation timestamp","CREATION_TIMESTAMP"),
 c("updated_at","TEXT","NOT NULL","Technical database update timestamp","LAST_UPDATE_TIMESTAMP")])
table("furnace_charge_tracking","TB_M2EA05_E_RF_IN060","Furnace charge tracking record separated from material lifecycle snapshot",[
 c("tracking_id","TEXT","PRIMARY KEY","Tracking occurrence ID","TRACKING_CODE"),
 c("material_id","TEXT","NOT NULL UNIQUE REFERENCES as_rolled_material(material_id)","Tracked material","MTL_NO"),
 c("yard_instruction_received_at","TEXT","NOT NULL","Actual yard instruction receipt","YD_INDI_RCP_DT"),
 c("lot_charging_started_at","TEXT","NOT NULL","Furnace lot charging start; different event granularity from material entry","HT_FCE_CH_LOT_CH_SAT_DT")])
table("cutting_finishing_instruction","TB_M2LM01_D_INST020","Cutting/finishing work instruction for mother material",[
 c("instruction_id","TEXT","PRIMARY KEY","Synthetic instruction ID","WIP_ENTITY_ID"),
 c("material_id","TEXT","NOT NULL UNIQUE REFERENCES as_rolled_material(material_id)","Directed mother material","MTL_NO"),
 c("released_at","TEXT","NOT NULL","Actual cutting/finishing instruction release","OP_INDI_RELEASE_DT"),
 c("cut_method","TEXT","NOT NULL CHECK(cut_method='SPLIT')","Synthetic split-cut method code","PL_CUT_METH")])
table("plate_material","TB_M2LM01_E_MTRL020","Individual cut Plate material, distinct from mother as-rolled material",[
 c("plate_material_id","TEXT","PRIMARY KEY","Finished-piece material identity","MTL_NO"),
 c("plate_no","TEXT","NOT NULL UNIQUE","Individual Plate number","PLATE_NO"),
 c("parent_as_rolled_plate_no","TEXT","NOT NULL REFERENCES as_rolled_material(as_rolled_plate_no)","Mother as-rolled plate number; synthetic FK policy","AS_ROLLED_PLATE_NO"),
 c("dimension_inspected_at","TEXT","","Actual dimensional inspection timestamp","SIZE_INSP_DATE"),
 c("latest_operation_completed_at","TEXT","","Latest piece operation snapshot","PLT_AC_OP_END_OP_DT")])
table("operation_code",None,"Synthetic operation code domain; codes are newly authored",[
 c("code","TEXT","PRIMARY KEY","Synthetic process code"),
 c("meaning","TEXT","NOT NULL UNIQUE","English operation meaning")])
table("material_operation_history","TB_M2LM01_T_OPERHIST","Immutable operation history for mother and piece material identities",[
 c("transaction_id","TEXT","PRIMARY KEY","Operation occurrence ID","TRANSACTION_ID"),
 c("material_id","TEXT","NOT NULL","Mother or piece material identity; validated against both material tables","MTL_NO"),
 c("operation_code","TEXT","NOT NULL REFERENCES operation_code(code)","Synthetic factory/process code","FAC_OP_CD_N"),
 c("started_at","TEXT","NOT NULL","Actual operation start time","OP_SAT_DT"),
 c("completed_at","TEXT","NOT NULL CHECK(completed_at > started_at)","Actual operation completion time","OP_DN_DT"),
 c("created_at","TEXT","NOT NULL","Technical record insertion time","CREATION_TIMESTAMP")])
CODES={"RL":"Rolling Completed","CO":"Cooling Completed","LE":"Leveling Completed","SC":"Split Cutting Completed","HT":"Heat Treatment Completed","IF":"Inspection Failed","IP":"Inspection Passed"}
def source(a,frm,case,ts,eid,pred=None):return dict(activity=a,from_expression=frm,case_id_expression=case,timestamp_expression=ts,event_id_expression=eid,predicate=pred)
S=[
 source("Rolling Instruction Released","rolling_instruction i JOIN as_rolled_material m ON i.instruction_id=m.instruction_id","m.material_id","i.released_at","'RI:' || i.instruction_id"),
 source("Yard Instruction Received","furnace_charge_tracking","material_id","yard_instruction_received_at","'YD:' || tracking_id"),
 source("Reheating Started","as_rolled_material","material_id","furnace_charged_at","'RH:' || material_id","furnace_charged_at IS NOT NULL"),
 source("Crop Shear Passed","as_rolled_material","material_id","crop_shear_passed_at","'CS:' || material_id","crop_shear_passed_at IS NOT NULL"),
 source("Cutting Instruction Released","cutting_finishing_instruction","material_id","released_at","'CI:' || instruction_id")]
# Resolve polymorphic history identity once to a mother case, with no mother-to-piece fanout.
RESOLVE="(SELECT material_id AS recorded_id, material_id AS case_id FROM as_rolled_material UNION ALL SELECT p.plate_material_id, m.material_id FROM plate_material p JOIN as_rolled_material m ON p.parent_as_rolled_plate_no=m.as_rolled_plate_no)"
S += [source(a,"material_operation_history h JOIN "+RESOLVE+" r ON h.material_id=r.recorded_id","r.case_id","h.completed_at","'OP:' || h.transaction_id","h.operation_code='"+co+"'") for co,a in CODES.items()]
S += [source("Dimensional Inspection Completed","plate_material p JOIN as_rolled_material m ON p.parent_as_rolled_plate_no=m.as_rolled_plate_no","m.material_id","p.dimension_inspected_at","'DIM:' || p.plate_material_id","p.dimension_inspected_at IS NOT NULL")]
def compile_es(es):
 parts=["SELECT "+s["event_id_expression"]+" event_id, "+s["case_id_expression"]+" case_id, '"+s["activity"]+"' activity, "+s["timestamp_expression"]+" timestamp FROM "+s["from_expression"]+(" WHERE "+s["predicate"] if s["predicate"] else "") for s in es["sources"]]
 return "SELECT * FROM ("+" UNION ALL ".join(parts)+") ORDER BY case_id,timestamp,event_id;"
def main():
 rng=random.Random(20261013)
 ddl="PRAGMA foreign_keys=ON;\n"+"\n".join("CREATE TABLE "+t+" ("+", ".join(c["name"]+" "+c["type"]+" "+c["constraints"] for c in d["columns"])+");" for t,d in T.items())
 # Two-domain material reference is a synthetic policy, not a declared source FK.
 ddl+="\nCREATE TRIGGER validate_history_material BEFORE INSERT ON material_operation_history WHEN NOT EXISTS(SELECT 1 FROM as_rolled_material WHERE material_id=NEW.material_id) AND NOT EXISTS(SELECT 1 FROM plate_material WHERE plate_material_id=NEW.material_id) BEGIN SELECT RAISE(ABORT,'Unknown material'); END;"
 write("input/schema.sql",ddl+"\n")
 rules=[
 "Plans, released instructions, tracking records, lifecycle snapshots, individual Plate records and operation history are separate.",
 "One slab supplies one mother material in this fixture. A completed mother material yields one to three individual Plate materials.",
 "Default mother-material lifecycle includes its own events and all recorded events of its descendant pieces; each occurrence is included once.",
 "Plan times, lot charging start and technical timestamps are not part of the selected default material lifecycle. Lot-level analysis is outside this fixture.",
 "Rolling completion is obtained from operation-history code RL, not from the latest-operation snapshot column.",
 "Operation history preserves repeated heat treatment and inspection. Dimensional inspection and general inspection decision are distinct activities.",
 "Completed route: rolling, cooling, leveling, crop-shear passage, cutting instruction, split cutting, piece-level treatment/inspection.",
 "Factory codes and cardinalities are synthetic assumptions. Original metadata does not declare data types, PK/FK or allowed code values.",
 "A mother-material identifier and a Plate-material identifier are distinct. The parent as-rolled plate number resolves lineage.",
 "No upstream casting or shipping timestamps are recorded."]
 d=dict(name="PlateFlow v2",language="en",timezone="UTC",tables=list(T.values()),code_domain=CODES,business_rules=rules)
 js("input/data_dictionary.json",d)
 md="# PlateFlow v2 English Data Dictionary\n\nSchema-informed synthetic subset; custom metadata profile.\n"
 for t in T.values():
  md+="\n## "+t["table"]+"\n\n"+t["definition"]+"\n\n| Column | Type | Constraints | Definition |\n|---|---|---|---|\n"
  md+="".join("| "+c["name"]+" | "+c["type"]+" | "+c["constraints"]+" | "+c["definition"]+" |\n" for c in t["columns"])
 md+="\n## Synthetic code domain\n\n"+"\n".join("- "+k+": "+v for k,v in CODES.items())
 md+="\n\n## Business rules\n\n"+"\n".join("- "+r for r in rules)+"\n";write("input/data_dictionary.md",md)
 js("design/logical_schema.json",list(T.values()))
 js("design/conceptual_model.json",dict(entities=list(T),relations=["Slab → Plan → Released rolling instruction → Mother material","Mother material → furnace tracking","Mother material → cutting instruction","Mother as-rolled plate number → many Plate materials","Mother/Plate material identity → many operation-history rows"]))
 write("design/requirements.md","# PlateFlow v2 Requirements\n\nA fictional steelworks maintains distinct records for slab materials, planned rolling instructions, released rolling instructions, furnace-charge tracking, as-rolled mother materials, cutting/finishing instructions, individual cut Plate materials and operation history. Preserve milestone timestamps on material records and repeated operation occurrences with start/completion times in history. Separate planned, actual and technical times. Model one-to-many mother-to-piece lineage. Extract mother-material lifecycle logs including descendant-piece operations exactly once. Use a synthetic code domain for operation meanings.\n\nThe physical separation follows selected tables in the supplied POSCO metadata. Cardinalities, keys, types, code values and execution rules are newly specified assumptions.\n")
 js("design/source_mapping.json",dict(source="Uploaded data schema MAS CSV",profile="English schema-informed subset, not full POSCO database replica",tables=[dict(synthetic_table=t,source_table=v["source_table"],columns=[dict(synthetic=c["name"],source=c["source_column"]) for c in v["columns"]]) for t,v in T.items()],assumptions=rules))
 path=P/"input/database.sqlite";path.unlink(missing_ok=True);con=sqlite3.connect(path);con.row_factory=sqlite3.Row;con.executescript(ddl)
 con.executemany("INSERT INTO operation_code VALUES (?,?)",CODES.items())
 history=[];ops=[];payload=[];modes=["planned","reheating","rolled","normal","treated","rework"]
 for i in range(1,37):
  mid=f"M{i:03}";sid=f"SL{i:03}";plan=f"PLAN{i:03}";ri=f"RI{i:03}";mother=f"AR{i:03}";mode=modes[(i-1)%6]
  base=datetime(2026,3,1,tzinfo=timezone.utc)+timedelta(hours=i*24)
  stamp=lambda x:(base+timedelta(hours=x)).isoformat().replace("+00:00","Z")
  own=[];pieces=[]
  def event(a,h,eid,recorded):
   e=dict(event_id=eid,case_id=mid,activity=a,timestamp=stamp(h));history.append(e)
   if recorded==mid:own.append(e)
  def op(co,h,recorded,suffix):
   oid=recorded+"-"+suffix
   event(CODES[co],h,"OP:"+oid,recorded);ops.append((oid,recorded,co,stamp(h-.5),stamp(h),stamp(h+.1)))
  event("Rolling Instruction Released",0,"RI:"+ri,mid)
  charged=None;crop=None;tracking=None;cut=None
  if mode!="planned":
   event("Yard Instruction Received",1,"YD:TR"+mid,mid)
   charge_hour=rng.choice([2,3,4]);charged=stamp(charge_hour);event("Reheating Started",charge_hour,"RH:"+mid,mid)
   tracking=("TR"+mid,mid,stamp(1),stamp(1.5))
  if mode not in ("planned","reheating"):op("RL",6,mid,"RL")
  if mode in ("normal","treated","rework"):
   op("CO",7,mid,"CO");op("LE",8,mid,"LE")
   crop=stamp(9);event("Crop Shear Passed",9,"CS:"+mid,mid)
   cut=("CI"+mid,mid,stamp(10),"SPLIT");event("Cutting Instruction Released",10,"CI:CI"+mid,mid)
   op("SC",11,mid,"SC")
   for j in range(1,1+rng.randint(1,3)):
    pid=f"P{i:03}-{j}";latest=13+j/10
    if mode=="treated":op("HT",12,pid,"HT1")
    if mode=="rework" and j==1:
     op("IF",12,pid,"IF1");op("HT",14,pid,"HT1");op("IF",15,pid,"IF2");op("HT",17,pid,"HT2");latest=18
    op("IP",latest,pid,"IP")
    event("Dimensional Inspection Completed",latest+.5,"DIM:"+pid,pid)
    pieces.append((pid,"PL"+pid,mother,stamp(latest+.5),stamp(latest+.5)))
  latest=max([e["timestamp"] for e in own if e["activity"] in CODES.values()],default=None)
  payload.append((sid,plan,ri,mid,mother,mode,stamp,charged,crop,latest,tracking,cut,pieces))
 # Every timestamp stored below originates in canonical events or explicitly marked plan/technical context.
 for sid,plan,ri,mid,mother,mode,stamp,charged,crop,latest,tracking,cut,pieces in payload:
  # Stored stamp closures are not used for identity/event timestamps; recover from instruction event.
  released=next(e["timestamp"] for e in history if e["event_id"]=="RI:"+ri)
  dt=datetime.fromisoformat(released.replace("Z","+00:00"))
  st=lambda h:(dt+timedelta(hours=h)).isoformat().replace("+00:00","Z")
  con.execute("INSERT INTO slab_material VALUES (?,?)",(sid,"CH"+sid[2:]))
  con.execute("INSERT INTO planned_rolling_instruction VALUES (?,?,?)",(plan,sid,st(2)))
  con.execute("INSERT INTO rolling_instruction VALUES (?,?,?)",(ri,plan,released))
  con.execute("INSERT INTO as_rolled_material VALUES (?,?,?,?,?,?,?,?,?)",(mid,mother,sid,ri,charged,crop,latest,st(-1),st(22)))
  if tracking:con.execute("INSERT INTO furnace_charge_tracking VALUES (?,?,?,?)",tracking)
  if cut:con.execute("INSERT INTO cutting_finishing_instruction VALUES (?,?,?,?)",cut)
  con.executemany("INSERT INTO plate_material VALUES (?,?,?,?,?)",pieces)
 con.executemany("INSERT INTO material_operation_history VALUES (?,?,?,?,?,?)",ops);con.commit()
 jl("private/canonical_history.jsonl",history);js("private/persistence_mapping.json",S)
 allacts=[s["activity"] for s in S]
 catalog=dict(case_concept="As-rolled mother material",default_scope=rules[2],activities=allacts,case_population="all as_rolled_material rows",setting="Catalog-assisted; source bindings withheld")
 js("input/task_scope_catalog.json",catalog)
 specs=[
 ("V01","explicit","Extract Reheating Started, Rolling Completed and Crop Shear Passed for each as-rolled mother material.",["Reheating Started","Rolling Completed","Crop Shear Passed"],None),
 ("V02","paraphrase","For each mother material, show actual furnace entry, rolling completion and crop-shear passage.",["Reheating Started","Rolling Completed","Crop Shear Passed"],"V01"),
 ("V03","explicit","Extract Inspection Failed, Heat Treatment Completed and Inspection Passed for each mother material, including all its descendant Plate materials.",["Inspection Failed","Heat Treatment Completed","Inspection Passed"],None),
 ("V04","paraphrase","Trace every failed inspection, thermal treatment and passing inspection of pieces originating from each mother material.",["Inspection Failed","Heat Treatment Completed","Inspection Passed"],"V03"),
 ("V05","full_lifecycle","Extract the complete recorded manufacturing lifecycle for each as-rolled mother material, including its descendant Plate materials.",allacts,None),
 ("V06","paraphrase","Build a mother-material log covering all recorded actual production steps and downstream operations on its cut pieces.",allacts,"V05"),
 ("V07","explicit","Extract Cutting Instruction Released, Split Cutting Completed and Dimensional Inspection Completed for each mother material and its cut pieces.",["Cutting Instruction Released","Split Cutting Completed","Dimensional Inspection Completed"],None),
 ("V08","unsupported","Extract continuous-casting start and completion for each slab.",[],None)]
 questions=[];gold=[];results=[]
 for qid,kind,q,acts,pair in specs:
  questions.append(dict(question_id=qid,text=q,pair_of=pair))
  if kind=="unsupported":gold.append(dict(question_id=qid,answerability="unsupported",reason="No casting event times in this selected schema.",es=None,process_view=None));results.append(dict(question_id=qid,status="unsupported_by_design"));continue
  es=dict(version="plateflow-es-2",case_population_query="SELECT material_id FROM as_rolled_material",sources=[s for s in S if s["activity"] in acts])
  gold.append(dict(question_id=qid,category=kind,answerability="answerable",process_view=dict(case_concept=catalog["case_concept"],activities=acts,scope_rule=catalog["default_scope"]),es=es))
  expected=sorted([e for e in history if e["activity"] in acts],key=lambda e:(e["case_id"],e["timestamp"],e["event_id"]))
  sql=compile_es(es);actual=[dict(r) for r in con.execute(sql)];assert expected==actual,qid
  p=P/("private/gold_logs/"+qid+".csv");p.parent.mkdir(parents=True,exist_ok=True)
  with p.open("w",newline="") as f:
   w=csv.DictWriter(f,fieldnames=["event_id","case_id","activity","timestamp"]);w.writeheader();w.writerows(expected)
  write("private/gold_sql/"+qid+".sql",sql+"\n");results.append(dict(question_id=qid,status="pass",event_count=len(expected)))
 jl("input/questions.jsonl",questions);jl("private/gold.jsonl",gold)
 assert not list(con.execute("PRAGMA foreign_key_check"))
 assert con.execute("PRAGMA integrity_check").fetchone()[0]=="ok"
 assert len({e["event_id"] for e in history})==len(history)
 assert con.execute("SELECT COUNT(*) FROM material_operation_history h WHERE NOT EXISTS(SELECT 1 FROM as_rolled_material m WHERE m.material_id=h.material_id) AND NOT EXISTS(SELECT 1 FROM plate_material p WHERE p.plate_material_id=h.material_id)").fetchone()[0]==0
 assert con.execute("SELECT COUNT(*) FROM as_rolled_material m JOIN plate_material p ON m.material_id=p.plate_material_id").fetchone()[0]==0
 for t,d in T.items():
  rows=list(con.execute("PRAGMA table_info("+t+")"))
  assert [(r["name"],r["type"]) for r in rows]==[(c["name"],c["type"]) for c in d["columns"]]
 assert con.execute("SELECT COUNT(*) FROM material_operation_history WHERE completed_at<=started_at").fetchone()[0]==0
 report=dict(seed=20261013,mother_materials=36,plate_materials=con.execute("SELECT COUNT(*) FROM plate_material").fetchone()[0],events=len(history),tables={t:con.execute("SELECT COUNT(*) FROM "+t).fetchone()[0] for t in T},scenario_counts=dict(Counter(r[5] for r in payload)),questions=results,checks=dict(gold_sql_exact_equality="pass",foreign_keys="pass",sqlite_integrity="pass",metadata_columns_types="pass",event_id_uniqueness="pass",history_start_before_completion="pass"),limitations=["Selected English schema-informed subset, not complete POSCO schema.","Original CSV supplies names/descriptions only; types, keys, code domain and cardinalities are authored.","No real production rows or fitted process distributions.","Classic mother-case log, not OCEL.","Fixture-local ES; existing NL2EventLog compatibility untested.","No extraction-model accuracy measured."])
 js("validation_report.json",report);con.close();print(json.dumps(report,indent=2))
if __name__=="__main__":main()
