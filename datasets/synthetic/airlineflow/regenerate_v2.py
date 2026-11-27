"""Build and validate the stochastic fixture in an isolated checkout. No model calls."""
from pathlib import Path
from collections import Counter, defaultdict
from itertools import product
import csv, json, sqlite3, hashlib, subprocess, tempfile, shutil, sys, re, html
R=Path(__file__).resolve().parent
E=R/'evaluation'
VERSION='Stochastic-v2-20261127'
def load(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,x): p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def csvread(p):
    with p.open(encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))
def csvwrite(p,rows,fields=None):
    fields=fields or list(rows[0])
    with p.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
def events(p,rows):
    with p.open('w',encoding='utf-8',newline='') as f:
        w=csv.writer(f);w.writerow(['case_id','activity','timestamp']);w.writerows(rows)
def qid(n): return f'Q{n:02d}'
def run_sql(c,p): return sorted(c.execute(p.read_text()).fetchall(),key=lambda r:(r[0],r[2],r[1]))
with tempfile.TemporaryDirectory() as td:
    subprocess.run(['node',str(R/'source/generate_records_v2.mjs'),str(Path(td)/'out')],check=True)
    records=load(Path(td)/'out/records.json')
    summary=load(Path(td)/'out/generator_summary.json')
save(R/'source/records.json',records)
save(R/'source/stochastic_v2_generator_preview.json',summary)
T={k:[dict(zip(v['columns'],r)) for r in v['rows']] for k,v in records.items()}
def index(t,k): return {x[k]:x for x in T[t]}
turn=index('turnarounds','turn_id'); inbound=index('turnarounds','inbound_id'); outbound=index('turnarounds','outbound_id')
legs=index('passenger_legs','leg_id'); tickets=index('tickets','ticket_id'); visits=index('security_visits','visit_id'); bags=index('bag_legs','bag_leg_id')
sessions=index('boarding_sessions','flight_id'); dispatch=index('flight_dispatch','flight_id')
mov={(r['flight_id'],r['kind']):r['value_at'] for r in T['movement_reports']}
job={(r['turn_id'],r['job_code']):r for r in T['handling_jobs']}
actions=defaultdict(list); sec=defaultdict(list); scans=defaultdict(list)
for r in T['passenger_actions']: actions[r['leg_id']].append(r)
for r in T['security_events']: sec[r['visit_id']].append(r)
for r in T['bag_scans']: scans[r['bag_leg_id']].append(r)
for u in turn.values():
    a,b=u['inbound_id'],u['outbound_id']; assert dispatch[a]['tail_id']==dispatch[b]['tail_id'] and dispatch[a]['destination']==dispatch[b]['origin']=='ICN'
    assert mov[a,'LAND']<=mov[a,'IN']<=u['handling_started_at']<=u['ready_at']<=mov[b,'OUT']<=mov[b,'AIR']
    assert sessions[b]['closed_at']<=u['ready_at']
    for code in ('DP','UL','CL','FU','CA','BL'):
        j=job[u['turn_id'],code];assert u['handling_started_at']<=j['started_at']<=j['finished_at']<=u['ready_at'] and j['finished_at']<=j['posted_at']
    assert job[u['turn_id'],'DP']['finished_at']<=job[u['turn_id'],'CL']['started_at']
    assert job[u['turn_id'],'UL']['finished_at']<=job[u['turn_id'],'BL']['started_at']
    assert max(job[u['turn_id'],code]['finished_at'] for code in ('CL','FU','CA'))<=sessions[b]['started_at']
for v in visits.values():
    d={r['point']:r['observed_at'] for r in sec[v['visit_id']]}; assert 'Q' in d
    assert 'S' not in d or d['Q']<=d['S']
    assert 'C' not in d or 'S' in d and d['S']<=d['C']
    assert all(r['observed_at']<=r['received_at'] for r in sec[v['visit_id']])
    ck=[r['action_at'] for r in actions[v['leg_id']] if r['action_code']=='CK'];assert len(ck)==1 and ck[0]<=d['Q']
