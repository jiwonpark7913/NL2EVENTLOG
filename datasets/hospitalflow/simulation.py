"""Seeded illustrative care pathways; no real patient data or fitted clinical distributions."""
import random

SEED=20261103

def populate(ins,event,hist,time,counts):
 rng=random.Random(SEED)
 # A longer tail is explicitly represented in this small evaluation sample.
 sizes={'LAB':[0,1,2,1,0,4,1,2,7,1,3,0,2,1,5],
        'MED':[2,0,1,3,1,0,5,2,1,7,0,1,3,2,1],
        'PROC':[0,1,0,2,1,0,1,3,0,1,2,0,1,1,4]}
 # Independent shuffled ID assignments. A small shared pool is intentional:
 # equal local IDs across order tables identify different requests.
 ids={}
 common=[30000117,30000691,30000983]
 for kind,ns in [('LAB',31000000),('MED',32000000),('PROC',33000000)]:
  pool=common+rng.sample(range(ns,ns+99999),sum(sizes[kind])+5)
  rng.shuffle(pool);ids[kind]=iter(pool)
 # Ensure shared values are actually represented, without aligning by admission.
 for kind in ids:
  pool=common+rng.sample(range({'LAB':31000000,'MED':32000000,'PROC':33000000}[kind],{'LAB':31000000,'MED':32000000,'PROC':33000000}[kind]+99999),sum(sizes[kind])-3)
  rng.shuffle(pool);ids[kind]=iter(pool)
 def minute(lo,hi):return rng.randint(lo,hi)/60
 def draw_stay():return max(36*60,min(240*60,round(rng.lognormvariate(8.3,.65))))/60
 def add_order(kind,oid,subject,a,base,end,serial):
  objs=['P:'+str(subject),kind+':'+str(oid)]+(['A:'+str(a)] if a else [])
  entered=base+minute(22+serial*71,64+serial*71)
  reviewed=entered+minute(12,93)
  cancelled=kind=='PROC' and serial%3==1
  pending=kind=='LAB' and serial%5==3
  hist(kind+':'+str(oid),'ENTERED',entered,objs)
  hist(kind+':'+str(oid),'REVIEWED',reviewed,objs)
  if serial%4==0:hist(kind+':'+str(oid),'REVIEWED',reviewed+minute(7,39),objs)
  milestone=reviewed+minute(19,116)
  if kind=='LAB':
   latest=milestone
   if not pending:
    event('LAB:'+str(oid)+':received','Specimen Received',milestone,objs)
    for j in range(rng.choice([1,1,2,3,5])):
     counts['lab']+=1;i=counts['lab'];h=milestone+minute(6,55)+j*minute(7,21);stored=h+minute(30,240);latest=max(latest,stored)
     item,label,unit,val=rng.choice([(1001,'Creatinine','mg/dL',round(rng.uniform(.5,2.3),2)),(1002,'Sodium','mmol/L',round(rng.uniform(130,146),1)),(1003,'Hemoglobin','g/dL',round(rng.uniform(9,16),1))])
     ins('labevents',labevent_id=i,order_id=oid,itemid=item,charttime=time(h),storetime=time(stored),valuenum=val,valueuom=unit)
     event('LABEV:'+str(i)+':chart','Lab Measurement Charted',h,objs);event('LABEV:'+str(i)+':result','Lab Result Available',stored,objs)
   verified=latest+minute(13,127)
   ins('lab_order',order_id=oid,subject_id=subject,hadm_id=a,specimen_received_at=None if pending else time(milestone),results_verified_at=None if pending else time(verified))
   if not pending:event('LAB:'+str(oid)+':verified','Lab Results Verified',verified,objs)
  elif kind=='MED':
   # Prescription is separate from each dispensing and each dose occurrence.
   unfinished=a in (20000014,20000015) or serial%7==5
   stopped=None if unfinished else min(end-minute(31,195),milestone+minute(12*60,28*60))
   ins('medication_order',order_id=oid,hadm_id=a,medication=rng.choice(['Acetaminophen','Amoxicillin','Metformin','Omeprazole']),stopped_at=None if stopped is None else time(stopped))
   for batch in range(rng.choice([0,1,1,1,2])):
    counts['pharmacy']+=1;ph=40000000+counts['pharmacy'];disp=milestone+batch*minute(2*60,4*60)
    ins('pharmacy',pharmacy_id=ph,order_id=oid,dispensed_at=time(disp));event('PHARM:'+str(ph)+':dispense','Medication Dispensed',disp,objs)
    h=disp
    for j in range(rng.choice([0,1,2,3,5])):
     counts['dose']+=1;i=counts['dose'];h+=minute(42,147)
     if stopped is not None and h>=stopped:break
     given=(serial+j+batch)%5!=1
     ins('emar',emar_id=i,pharmacy_id=ph,charttime=time(h),event_txt='Administered' if given else 'Not Given',storetime=time(h+minute(2,57)))
     event('EMAR:'+str(i),'Medication Administered' if given else 'Medication Not Given',h,objs)
   if stopped is not None:event('MED:'+str(oid)+':stop','Medication Stopped',stopped,objs)
  else:
   ins('procedure_order',order_id=oid,hadm_id=a,procedure_name=rng.choice(['Bronchoscopy','Wound Debridement','Endoscopy']),preparation_completed_at=None if cancelled else time(milestone))
   if cancelled:hist(kind+':'+str(oid),'CANCELLED',reviewed+minute(4,17),objs)
   else:
    event('PROC:'+str(oid)+':prep','Procedure Preparation Completed',milestone,objs)
    for j in range(rng.choice([1,1,2,3])):
     counts['proc']+=1;i=counts['proc'];h=milestone+minute(28,120)+j*minute(130,210);finish=h+minute(21,155);is_open=a in (20000014,20000015) and j==0
     ins('procedure_episode',procedureevent_id=i,order_id=oid,starttime=time(h),endtime=None if is_open else time(finish),storetime=time(h+minute(3,35)))
     event('PROCEV:'+str(i)+':start','Procedure Started',h,objs)
     if not is_open:event('PROCEV:'+str(i)+':end','Procedure Completed',finish,objs)
 # Parents are inserted before children. The per-order insert is staged below to
 # preserve business chronology without turning SQL insertion order into time.
 staged=[]
 original_ins=ins
 def stage(t,**r):staged.append((t,r))
 ins=stage
 # hist closes over the real insertion helper: disable FK checks only by staging
 # all rows in main before replay; supplied hist callback is wrapped there.
 for patient in range(1,13):
  subject=10000000+patient;po='P:'+str(subject)
  ins('patients',subject_id=subject,gender='F' if patient%2 else 'M')
  next_base=patient*400+minute(3,119)
  if patient%2:
   h=next_base-minute(150,1500);ins('patient_profile',subject_id=subject,profile_verified_at=time(h),preferred_language='English');event('PAT:'+str(subject)+':profile','Patient Profile Verified',h,[po])
  if patient==12:continue
  for repeat in range(2 if patient<=4 else 1):
   counts['adm']+=1;idx=counts['adm'];a=20000000+idx;ao='A:'+str(a);base=next_base;end=base+draw_stay();ongoing=idx>=14
   next_base=end+minute(48*60,240*60)
   ed=base-minute(17,263) if idx%2 else None
   ins('admissions',hadm_id=a,subject_id=subject,edregtime=None if ed is None else time(ed),admittime=time(base),discharge_authorized_at=None if ongoing else time(end-minute(22,225)),dischtime=None if ongoing else time(end))
   if ed is not None:event('ADM:'+str(a)+':ed','Emergency Department Registered',ed,[po,ao])
   event('ADM:'+str(a)+':in','Hospital Admitted',base,[po,ao])
   if not ongoing:
    # Use the stored authorization instant, not a second random draw.
    auth=staged[-1][1]['discharge_authorized_at'];
    from datetime import datetime
    ah=(datetime.fromisoformat(auth.replace('Z','+00:00'))-datetime.fromisoformat('2026-01-01T00:00:00+00:00')).total_seconds()/3600
    event('ADM:'+str(a)+':auth','Discharge Authorized',ah,[po,ao]);event('ADM:'+str(a)+':out','Hospital Discharged',end,[po,ao])
   if idx%3==1:
    signed=end-minute(7,19);ins('admission_detail',hadm_id=a,discharge_summary_signed_at=time(signed),summary_status='SIGNED');event('ADM:'+str(a)+':summary','Discharge Summary Signed',signed,[po,ao])
   for kind in ['LAB','MED','PROC']:
    for serial in range(sizes[kind][idx-1]):add_order(kind,next(ids[kind]),subject,a,base,end,serial)
 # Authored outpatient requests: patient is known, hospital admission is absent.
 for j in range(4):add_order('LAB',35000000+rng.randrange(1000,9999),10000001+j,None,patient*400+200+j*30,patient*400+400,j)
 rank={t:i for i,t in enumerate(['patients','patient_profile','admissions','admission_detail','lab_order','medication_order','procedure_order','pharmacy','labevents','emar','procedure_episode'])}
 for t,row in sorted(staged,key=lambda x:rank[x[0]]):original_ins(t,**row)
