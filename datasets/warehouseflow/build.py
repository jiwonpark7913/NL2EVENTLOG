"""RSchema retaining the original source structure warehouse dataset. Standard library only."""
import csv,json,sqlite3,random
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from readability import bullet_prose
from datetime import datetime,timedelta,timezone
from collections import Counter
P=Path(__file__).resolve().parent
def write(n,s):
 p=P/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(bullet_prose(s) if p.suffix=='.md' else s,encoding="utf-8")
def js(n,o):write(n,json.dumps(o,indent=2)+"\n")
def jl(n,o):write(n,"".join(json.dumps(r)+"\n" for r in o))
TABLE_MAP={"Warehouse":"warehouse","Goods":"goods","Loader":"loader","transaction record":"transaction_record","good transaction record details":"goods_transaction_detail","stevedore-transaction record":"loader_transaction"}
NAMES={"warehouse number":"warehouse_number","address":"address","capacity":"capacity","goods id":"goods_id","goods name":"goods_name","name":"name","phone":"phone","loader id":"loader_id","transaction id":"transaction_id","time":"occurred_at","transaction type":"transaction_type","quantity":"quantity"}
DESC={"warehouse_number":"Warehouse identity","address":"Warehouse postal address","capacity":"Maximum total stock units; synthetic unit convention","goods_id":"Goods identity","goods_name":"Goods business name","name":"Worker name","phone":"Worker contact phone","loader_id":"Worker identity","transaction_id":"Inbound/outbound transaction identity","occurred_at":"Actual UTC completion time of recorded task; instant-event convention","transaction_type":"IN = Goods Received; OUT = Goods Dispatched","quantity":"Positive number of units of this goods type moved by the transaction"}
TD={"warehouse":"Warehouse master","goods":"Goods master","loader":"Loading/unloading worker master","transaction_record":"Inbound/outbound task header, one business occurrence per row","goods_transaction_detail":"Goods lines per transaction; composite key prevents repeated goods within one task","loader_transaction":"Worker assignment bridge; multiple workers may share one task"}
def canonical(n):return NAMES[n.casefold()]
def compile_es(es):
 if es.get("compiled_sql"):return es["compiled_sql"]
 parts=[]
 for s in es["sources"]:
  parts.append("SELECT 'TX:' || t.transaction_id event_id, t.warehouse_number case_id, '"+s["activity"]+"' activity, t.occurred_at timestamp FROM transaction_record t WHERE t.transaction_type='"+s["value"]+"'")
 return "SELECT * FROM ("+" UNION ALL ".join(parts)+") ORDER BY case_id,timestamp,event_id;"