visit_by_leg=defaultdict(list)
for v in visits.values():visit_by_leg[v['leg_id']].append(v)
for l in legs.values():
    s=sessions[l['flight_id']];aa=actions[l['leg_id']]
    ck=[r['action_at'] for r in aa if r['action_code']=='CK'];bd=[r['action_at'] for r in aa if r['action_code']=='BD'];rj=[r['action_at'] for r in aa if r['action_code']=='RJ']
    assert len(ck)<=1 and len(bd)<=1
    assert all(s['started_at']<=v<=s['closed_at'] for v in bd+rj)
    assert not bd or ck and max(rj or ck)<=bd[0]
    completed=[r['observed_at'] for v in visit_by_leg[l['leg_id']] for r in sec[v['visit_id']] if r['point']=='C']
    assert not (bd or rj) or completed and max(completed)<=min(bd+rj)
for b in bags.values():
    d={r['scan_code']:r['scanned_at'] for r in scans[b['bag_leg_id']]}; assert 'B101' in d
    l=legs[b['leg_id']];ck=[r['action_at'] for r in actions[l['leg_id']] if r['action_code']=='CK'];assert len(ck)==1 and ck[0]<=d['B101']
    if 'B204' in d:
        assert d['B101']<=d['B204']
        if l['flight_id'] in outbound:
            j=job[outbound[l['flight_id']]['turn_id'],'BL'];assert j['started_at']<=d['B204']<=j['finished_at']
manifest=load(E/'variant_manifest.json')
previous={}
for v in manifest:
    p=R/v['database_path']; p.unlink(missing_ok=True)
    with sqlite3.connect(p) as c:
        c.execute('PRAGMA foreign_keys=ON');c.executescript(p.with_name('schema.sql').read_text())
        actual={}
        for (t,) in c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY rowid").fetchall():
            r=records[t]
            c.executemany('INSERT INTO '+t+' ('+','.join(r['columns'])+') VALUES ('+','.join('?' for _ in r['columns'])+')',r['rows'])
            actual[t]=c.execute(f'SELECT * FROM "{t}" ORDER BY 1').fetchall()
        assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok' and not c.execute('PRAGMA foreign_key_check').fetchall()
        assert all(actual[t]==rows for t,rows in previous.items())
        previous=actual
    v['table_rows']={t:len(r) for t,r in actual.items()};v['row_count']=sum(v['table_rows'].values());v['database_sha256']=sha(p);v['dictionary_sha256']=sha(R/v['dictionary_path']);v['query_registry_version']=VERSION
save(E/'variant_manifest.json',manifest)
shutil.copy2(R/'variants/l15/input/database.sqlite',R/'input/database.sqlite')
# Independent intent transcription: labels below are not read from Gold SQL, PI or registry.
B=['Boarding Start','Boarding Close']; M=['Off-block','Take-off']; arrival=['Landing','In-block']
J={code:[name+' Start',name+(' Close' if code=='BL' else ' Complete')] for code,name in [('DP','Disembarkation'),('UL','Baggage Unloading'),('CL','Cabin Cleaning'),('FU','Refuelling'),('CA','Catering Loading'),('BL','Baggage Loading')]}
def phases(*codes):return [a for c in codes for a in J[c]]
def ends(*codes):return [J[c][1] for c in codes]
alljobs=phases('DP','UL','CL','FU','CA','BL')
H='Handling Start'; RY='Aircraft Ready'; CK='Check-in Complete'; BD='Passenger Boarding Confirmed'; RJ='Scan Rejected'; S=['Queue Entry','Screening Start','Screening Complete']; BA=['Bag Accepted','Bag Loaded']
I={}
def spec(n,et,acts):I[qid(n)]=(et,list(acts))
spec(1,'Boarding Session',B);spec(2,'Turnaround',[H]+alljobs+[RY]);spec(3,'Flight',B+ends('BL')+[RY,M[0]]);spec(4,'Turnaround',arrival+[H]+alljobs+B+[RY]+M);spec(5,'Turnaround',[H]+phases('CL','FU')+[RY]);spec(6,'Flight',B+M);spec(7,'Flight',ends('UL','CL','FU','CA','BL'));spec(8,'Turnaround',arrival+M);spec(9,'Flight',M);spec(10,'Flight',B+[M[0]]);spec(11,'Boarding Session',B);spec(12,'Flight',B+M)
for start,ets,act in [(13,['Bag Leg','Passenger Leg','Flight'],BA),(16,['Security Visit','Passenger Leg','Flight'],S),(19,['Passenger Leg','Ticket','Booking'],[CK,BD]),(22,['Passenger Leg','Ticket','Booking'],[BD,RJ])]:
    for i,et in enumerate(ets):spec(start+i,et,act)
