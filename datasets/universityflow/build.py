"""Build the UniversityFlow course-registration dataset using Python's standard library."""
import csv,json,sqlite3,random
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from readability import bullet_prose
from datetime import datetime,timedelta,timezone
from collections import Counter
P=Path(__file__).resolve().parent
TABLE_MAP={'Student':'student','Course':'course','Registration':'registration','Degree Examination Result':'degree_examination_result'}
NAMES={a:a.lower().replace(' ','_') for a in ['Student ID','Name','Date of Birth','Phone Number','Home Address','Registration Eligibility','Course ID','Course Name','Credits','Instructor','Class Time','Class Location','Registration Time','Status','Result ID','Examination Name','Grade','Examination Date']}
DESC={'student_id':'Student identifier','name':'Student name','date_of_birth':'Birth date; not an academic event','phone_number':'Student contact number','home_address':'Student postal address','registration_eligibility':'Current eligibility: ELIGIBLE or INELIGIBLE; does not store when eligibility changed','course_id':'Course identifier; one course offering in this dataset','course_name':'Course title','credits':'Academic credit units','instructor':'Instructor name; the original schema has no separate instructor table','class_time':'Scheduled teaching time; not proof that a class took place','class_location':'Scheduled teaching location','registration_time':'Actual successful course-registration time in UTC','status':'Current registration status; REGISTERED in this dataset; no status-change history is stored','result_id':'Unique examination-result identifier','examination_name':'Degree examination name','grade':'Examination score from 0 to 100; 60 is the synthetic eligibility threshold','examination_date':'Actual examination time in UTC; not the time its result was published'}
ROLE={'student':'Basic student information and current registration eligibility','course':'Course offerings and teaching schedules','registration':'Successful student-course registrations; one row per student and course','degree_examination_result':'Degree examination results; repeated examinations use separate result IDs'}
RULES=['Use each student as a case (one timeline).','An examination-result row records one Degree Examination Taken event at examination_date. The timestamp does not establish when the result was published.','A registration row records one Course Registered event at registration_time.','The default student timeline contains recorded examination events and successful registrations.','Students may retake the examination. In this simulation a score of at least 60 permits subsequent registration. The source does not specify this threshold.','The student-course composite key allows only one retained registration per pair. Repeated registrations and withdrawals are not added.','Eligibility and status are current values. Their transitions cannot be reconstructed.','Birth dates and scheduled class times are not academic process events.','The requirement mentions notification and information checks, but their execution times are not stored.','Students with no selected events remain in the separately declared case population.']
def write(n,s):
 p=P/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(bullet_prose(s) if p.suffix=='.md' else s,encoding='utf-8')
def js(n,o):write(n,json.dumps(o,indent=2)+'\n')
def jl(n,rows):write(n,''.join(json.dumps(r)+'\n' for r in rows))
def compile_es(es):
 parts=[]
 for s in es['sources']:
  key="'EX:' || result_id" if s['table']=='degree_examination_result' else "'REG:' || student_id || ':' || course_id"
  parts.append(f"SELECT {key} event_id, student_id case_id, '{s['activity']}' activity, {s['timestamp_column']} timestamp FROM {s['table']}")
 return 'SELECT * FROM ('+' UNION ALL '.join(parts)+') ORDER BY case_id,timestamp,event_id;'