def main():
 (P/"private/lifecycle_links.json").unlink(missing_ok=True)
 original=json.loads((P/"source/rschema_original.json").read_text())
 tables=[];changes=[]
 for name,t in original["answer"].items():
  cols=[]
  for a in t["Attributes"]:
   n=canonical(a);ty="INTEGER" if n in ["capacity","quantity"] else "TEXT"
   constraints="NOT NULL"
   if n=="capacity":constraints+=" CHECK(capacity > 0)"
   if n=="quantity":constraints+=" CHECK(quantity > 0)"
   if n=="transaction_type":constraints+=" CHECK(transaction_type IN ('IN','OUT'))"
   cols.append(dict(name=n,type=ty,constraints=constraints,definition=DESC[n],source_attribute=a))
  pk=[canonical(x) for x in t["Primary key"]]
  fk=[]
  for a,target in t["Foreign key"].items():
   for ref,attr in target.items():fk.append(dict(column=canonical(a),parent_table=TABLE_MAP[ref],parent_column=canonical(attr)))
  for x in t["Primary key"]:
   if x not in t["Attributes"]:changes.append(dict(table=name,issue="Key label does not exactly match attribute spelling",label=x,repair="Case-insensitive resolution to declared attribute"))
  for x,targets in t["Foreign key"].items():
   if x not in t["Attributes"]:changes.append(dict(table=name,issue="FK label casing mismatch",label=x,repair="Case-insensitive normalization"))
   for ref,attr in targets.items():
    if attr not in original["answer"][ref]["Attributes"]:changes.append(dict(table=name,issue="Referenced attribute casing mismatch",label=ref+"."+attr,repair="Case-insensitive normalization"))
  tables.append(dict(table=TABLE_MAP[name],source_table=name,definition=TD[TABLE_MAP[name]],columns=cols,primary_key=pk,foreign_keys=fk))
 ddl="PRAGMA foreign_keys=ON;\n"
 for t in tables:
  clauses=[c["name"]+" "+c["type"]+" "+c["constraints"] for c in t["columns"]]+["PRIMARY KEY ("+",".join(t["primary_key"])+")"]
  clauses+=["FOREIGN KEY ("+f["column"]+") REFERENCES "+f["parent_table"]+"("+f["parent_column"]+")" for f in t["foreign_keys"]]
  ddl+="CREATE TABLE "+t["table"]+" ("+", ".join(clauses)+");\n"
 write("input/schema.sql",ddl);js("design/logical_schema.json",tables)
 rules=["One transaction header is one warehouse business event, regardless of goods-line or worker counts.","IN adds quantity; OUT removes quantity. Stock is never negative, and total stock stays within warehouse capacity.","Transactions have at least one goods line and one worker assignment.","Goods details and worker assignments enrich events; joining them must not multiply header events.","A transaction ID does not link an inbound task to a later outbound task as a shipment lifecycle.","The default warehouse view contains all recorded IN/OUT transactions for that warehouse.","Only completion instants are recorded. Task start times and durations cannot be inferred.","Master records and worker assignments are not additional business events."]
 dictionary=dict(name="WarehouseFlow RSchema v1",language="en",timezone="UTC",tables=tables,value_domain={"IN":"Goods Received","OUT":"Goods Dispatched"},business_rules=rules)
 js("input/data_dictionary.json",dictionary)
 md="# WarehouseFlow English Data Dictionary\n"
 for t in tables:
  md+="\n## "+t["table"]+"\n\n"+t["definition"]+"\n\n| Column | Type | Meaning |\n|---|---|---|\n"+"".join("| "+c["name"]+" | "+c["type"]+" | "+c["definition"]+" |\n" for c in t["columns"])
  md+="\nPrimary key: "+", ".join(t["primary_key"])+".\n"
  md+="".join("\nForeign key: "+f["column"]+" → "+f["parent_table"]+"."+f["parent_column"]+".\n" for f in t["foreign_keys"])
 md+="\n## Code domain\n\nIN = Goods Received; OUT = Goods Dispatched.\n\n## Business rules\n\n"+"\n".join("- "+r for r in rules)+"\n";write("input/data_dictionary.md",md)
 js("design/adaptation_report.json",dict(source_record_id=original["id"],original_tables=len(tables),retained_tables=len(tables),original_attribute_count=sum(len(t["Attributes"]) for t in original["answer"].values()),retained_attribute_count=sum(len(t["columns"]) for t in tables),new_tables=0,new_columns=0,renamed_tables=TABLE_MAP,renamed_columns=NAMES,repairs=changes,additions=["SQLite types and CHECK constraints","UTC timestamp and task-completion convention","IN/OUT allowed-value meanings","Stock and capacity simulation rules","Questions, case scope, Gold ES and logs"],not_claimed=["Original source SQL types or allowed-value codes","Source-defined approval, purchase-order or shipment lifecycle","SchemaAgent code execution","ISO compliance"]))
 write("design/requirements.md","# Adapted execution specification\n\nThe original RSchema requirement is preserved in source/requirements_original.md. Retain all six original logical tables, all attributes and all declared PK/FK relationships. Normalize English identifiers to snake_case without changing entity structure. Materialize a warehouse task simulation with IN/OUT task completion timestamps, positive goods quantities, nonnegative stock and capacity limits. Worker assignments and goods details may be many-to-many with task headers. Query-specific logs use warehouses as cases and each task as one event.\n")
 js("design/conceptual_model.json",dict(entities=["Warehouse","Goods","Loader","Transaction"],relations=["Warehouse 1:N Transaction","Transaction M:N Goods through composite-key details","Transaction M:N Loader through composite-key assignments"],status="Derived from original logical schema; not supplied as an original conceptual artifact"))
 db=P/"input/database.sqlite";db.unlink(missing_ok=True);con=sqlite3.connect(db);con.row_factory=sqlite3.Row;con.executescript(ddl)
 con.executemany("INSERT INTO warehouse VALUES (?,?,?)",[(f"W{i}",f"Fictional Warehouse Avenue {i}",1000) for i in range(1,5)])
 con.executemany("INSERT INTO goods VALUES (?,?)",[(f"G{i}","Goods "+str(i)) for i in range(1,7)])
 # Source order is name, phone, loader ID.
 con.executemany("INSERT INTO loader VALUES (?,?,?)",[(f"Worker {i}",f"+1-555-010{i}",f"L{i}") for i in range(1,6)])
 rng=random.Random(20261014);history=[];payload=[];stock=Counter();peak=Counter()
 for i in range(1,81):
  wid=f"W{1+(i-1)%4}";direction="IN" if (i-1)//4%2==0 else "OUT"
  goods=rng.sample([f"G{j}" for j in range(1,7)],rng.randint(1,3))
  lines=[]
  for g in goods:
   if direction=="OUT" and not stock[wid,g]:continue
   qty=rng.randint(1,10) if direction=="IN" else rng.randint(1,min(10,stock[wid,g]))
   stock[wid,g]+=qty if direction=="IN" else -qty;lines.append((g,qty))
  if not lines:
   direction="IN";g=goods[0];qty=rng.randint(1,10);stock[wid,g]+=qty;lines=[(g,qty)]
  assert all(q>=0 for q in stock.values())
  total=sum(v for (w,_),v in stock.items() if w==wid);assert total<=1000;peak[wid]=max(peak[wid],total)
  tx=f"T{i:03}";stamp=(datetime(2026,4,1,tzinfo=timezone.utc)+timedelta(hours=i)).isoformat().replace("+00:00","Z")
  workers=rng.sample([f"L{j}" for j in range(1,6)],rng.randint(1,3))
  history.append(dict(event_id="TX:"+tx,case_id=wid,activity="Goods Received" if direction=="IN" else "Goods Dispatched",timestamp=stamp))
  payload.append((tx,wid,direction,stamp,lines,workers))
 for tx,wid,direction,stamp,lines,workers in payload:
  # Original header attribute ordering is transaction ID, time, warehouse number, type.
  con.execute("INSERT INTO transaction_record VALUES (?,?,?,?)",(tx,stamp,wid,direction))
  con.executemany("INSERT INTO goods_transaction_detail VALUES (?,?,?)",[(g,tx,q) for g,q in lines])
  con.executemany("INSERT INTO loader_transaction VALUES (?,?)",[(l,tx) for l in workers])
 con.commit();jl("private/canonical_history.jsonl",history)
 sources=[dict(activity=a,value=v,table="transaction_record",case_column="warehouse_number",timestamp_column="occurred_at",event_key="transaction_id") for v,a in [("IN","Goods Received"),("OUT","Goods Dispatched")]]
 js("private/persistence_mapping.json",sources)
 js("input/task_scope_catalog.json",dict(case_concept="Warehouse",activities=["Goods Received","Goods Dispatched"],default_scope=rules[5],case_population="all warehouse rows",setting="Catalog-assisted"))
 specs=[("R01","explicit","Extract Goods Received events for each warehouse.",["Goods Received"],None),("R02","paraphrase","For every warehouse, show all recorded inbound goods-handling tasks.",["Goods Received"],"R01"),("R03","explicit","Extract Goods Dispatched events for each warehouse.",["Goods Dispatched"],None),("R04","paraphrase","Build a warehouse-level timeline of recorded outbound goods-handling tasks.",["Goods Dispatched"],"R03"),("R05","full_lifecycle","Extract all recorded inbound and outbound business events for each warehouse.",["Goods Received","Goods Dispatched"],None),("R06","paraphrase","Show the complete recorded goods-movement history of every warehouse.",["Goods Received","Goods Dispatched"],"R05"),("R07","unsupported","Extract task start and completion events for each warehouse.",[],None)]
 questions=[];gold=[];results=[]
 for qid,kind,q,acts,pair in specs:
  questions.append(dict(question_id=qid,text=q,pair_of=pair))
  if kind=="unsupported":
   gold.append(dict(question_id=qid,answerability="unsupported",reason="Only one task time is stored, defined as completion. Task start times are not recorded.",process_view=None,es=None));results.append(dict(question_id=qid,status="unsupported_by_design"));continue
  es=dict(version="warehouseflow-es-1",case_population_query="SELECT warehouse_number FROM warehouse",sources=[s for s in sources if s["activity"] in acts])
  gold.append(dict(question_id=qid,category=kind,answerability="answerable",process_view=dict(case_concept="Warehouse",activities=acts,scope_rule=rules[5]),es=es))
  sql=compile_es(es);actual=[dict(r) for r in con.execute(sql)];expected=sorted([e for e in history if e["activity"] in acts],key=lambda e:(e["case_id"],e["timestamp"],e["event_id"]));assert actual==expected
  p=P/("private/gold_logs/"+qid+".csv");p.parent.mkdir(parents=True,exist_ok=True)
  with p.open("w",newline="") as f:
   w=csv.DictWriter(f,fieldnames=["event_id","case_id","activity","timestamp"]);w.writeheader();w.writerows(expected)
  write("private/gold_sql/"+qid+".sql",sql+"\n");results.append(dict(question_id=qid,status="pass",event_count=len(expected)))
 jl("input/questions.jsonl",questions);jl("private/gold.jsonl",gold)
 assert not list(con.execute("PRAGMA foreign_key_check"));assert con.execute("PRAGMA integrity_check").fetchone()[0]=="ok"
 for t in tables:
  cols=list(con.execute("PRAGMA table_info("+t["table"]+")"))
  assert [r["name"] for r in cols]==[c["name"] for c in t["columns"]]
  assert [r["name"] for r in sorted(cols,key=lambda r:r["pk"]) if r["pk"]]==t["primary_key"]
  assert len(list(con.execute("PRAGMA foreign_key_list("+t["table"]+")")))==len(t["foreign_keys"])
 assert con.execute("SELECT COUNT(*) FROM transaction_record t WHERE NOT EXISTS(SELECT 1 FROM goods_transaction_detail d WHERE d.transaction_id=t.transaction_id) OR NOT EXISTS(SELECT 1 FROM loader_transaction l WHERE l.transaction_id=t.transaction_id)").fetchone()[0]==0
 fanout=con.execute("SELECT COUNT(*) FROM transaction_record t JOIN goods_transaction_detail d USING(transaction_id) JOIN loader_transaction l USING(transaction_id)").fetchone()[0]
 report=dict(seed=20261014,source_record_id=original["id"],original_tables_retained="6/6",original_attributes_retained=str(sum(len(t["Attributes"]) for t in original["answer"].values()))+"/"+str(sum(len(t["columns"]) for t in tables)),original_fk_relationships_retained="5/5",warehouses=4,events=len(history),activity_counts=dict(Counter(e["activity"] for e in history)),table_rows={t["table"]:con.execute("SELECT COUNT(*) FROM "+t["table"]).fetchone()[0] for t in tables},naive_detail_worker_join_rows=fanout,correct_event_rows=80,peak_inventory_units=dict(peak),questions=results,checks=dict(gold_sql_exact_equality="pass",foreign_keys="pass",source_pk_fk_structure="pass",stock_capacity="pass",task_detail_worker_coverage="pass"),limitations=["Original schema records two instant task types; no approval or order lifecycle.","Warehouse cases group independent tasks, not one shipment lifecycle.","Codes, SQL types and timestamp convention are adaptations.","Dataset-specific ES; no model accuracy measured.","No held-out generalization claim."])
 js("validation_report.json",report);con.close();from object_views import extend_dataset;extend_dataset(P);from lifecycle import extend;extend(P);extend_dataset(P);report=json.loads((P/"validation_report.json").read_text());print(json.dumps(report,indent=2))
if __name__=="__main__":main()