for n,aa in enumerate([ends('CL','FU','CA','BL')+B,ends('CL','FU')+B+M,ends('CL','FU')+[B[1],RY]+M,ends('DP','UL','CL','FU')+B,arrival+ends('DP','UL')+B,arrival+[H]+ends('DP','UL')+[B[0]]],25):spec(n,'Turnaround',aa)
for n,aa in enumerate([S[1:]+B,[CK,S[2]]+B,[CK,S[2],B[1],RY],[S[0],S[2]]+B,[S[2],BD]+B,[S[2],BD,B[1],RY]],31):spec(n,'Flight',aa)
for n,aa in enumerate([phases('CL'),phases('CL','FU'),phases('CL','FU','CA','BL'),alljobs,ends('BL')+[M[0]],phases('BL')+M,phases('CL','FU','BL')+M,phases('DP','CL','FU','CA','BL')+M],37):spec(n,'Turnaround',aa)
for n,aa in enumerate([ends('CL')+[BD],[CK]+phases('CL')+[BD],[CK]+phases('CL','FU','CA')+[BD],[CK]+phases('UL','CL','FU','CA','BL')+[BD]],45):spec(n,'Flight',aa)
for n in range(49,53):spec(n,'Bag Leg',BA)
for n in range(53,57):spec(n,'Security Visit',S)
for n in range(57,61):spec(n,'Passenger Leg',[CK]+S+[RJ,BD])
roles={}
for n,aa,rr in [(61,[M[1],arrival[0]],['in','in']),(62,[M[1],arrival[0]],['out','out']),(63,[arrival[0],M[1]],['in','out']),(64,[M[0],arrival[1]],['in','in']),(65,[M[0],arrival[1]],['out','out']),(66,[arrival[1],M[0]],['in','out']),(67,[B[1],arrival[0]],['in','in']),(68,[B[1],arrival[0]],['out','out']),(69,[arrival[0],B[1]],['in','out']),(70,[B[0],arrival[1]],['in','in']),(71,[B[0],arrival[1]],['out','out']),(72,[arrival[1],B[0]],['in','out'])]:
    spec(n,'Turnaround',aa);roles[qid(n)]=dict(zip(aa,rr))
# Canonical occurrence inventory with independent source-row evidence.
occ=defaultdict(list)
def emit(a,t,r,col,**kw):occ[a].append((r[col],t,r[records[t]['columns'][0]],col,kw))
for r in T['boarding_sessions']:
    for a,col in zip(B,['started_at','closed_at']):emit(a,'boarding_sessions',r,col,flight=r['flight_id'],session=r['session_id'])
for r in T['handling_jobs']:
    for a,col in zip(J[r['job_code']],['started_at','finished_at']):emit(a,'handling_jobs',r,col,turn=r['turn_id'])
for r in T['turnarounds']:
    for a,col in [(H,'handling_started_at'),(RY,'ready_at')]:emit(a,'turnarounds',r,col,turn=r['turn_id'])
for r in T['movement_reports']:
    a=dict(zip(['LAND','IN','OUT','AIR'],arrival+M)).get(r['kind'])
    if a:emit(a,'movement_reports',r,'value_at',flight=r['flight_id'])