def main():
 original=json.loads((P/'source/rschema_original.json').read_text());tables=[]
 for name,t in original['answer'].items():
  cols=[]
  for a in t['Attributes']:
   n=NAMES[a];ty='INTEGER' if n in ['credits','grade'] else 'TEXT';constraint='NOT NULL'
   if n=='grade':constraint+=' CHECK(grade BETWEEN 0 AND 100)'
   if n=='credits':constraint+=' CHECK(credits > 0)'
   if n=='registration_eligibility':constraint+=" CHECK(registration_eligibility IN ('ELIGIBLE','INELIGIBLE'))"
   if n=='status':constraint+=" CHECK(status='REGISTERED')"
   cols.append(dict(name=n,type=ty,constraints=constraint,definition=DESC[n],source_attribute=a))
  fk=[dict(column=NAMES[a],parent_table=TABLE_MAP[ref],parent_column=NAMES[attr]) for a,target in t['Foreign key'].items() for ref,attr in target.items()]
  tables.append(dict(table=TABLE_MAP[name],source_table=name,definition=ROLE[TABLE_MAP[name]],columns=cols,primary_key=[NAMES[a] for a in t['Primary key']],foreign_keys=fk))
 ddl='PRAGMA foreign_keys=ON;\n'
 for t in tables:
  clauses=[c['name']+' '+c['type']+' '+c['constraints'] for c in t['columns']]+['PRIMARY KEY ('+','.join(t['primary_key'])+')']
  clauses+=['FOREIGN KEY ('+f['column']+') REFERENCES '+f['parent_table']+'('+f['parent_column']+')' for f in t['foreign_keys']]
  ddl+='CREATE TABLE '+t['table']+' ('+', '.join(clauses)+');\n'
 write('input/schema.sql',ddl);js('design/logical_schema.json',tables)
 d=dict(name='UniversityFlow',language='en',timezone='UTC',tables=tables,value_domain={'ELIGIBLE':'Student may register after passing the simulated examination','INELIGIBLE':'Student has no passing examination in the simulated history','REGISTERED':'A successful course registration'},business_rules=RULES);js('input/data_dictionary.json',d)
 md='# UniversityFlow English Data Dictionary\n'
 for t in tables:
  md+='\n## '+t['table']+'\n\n- '+t['definition']+'\n- Primary key: '+', '.join(t['primary_key'])+'\n'+''.join('- Foreign key: '+f['column']+' → '+f['parent_table']+'.'+f['parent_column']+'\n' for f in t['foreign_keys'])+'\n| Column | Type | Meaning |\n|---|---|---|\n'+''.join('| '+c['name']+' | '+c['type']+' | '+c['definition']+' |\n' for c in t['columns'])
 md+='\n## Business rules\n\n'+'\n'.join('- '+r for r in RULES)+'\n';write('input/data_dictionary.md',md)
 js('design/adaptation_report.json',dict(source_record_id=original['id'],original_tables=4,retained_tables=4,original_attribute_count=21,retained_attribute_count=21,original_fk_relationships=3,retained_fk_relationships=3,new_tables=0,new_columns=0,renamed_tables=TABLE_MAP,renamed_columns=NAMES,repairs=[],additions=['SQLite data types and constraints','UTC instant-event interpretation','Synthetic passing threshold of 60','Eligibility/status values and simulation rules','Questions and expected extraction results'],source_gaps=['No notification or information-verification timestamps','No eligibility-change or registration-status history','No result-publication timestamp','Composite registration key cannot retain multiple registrations for the same student and course']))
 js('design/conceptual_model.json',dict(entities=['Student','Course','Registration','Degree Examination Result'],relations=['Student 1:N Degree Examination Result','Student M:N Course through Registration'],status='Derived locally from the original RSchema logical schema'))
 write('design/requirements.md','# UniversityFlow execution requirements\n\n- Preserve all four tables, 21 attributes and three foreign-key relationships from the original RSchema registration example.\n- Simulate degree examinations, retakes and successful course registrations.\n- Keep the source student-course composite key; do not invent a withdrawal or repeat-registration history.\n- Define student timelines using examination and registration timestamps.\n- Document unsupported operations mentioned in the original requirement but absent from the schema.\n')
 db=P/'input/database.sqlite';db.unlink(missing_ok=True);con=sqlite3.connect(db);con.row_factory=sqlite3.Row;con.executescript(ddl)
 rng=random.Random(20261015);history=[];exams=[];registrations=[];base=datetime(2026,2,1,tzinfo=timezone.utc)
 stamp=lambda t:t.isoformat().replace('+00:00','Z')
 scenarios=Counter()
 for i in range(1,41):
  sid=f'S{i:03}';scenario=['no_exam','failed','retake_pass','passed'][i%4];scenarios[scenario]+=1;passed=scenario in ['retake_pass','passed']
  con.execute('INSERT INTO student VALUES (?,?,?,?,?,?)',(sid,f'Student {i:02}','2004-01-01',f'+1-555-{i:04}',f'Fictional Campus Residence {i}','ELIGIBLE' if passed else 'INELIGIBLE'))
  if scenario!='no_exam':
   grades=[rng.randint(20,59),rng.randint(60,100)] if scenario=='retake_pass' else [rng.randint(60,100) if passed else rng.randint(20,59)]
   for j,grade in enumerate(grades):
    rid=f'E{i:03}-{j+1}';time=stamp(base+timedelta(days=i,hours=9+j*48));exams.append((rid,sid,'Registration Eligibility Examination',grade,time));history.append(dict(event_id='EX:'+rid,case_id=sid,activity='Degree Examination Taken',timestamp=time))
  if passed:
   for cid in rng.sample([f'C{k:02}' for k in range(1,7)],rng.randint(1,3)):
    time=stamp(base+timedelta(days=i+4,hours=10+int(cid[1:])));registrations.append((sid,cid,time,'REGISTERED'));history.append(dict(event_id='REG:'+sid+':'+cid,case_id=sid,activity='Course Registered',timestamp=time))
 for k,name in enumerate(['Database Systems','Statistics','Operations Research','Programming','Economics','Process Mining'],1):con.execute('INSERT INTO course VALUES (?,?,?,?,?,?)',(f'C{k:02}',name,3,f'Instructor {k}','Monday 09:00',f'Room {k:03}'))
 con.executemany('INSERT INTO degree_examination_result VALUES (?,?,?,?,?)',exams);con.executemany('INSERT INTO registration VALUES (?,?,?,?)',registrations);con.commit();jl('private/canonical_history.jsonl',history)
 sources=[dict(activity='Degree Examination Taken',table='degree_examination_result',timestamp_column='examination_date',case_column='student_id',event_key=['result_id']),dict(activity='Course Registered',table='registration',timestamp_column='registration_time',case_column='student_id',event_key=['student_id','course_id'])];js('private/persistence_mapping.json',sources)
 js('input/task_scope_catalog.json',dict(case_concept='Student',activities=[s['activity'] for s in sources],default_scope=RULES[3],case_population='all student rows',setting='Catalog-assisted'))
 specs=[('U01','explicit','Extract Degree Examination Taken events for each student.',['Degree Examination Taken'],None),('U02','paraphrase','Show when each student sat their degree examinations, including retakes.',['Degree Examination Taken'],'U01'),('U03','explicit','Extract Course Registered events for each student.',['Course Registered'],None),('U04','paraphrase','Build a student-level timeline of successful course sign-ups.',['Course Registered'],'U03'),('U05','full_lifecycle','Extract all recorded examination and course-registration events for each student.',[s['activity'] for s in sources],None),('U06','paraphrase','Show every recorded step from sitting examinations to signing up for classes for each student.',[s['activity'] for s in sources],'U05'),('U07','unsupported','Extract registration-success notification events for each student.',[],None),('U08','unsupported','Extract course-withdrawal events for each student.',[],None)]
 questions=[];gold=[];results=[]
 for qid,kind,q,acts,pair in specs:
  questions.append(dict(question_id=qid,text=q,pair_of=pair))
  if kind=='unsupported':
   reason='The requirement mentions notifications, but the schema stores no notification records or times.' if qid=='U07' else 'No withdrawal time or registration-status history is recorded.'
   gold.append(dict(question_id=qid,category=kind,answerability='unsupported',reason=reason,process_view=None,es=None));results.append(dict(question_id=qid,status='unsupported_by_design'));continue
  es=dict(version='universityflow-es-1',case_population_query='SELECT student_id FROM student',sources=[s for s in sources if s['activity'] in acts]);sql=compile_es(es)
  expected=sorted([e for e in history if e['activity'] in acts],key=lambda e:(e['case_id'],e['timestamp'],e['event_id']));actual=[dict(r) for r in con.execute(sql)];assert actual==expected
  gold.append(dict(question_id=qid,category=kind,answerability='answerable',process_view=dict(case_concept='Student',activities=acts,scope_rule=RULES[3]),es=es))
  p=P/('private/gold_logs/'+qid+'.csv');p.parent.mkdir(parents=True,exist_ok=True)
  with p.open('w',newline='') as f:
   w=csv.DictWriter(f,fieldnames=['event_id','case_id','activity','timestamp']);w.writeheader();w.writerows(expected)
  write('private/gold_sql/'+qid+'.sql',sql+'\n');results.append(dict(question_id=qid,status='pass',event_count=len(expected)))
 jl('input/questions.jsonl',questions);jl('private/gold.jsonl',gold)
 assert not list(con.execute('PRAGMA foreign_key_check'));assert con.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
 for t in tables:
  cols=list(con.execute('PRAGMA table_info('+t['table']+')'));assert [r['name'] for r in cols]==[c['name'] for c in t['columns']]
  assert [r['name'] for r in sorted(cols,key=lambda r:r['pk']) if r['pk']]==t['primary_key']
  observed={(r['from'],r['table'],r['to']) for r in con.execute('PRAGMA foreign_key_list('+t['table']+')')};assert observed=={(f['column'],f['parent_table'],f['parent_column']) for f in t['foreign_keys']}
 assert con.execute("SELECT COUNT(*) FROM registration r JOIN student s USING(student_id) WHERE s.registration_eligibility!='ELIGIBLE' OR NOT EXISTS(SELECT 1 FROM degree_examination_result e WHERE e.student_id=r.student_id AND e.grade>=60 AND e.examination_date<r.registration_time)").fetchone()[0]==0
 assert len({e['event_id'] for e in history})==len(history)
 fanout=con.execute('SELECT COUNT(*) FROM student s JOIN registration r USING(student_id) JOIN degree_examination_result e USING(student_id)').fetchone()[0]
 report=dict(seed=20261015,source_record_id=original['id'],original_tables_retained='4/4',original_attributes_retained='21/21',original_fk_relationships_retained='3/3',students=40,events=len(history),activity_counts=dict(Counter(e['activity'] for e in history)),table_rows={t['table']:con.execute('SELECT COUNT(*) FROM '+t['table']).fetchone()[0] for t in tables},scenario_counts=dict(scenarios),students_without_events=10,naive_exam_registration_join_rows=fanout,questions=results,checks=dict(gold_sql_exact_equality='pass',foreign_keys='pass',sqlite_integrity='pass',source_pk_fk_structure='pass',registration_eligibility_and_time='pass',event_id_uniqueness='pass'),limitations=['UTC timestamp meanings and eligibility rules are authored assumptions.','No notification, withdrawal or result-publication event times.','Student timelines do not infer causality between arbitrary exams and registrations.','Dataset-specific extraction specification; existing NL2EventLog compatibility untested.','No model accuracy or generalization result.'])
 js('validation_report.json',report);con.close();print(json.dumps(report,indent=2))
if __name__=='__main__':main()