for r in T['passenger_actions']:emit({'CK':CK,'BD':BD,'RJ':RJ}[r['action_code']],'passenger_actions',r,'action_at',leg=r['leg_id'])
for r in T['security_events']:emit(dict(zip(['Q','S','C'],S))[r['point']],'security_events',r,'observed_at',leg=visits[r['visit_id']]['leg_id'],visit=r['visit_id'])
for r in T['bag_scans']:emit(dict(zip(['B101','B204'],BA))[r['scan_code']],'bag_scans',r,'scanned_at',leg=bags[r['bag_leg_id']]['leg_id'],bag=r['bag_leg_id'])
def independent(q):
    et,aa=I[q]; n=int(q[1:]); result=[]
    for a in aa:
        for ts,t,pk,col,k in occ[a]:
            f=k.get('flight') or (legs[k['leg']]['flight_id'] if 'leg' in k else turn[k['turn']]['outbound_id'] if 'turn' in k else None)
            case=None
            if et=='Flight':case=f if n in (15,18) or f in outbound else None
            elif et=='Turnaround':
                role=roles.get(q,{}).get(a,'in' if a in arrival else 'out')
                case=k.get('turn') or (inbound if role=='in' else outbound).get(f,{}).get('turn_id')
            elif et=='Boarding Session':case=k.get('session')
            elif et=='Bag Leg':case=k.get('bag')
            elif et=='Security Visit':case=k.get('visit')
            elif et=='Passenger Leg':case=k.get('leg')
            elif et=='Ticket':case=legs[k['leg']]['ticket_id']
            elif et=='Booking':case=tickets[legs[k['leg']]['ticket_id']]['booking_id']
            if case:result.append((case,a,ts,t,pk,col))
    return sorted(result,key=lambda x:(x[0],x[2],x[1],x[3],x[4]))
registry=csvread(E/'query_registry.csv');assert len(registry)==72
edits={
'Q02':('For each aircraft turnaround, reconstruct the actual ground-service jobs. Include overall ground-handling coordination start and aircraft readiness as events, and the actual start and completion of each type of ground-service job. Exclude passenger boarding. I want to examine how the jobs progress and overlap.','각 항공기 턴어라운드에서 전체 지상조업 조정 시작과 항공기 준비 완료를 이벤트로 포함하고, 각 개별 지상조업 유형의 실제 시작과 완료를 추출해줘. 승객 탑승은 제외하고 조업의 진행과 중첩을 분석하고 싶어.'),
'Q04':('Where is time lost during aircraft turnarounds? For each turnaround, reconstruct the actual process from inbound landing to outbound take-off, including arrival movements, the overall start of ground handling, the actual start and completion of every ground service, the departing flight’s boarding start and close, aircraft readiness, and departure movements.','각 턴어라운드에서 도착편 착륙부터 다음 출발편 이륙까지 도착 이동, 전체 조업 시작, 모든 개별 조업의 실제 시작·완료, 다음 출발편의 탑승 시작·종료, 항공기 준비 완료 및 출발 이동을 추출해 잠재적 병목 구간을 살펴보고 싶어.'),
'Q12':(None,'턴어라운드 이후 출발편의 탑승 시작부터 실제 이륙까지 어떤 흐름으로 진행되는지 알고 싶어. 항공편 수준의 탑승 단계와 실제 출발 이동 이벤트만 포함해줘.'),
'Q25':(None,None),
'Q58':('For each flight segment on a passenger’s ticket, reconstruct the passenger’s own recorded departure processing from check-in through waiting and screening at security to boarding or the last recorded step if boarding was not completed. Include unsuccessful attempts; exclude individual baggage tracking. Return an event log.','승객 항공권의 운항 구간별로 체크인부터 보안검색 대기와 검색을 거쳐 탑승 또는 미완료 시 마지막 기록까지 승객 자체의 출발 처리 과정을 재구성해줘. 실패 시도를 포함하고 개별 수하물 추적 기록은 제외해줘.'),
'Q60':('How do travellers progress through their own recorded departure processing from check-in through airport security, including waiting, to boarding or their last recorded step if boarding is not completed? Create an event log including unsuccessful attempts, excluding individual baggage tracking.','여행객이 체크인부터 보안검색 대기 및 검색을 거쳐 탑승하거나 미완료 시 마지막 기록에 이르기까지 자신의 출발 처리 과정이 어떻게 진행되는지 알고 싶어. 실패 시도를 포함하고 개별 수하물 추적 기록은 제외한 이벤트 로그를 만들어줘.')}
for r in registry:
    q=r['QUERY ID'];en,kr=r['QUERY (EN / KR)'].split('\n',1)
    if q in edits:
        a,b=edits[q];en=a or en;kr=b or kr
    if q=='Q25':en=en.replace('preparation and departure milestones','ground-service completion and gate-boarding milestones');kr=kr.replace('출발 준비와 실제 출발의 주요 시점','지상조업 완료와 게이트 탑승의 주요 시점')
    # Observed partial cases are within scope; no synthetic missing event.
    if q in {'Q13','Q49','Q50','Q51','Q52','Q16','Q53','Q54','Q55','Q56','Q19','Q57','Q59'}:
        en+=' Preserve recorded partial traces; do not invent missing events.'
        kr+=' 기록된 미완료 흐름은 유지하고 없는 이벤트를 생성하지 마.'
    r['QUERY (EN / KR)']=en+'\n'+kr
# Bucket DFG with exact equal-time multiset labels; no artificial within-tie order.
def metrics(rows):
    traces=defaultdict(lambda:defaultdict(list))
    for c,a,t in rows:traces[c][t].append(a)
    variants=Counter();nodes=Counter();edges=Counter();ties=0
    for d in traces.values():
        v=tuple(' ∥ '.join(sorted(d[t])) for t in sorted(d))
        ties+=any(len(x)>1 for x in d.values());variants[v]+=1;nodes.update(v);edges.update(zip(('Start',)+v,v+('End',)))
    return traces,variants,nodes,edges,ties
def render_dfg(q,rows,g):
    traces,variants,nodes,edges,ties=metrics(rows)
    keys={'Start':'start','End':'end'};keys.update({a:'n'+str(i) for i,a in enumerate(sorted(nodes))})
    lines=['digraph G {','rankdir=LR; graph [bgcolor="white",pad=0.2,nodesep=0.3,ranksep=0.5]; node [shape=box,style="rounded,filled",fillcolor="#eaf2f6",color="#607b8b",fontname="Arial",fontsize=10]; edge [color="#728899",fontname="Arial",fontsize=9];','start [label="Start",shape=oval,fillcolor="#e1f2e7"]; end [label="End",shape=oval,fillcolor="#f7e4e4"];']
    for a,n in sorted(nodes.items()):lines.append(f'{keys[a]} [label={json.dumps(a+"\\n"+str(n),ensure_ascii=False)}];')
    for (a,b),n in sorted(edges.items()):lines.append(f'{keys[a]} -> {keys[b]} [label="{n}"];')
    lines.append('}')
    (g/'dfg.dot').write_text('\n'.join(lines)+'\n')
    subprocess.run(['dot','-Tsvg',str(g/'dfg.dot'),'-o',str(g/'dfg.svg')],check=True)
    return traces,variants,nodes,edges,ties
# Existing reference SQL is retained and compared against independent reconstruction.
all_gold={};evidence={};metadata={};digest_groups=defaultdict(list)
with sqlite3.connect(R/'input/database.sqlite') as c:
    for r in registry:
        q=r['QUERY ID'];g=R/'gold'/q;ref=independent(q);rows=run_sql(c,g/'gold.sql');assert rows==[x[:3] for x in ref],q
        all_gold[q]=rows;evidence[q]=ref
        events(g/'events.csv',rows);tr,va,no,ed,ti=render_dfg(q,rows,g)
        et,aa=I[q];assert et==r['CASE ENTITY'] and set(aa)==set(r['EXPECTED ACTIVITIES'].split('; ')),q
        pi=load(g/'pi.json');es=load(g/'espec.json')
        assert set(pi['activities'])==set(aa) and {x['activity'] for x in es['rules']}==set(aa),q
        # Independent source-rule provenance must agree on physical source and occurrence clock.
        expected_rules={a:{(x[3],x[5]) for x in ref if x[1]==a} for a in aa}
        for rule in es['rules']:
            assert expected_rules[rule['activity']]=={(rule['source_table'],rule['timestamp_column'])},(q,rule['activity'])
        for p,obj in [(g/'pi.json',pi),(g/'espec.json',es)]:
            obj['expected_case_count']=len(tr);obj['expected_event_count']=len(rows);obj['fixture_version']=VERSION
            obj['case_scope']= 'Observed requested events, retaining occurrence multiplicity and partial traces within the natural-language scope.'
            save(p,obj)
        counts=Counter(x[1] for x in rows)
        r.update({'EXPECTED CASE COUNT':str(len(tr)),'EXPECTED EVENT COUNT':str(len(rows)),'MEAN TRACE LENGTH':str(round(len(rows)/len(tr),6)),'SOURCE OCCURRENCE PROFILE':'; '.join(f'{a}={counts[a]}' for a in aa),'DUPLICATE EVENT ROWS':str(len(rows)-len(set(rows))),'TIMESTAMP TIE CASES':str(ti),'BUCKET VARIANTS':str(len(va)),'GOLD STATUS':'SQLite and independent occurrence reconstruction PASS','SEMANTIC REVIEW':'v2 automated intent, occurrence and source-rule checks; human review pending','REVIEW VERDICT':'Pending final human approval','REVIEW ACTION':'Regenerated for stochastic fixture; review before model inference'})
        if q in ('Q55','Q56'):r['ALTERNATIVE CASE POLICY']='Passenger Leg not equivalent: multiple visits per leg; scope bijection required.'
        if q in ('Q51','Q52'):r['ALTERNATIVE CASE POLICY']='Bag tag secondary only after verified bijection; Passenger Leg not equivalent.'
        if r['EXPERIMENT']=='B':r['CONTROL / CAVEAT']+='; stochastic event counts and activity mix may differ; not isolated causal effect.'
        d=hashlib.sha256(json.dumps(sorted(rows),ensure_ascii=False,separators=(',',':')).encode()).hexdigest();digest_groups[d].append(q)
        metadata[q]={'case':et,'activity_count':len(aa),'cases':len(tr),'events':len(rows),'variants':len(va),'ties':ti,'digest':d,'dfg':(g/'dfg.svg').read_text(),'pi':pi,'espec':es,'sql':(g/'gold.sql').read_text(),'query':r['QUERY (EN / KR)'],'experiment':r['EXPERIMENT'],'sources':r['EVENT SOURCE COUNT'],'activities':aa}
    for p in (R/'private').glob('*.sql'):
        events(p.with_name(p.stem+'_events.csv'),run_sql(c,p))
    for q in ('B01','B02','B03'):
        g=R/'semantic_check/evaluation'/q;events(g/'events.csv',run_sql(c,g/'gold.sql'))
for i,(d,qs) in enumerate(digest_groups.items(),1):
    for r in registry:
        if r['QUERY ID'] in qs:r['GOLD GROUP ID']=f'G{i:03d}';r['SAME GOLD QUERY IDS']=','.join(qs)
for a in (49,53,57):
    assert all(all_gold[qid(a)]==all_gold[qid(n)] for n in range(a,a+4))
for a in (13,16,19,22):
    refs=[Counter((x[1],x[2],x[3],x[4],x[5]) for x in evidence[qid(n)]) for n in range(a,a+3)]
    assert refs[0]==refs[1]==refs[2]
conditions=0
for v in manifest:
    with sqlite3.connect(R/v['database_path']) as c:
        for q in v['question_ids']:
            assert run_sql(c,R/'gold'/q/'gold.sql')==all_gold[q],(v['variant_id'],q)
            conditions+=1
assert conditions==108
# Refresh pilot overlap using physical occurrence identity, not coincident timestamp triples.
pilot=[qid(n) for n in range(1,13)]
def os(q):return Counter((x[1],x[2],x[3],x[4],x[5]) for x in evidence[q])
pilot_occ={q:os(q) for q in pilot}
for r in registry[12:]:
    q=r['QUERY ID'];e=os(q);related=[(p,sum((e&o).values())) for p,o in pilot_occ.items()];related=[(p,n) for p,n in related if n]
    union=Counter()
    for o in pilot_occ.values():union|=o
    shared=sum((e&union).values())
    r['PILOT EVENT OVERLAP RATIO']=f'{shared/sum(e.values()):.6f}'
    r['PILOT RELATED QUERY IDS']=','.join(p for p,n in related) or 'None'
    r['PILOT GOLD RELATION']='Same Gold' if any(all_gold[q]==all_gold[p] for p in pilot) else 'Shared occurrences' if shared else 'None'
    r['PILOT RELATION DETAIL']='; '.join(f'{p}: {n}' for p,n in related) or 'None'
csvwrite(E/'query_registry.csv',registry);csvwrite(E/'test_registry.csv',registry[12:])
gs=[]
for r in registry:
    q=r['QUERY ID'];m=metadata[q];gs.append({'query_id':q,'experiment':r['EXPERIMENT'],'gold_group_id':r['GOLD GROUP ID'],'cases':m['cases'],'events':m['events'],'multiset_sha256':m['digest']})
csvwrite(E/'gold_summary.csv',gs)
pjs=[]
for r in registry[:12]:
    en,kr=r['QUERY (EN / KR)'].split('\n',1);pjs.append({'question_id':r['QUERY ID'],'question_en':en,'question_kr':kr})
save(E/'query_registry.json',pjs)
for name,rs in [('model_questions.jsonl',registry[:12]),('model_questions_test.jsonl',registry[12:])]:
    (E/name).write_text(''.join(json.dumps({'question_id':r['QUERY ID'],'text':r['QUERY (EN / KR)'].split('\n',1)[0]},ensure_ascii=False)+'\n' for r in rs))
policy=load(E/'case_key_policy.json')
policy['mappings']['Passenger Leg']['verified_rows']=len(legs);policy['mappings']['Bag Leg']['verified_rows']=len(bags);policy['mappings']['Flight']['verified_rows']=len(T['flights'])
policy['secondary']['Q55/Q56']='Passenger Leg secondary only with full-scope bijection; current fixture has repeat visits, so not equivalent.'
save(E/'case_key_policy.json',policy)
# Scope the existing approved semantic aliases uniformly to all queries using the same activities.
aliases=load(E/'approved_activity_aliases.json');canonical=aliases.get('Q02',{});canonical.update({'Handling Start':['Ground Handling Start','Ground Handling Started','Handling Started'],'Aircraft Ready':['Aircraft Readiness','Aircraft Prepared','Aircraft Preparation Complete']})
save(E/'approved_activity_aliases.json',{q:{a:canonical[a] for a in m['activities'] if a in canonical} for q,m in metadata.items() if any(a in canonical for a in m['activities'])})
# Older diagnostic mappings are not meaningful after generating new physical occurrences.
sm=R/'semantic_check/evaluation/scan_id_mapping.csv'
if sm.exists():sm.unlink()
(R/'semantic_check/README.md').write_text((R/'semantic_check/README.md').read_text()+'\nStochastic v2: the old scan-ID remapping receipt is retired; scan IDs are opaque at generation. B01–B03 reference CSVs were replayed against the new L15 input. This is not a completed semantic recovery experiment.\n')
# Update documentation without claiming human or production-scorer approval.
receipt={'version':VERSION,'seed':summary['seed'],'status':'candidate; human review and production scorer pending','sqlite_conditions_passed':conditions,'independent_occurrence_comparisons':len(all_gold),'nested_schema_check':'PASS','integrity_and_fk':'PASS','generator_summary':summary,'production_scorer':'NOT_RUN','human_semantic_review':'PENDING','model_inference':'NOT_RUN'}
save(E/'verification.json',receipt)
(R/'docs/queries.md').write_text('# Request catalog — '+VERSION+'\n\n72 requests, 108 DB–request conditions. Evaluator-only references. Human review pending.\n\n| ID | Request (English) | Case | Activities | Cases | Events | Reference files |\n|---|---|---|---:|---:|---:|---|\n'+'\n'.join(f"| {q} | {m['query'].splitlines()[0]} | {m['case']} | {m['activity_count']} | {m['cases']} | {m['events']} | [CSV](../gold/{q}/events.csv) · [DFG](../gold/{q}/dfg.svg) · [SQL](../gold/{q}/gold.sql) · [PI](../gold/{q}/pi.json) · [ESpec](../gold/{q}/espec.json) |" for q,m in metadata.items())+'\n')
(R/'evaluation/semantic_gold_review_20261127.md').write_text('# Stochastic v2 automated review\n\nThe prior PM-Scope1 review is preserved in git history. Current validation: 108 SQL conditions and 72 independently reconstructed occurrence multisets. Human semantic review and production scorer integration remain pending.\n\n| Query | Case | Activities | Cases | Events |\n|---|---|---:|---:|---:|\n'+'\n'.join(f"| {q} | {m['case']} | {m['activity_count']} | {m['cases']} | {m['events']} |" for q,m in metadata.items())+'\n')
# Preserve dated audit evidence as historical instead of misrepresenting it as current.
for fn in ('timestamp_query_audit.csv','interval_audit.csv','pm_scope_revision_20261127.md'):
    p=E/fn
    if p.exists():
        archive=R/'docs/archive'/('pm_scope1_'+fn);archive.parent.mkdir(exist_ok=True);shutil.move(p,archive)
csvwrite(E/'timestamp_query_audit.csv',[{'query_id':q,'cases':m['cases'],'events':m['events'],'ties':m['ties'],'variants':m['variants'],'status':'source occurrence comparison PASS'} for q,m in metadata.items()])
stats=json.loads(subprocess.check_output([sys.executable,str(R/'docs/analyze_dataset.py')],text=True));save(R/'docs/dataset_statistics.json',stats)
(R/'docs/dataset_analysis.md').write_text('# Stochastic v2 dataset analysis\n\nCurrent counts and actual distributions: [generator preview](../source/stochastic_v2_generator_preview.json) and [statistics](dataset_statistics.json).\n\n| Variant | Tables | Rows |\n|---|---:|---:|\n'+'\n'.join(f"| {v['variant_id']} | {v['table_count']} | {v['row_count']} |" for v in manifest)+'\n\nSource-diversity event counts are not forced equal. Fixed six jobs and one boarding session per flight preserve ground-service experiment structure. Human approval pending.\n')
# Compact self-contained review payload. Each event includes source table, row identity and occurrence column.
payload={'version':VERSION,'manifest':manifest,'records':records,'queries':metadata,'events':evidence,'registry':registry,'summary':summary}
template=(R/'docs/review_v2_template.html').read_text()
(R/'docs/scenario.html').write_text(template.replace('/*__PAYLOAD__*/null',json.dumps(payload,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')))
# Current top-level documentation generated from actual counts; no stale claims.
variant_rows='\n'.join(f"| [{v['variant_id'].upper()}](variants/{v['variant_id']}/README.md) | {v['table_count']} | {v['row_count']} | [SQLite]({v['database_path']}) · [DD]({v['dictionary_path']}) |" for v in manifest)
(R/'README.md').write_text(f"""# AirlineFlow — {VERSION}

Synthetic relational event-log extraction benchmark. **100 turnarounds, 200 operating legs, {len(legs):,} passenger legs; 72 requests / 108 DB–request conditions.**

## Database variants
| Variant | Tables | Rows | Inputs |
|---|---:|---:|---|
{variant_rows}

## Review
- [Integrated reference review](docs/scenario.html) (download and open locally; evaluator-only).
- [Query catalog](docs/queries.md) · [Gold summary](evaluation/gold_summary.csv) · [Registry](evaluation/query_registry.csv)
- [Design](docs/stochastic_fixture_v2.md) · [Generator configuration](source/stochastic_v2_config.json) · [Realized population](source/stochastic_v2_generator_preview.json)
- [Verification receipt](evaluation/verification.json) · [Analysis](docs/dataset_analysis.md)

## Reproduce
Run node source/generate_records_v2.mjs EMPTY_OUTPUT_DIRECTORY to regenerate records. Run python verify.py for read-only checks. The release build script regenerate_v2.py requires Node, Python and Graphviz and is intended for an isolated checkout.

## Validation
108 SQLite-query comparisons and 72 independent occurrence reconstructions passed in the release build. Human review and production scorer integration remain pending. No model inference performed. The older PM-Scope1 fixture remains in git history. Model input is only the chosen DB, its general DD, and request text. Never include evaluator metadata or the review HTML.
""")
for v in manifest:
    p=R/'variants'/v['variant_id']/'README.md'
    p.write_text(f"# {v['variant_id'].upper()} — {VERSION}\n\n{v['table_count']} tables; {v['row_count']} rows.\n\n[SQLite](input/database.sqlite) · [Data dictionary](input/data_dictionary.json) · [Schema](input/schema.sql) · [ERD](docs/schema.svg) · [Dataset home](../../README.md)\n")
(R/'variants/README.md').write_text('# Database variants\n\n| Variant | Tables | Rows |\n|---|---:|---:|\n'+'\n'.join(f"| [{v['variant_id']}]({v['variant_id']}/README.md) | {v['table_count']} | {v['row_count']} |" for v in manifest)+'\n')
print(json.dumps({k:v for k,v in receipt.items() if k!='generator_summary'},indent=2))
