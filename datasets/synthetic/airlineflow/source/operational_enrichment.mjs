import {readFileSync} from 'node:fs';
const schema=JSON.parse(readFileSync(new URL('./operational_fields_v1.json',import.meta.url),'utf8'));
export function enrichOperationalRecords(records,seed){
  const hash=(...a)=>{let h=2166136261;for(const c of a.join('|')){h^=c.charCodeAt(0);h=Math.imul(h,16777619)}return h>>>0};
  const choose=(a,k,...x)=>a[hash(seed,k,...x)%a.length],num=(k)=>Number(String(k).match(/\d+$/)?.[0]||0),pad=(n,w)=>String(n).padStart(w,'0');
  const obj=t=>records[t].rows.map(r=>Object.fromEntries(records[t].columns.map((c,i)=>[c,r[i]])));
  const T=Object.fromEntries(Object.keys(records).map(t=>[t,obj(t)]));
  const by=t=>new Map(T[t].map(r=>[Object.values(r)[0],r]));
  const group=(rows,k)=>{const m=new Map();for(const r of rows){if(!m.has(r[k]))m.set(r[k],[]);m.get(r[k]).push(r)}return m};
  const flights=by('flights'),dispatch=new Map(T.flight_dispatch.map(r=>[r.flight_id,r])),legs=by('passenger_legs'),tickets=by('tickets'),bookings=by('bookings'),bags=by('bag_legs'),visits=by('security_visits'),cp=by('checkpoints');
  const acts=group(T.passenger_actions,'leg_id'),scan=group(T.bag_scans,'bag_leg_id'),sec=group(T.security_events,'visit_id'),byTicket=group(T.passenger_legs,'ticket_id'),byFlight=group(T.passenger_legs,'flight_id');
  const ticketMoney=new Map(),bookingMoney=new Map(),legMeta=new Map(),ticketMeta=new Map(),checkins=new Map();
  for(const [fid,ll] of byFlight){
    const checked=ll.filter(l=>(acts.get(l.leg_id)||[]).some(a=>a.action_code==='CK')).sort((a,b)=>acts.get(a.leg_id).find(x=>x.action_code==='CK').action_at.localeCompare(acts.get(b.leg_id).find(x=>x.action_code==='CK').action_at)||a.leg_id.localeCompare(b.leg_id));
    checked.forEach((l,i)=>checkins.set(l.leg_id,i+1));
    const business=checked.filter(l=>hash(seed,'fare',l.ticket_id)%10===0),economy=checked.filter(l=>!business.includes(l));
    for(const [ls,start,letters] of [[business,1,'ACDF'],[economy,5,'ABCDEF']])ls.forEach((l,i)=>{legMeta.set(l.leg_id,{seat_no:String(start+Math.floor(i/letters.length))+letters[i%letters.length]})});
  }
  for(const [tid,ll] of byTicket){
    const product=hash(seed,'fare',tid)%10===0?'BUSINESS':choose(['ECONOMY_SAVER','ECONOMY_FLEX'],'product',tid);
    let base=0,tax=0;
    ll.slice().sort((a,b)=>flights.get(a.flight_id).scheduled_offblock.localeCompare(flights.get(b.flight_id).scheduled_offblock)).forEach((l,i)=>{
      const x=(acts.get(l.leg_id)||[]),status=x.some(a=>a.action_code==='BD')?'BOARDED':x.some(a=>a.action_code==='CK')?'CHECKED_IN':'BOOKED';
      const b=(product==='BUSINESS'?360000:product==='ECONOMY_FLEX'?190000:110000)+1000*(hash(seed,'fareamount',l.leg_id)%81),t=27000+1000*(hash(seed,'tax',l.leg_id)%18);
      base+=b;tax+=t;legMeta.set(l.leg_id,{...legMeta.get(l.leg_id),coupon_no:i+1,booking_class:product==='BUSINESS'?'J':product==='ECONOMY_FLEX'?'Y':'M',cabin_class:product==='BUSINESS'?'BUSINESS':'ECONOMY',fare_basis:product==='BUSINESS'?'JDEMO':product==='ECONOMY_FLEX'?'YFLEX':'MSAVER',checkin_sequence:checkins.get(l.leg_id)??null,departure_status:status,checked_bag_allowance:product==='BUSINESS'?2:1,segment_base_fare:b,segment_tax:t});
    });
    ticketMoney.set(tid,[base,tax]);ticketMeta.set(tid,product);
    const bid=tickets.get(tid).booking_id,prev=bookingMoney.get(bid)||[0,0];bookingMoney.set(bid,[prev[0]+base,prev[1]+tax]);
  }
  const channel=b=>choose(['WEB','MOBILE','AGENCY','CONTACT_CENTER'],'channel',b),terminal=st=>st==='ICN'?'T1':'T1';
  const nameParts={KR:[['Jiwon','Minseo','Jinwoo','Soyeon'],['Kim','Lee','Park','Choi']],JP:[['Haruka','Yuki','Ren','Sora'],['Sato','Suzuki','Takahashi','Ito']],US:[['Alex','Jordan','Taylor','Morgan'],['Miller','Smith','Brown','Davis']],DE:[['Lena','Lukas','Mia','Noah'],['Meyer','Schmidt','Weber','Fischer']],SG:[['Kai','Jia','Wei','Mei'],['Tan','Lim','Ng','Chua']]};
  const ap={ICN:['Incheon International Airport','RKSI','KR','Asia/Seoul'],KIX:['Kansai International Airport','RJBB','JP','Asia/Tokyo'],NRT:['Narita International Airport','RJAA','JP','Asia/Tokyo']};
  const station=l=>dispatch.get(legs.get(l).flight_id).origin;
  const methods={
    bookings:r=>{const [b,t]=bookingMoney.get(r.booking_id);return ['R'+pad(num(r.booking_id),5),channel(r.booking_id),'CONFIRMED','KRW',b,t,b+t,'PAID']},
    passengers:r=>{const [gn,fn]=nameParts[r.nationality_code]||nameParts.US;return [choose(gn,'given',r.passenger_id),choose(fn,'family',r.passenger_id),({KR:'ko',JP:'ja',DE:'de',SG:'en',US:'en'})[r.nationality_code]||'en',choose([null,null,null,'SILVER','GOLD'],'tier',r.passenger_id)]},
    tickets:r=>{const [b,t]=ticketMoney.get(r.ticket_id);return ['000'+pad(num(r.ticket_id),10),'ISSUED',channel(r.booking_id),'KRW',b,t,b+t,ticketMeta.get(r.ticket_id)]},
    passenger_legs:r=>{const m=legMeta.get(r.leg_id);return schema.passenger_legs.map(([k])=>m[k]??null)},
    passenger_actions:r=>{const st=station(r.leg_id),ch=r.action_code==='CK'?choose(['WEB','MOBILE','COUNTER','KIOSK'],'checkin',r.leg_id):'GATE';return [st,ch,['WEB','MOBILE'].includes(ch)?null:terminal(st),['WEB','MOBILE'].includes(ch)?ch+'-APP':st+'-'+ch+'-'+pad(hash(seed,'dev',r.action_id)%8+1,2),r.action_code==='RJ'?'REJECTED':'OK',r.action_code==='RJ'?choose(['READ_ERROR','SEQUENCE_MISMATCH','RETRY_REQUIRED'],'reject',r.action_id):null]},
    bag_legs:r=>{const d=dispatch.get(legs.get(r.leg_id).flight_id);return ['0999'+pad(num(r.bag_leg_id),6),Math.round((6+hash(seed,'kg',r.bag_leg_id)%260/10)*10)/10,choose(['STANDARD','STANDARD','STANDARD','STANDARD','SPECIAL','OVERSIZE'],'bagtype',r.bag_leg_id),d.origin,d.destination,(scan.get(r.bag_leg_id)||[]).some(x=>x.scan_code==='B204')?'LOADED':'ACCEPTED']},
    bag_scans:r=>{const st=station(bags.get(r.bag_leg_id).leg_id),loc=r.scan_code==='B101'?'BAG_DROP':'AIRCRAFT_LOADING';return [st,loc,st+'-'+loc+'-'+pad(hash(seed,'scanner',r.scan_id)%6+1,2),choose(['BARCODE','BARCODE','RFID'],'capture',r.scan_id),r.scan_code==='B204'?'CART-'+pad(hash(seed,'cart',bags.get(r.bag_leg_id).leg_id)%12+1,2):null,r.scan_code==='B101'?'BHS':'BRS']},
    checkpoints:r=>[terminal(r.zone),r.zone+' passenger checkpoint','PASSENGER',4+hash(seed,'lanes',r.checkpoint_id)%5,'OPEN'],
    security_visits:r=>{const pts=(sec.get(r.visit_id)||[]).map(x=>x.point),c=cp.get(r.checkpoint_id),lanes=4+hash(seed,'lanes',r.checkpoint_id)%5;return [choose(['STANDARD','STANDARD','STANDARD','PRIORITY'],'queue',r.visit_id),pts.includes('S')?1+hash(seed,'lane',r.visit_id)%lanes:null,pts.includes('C')?'COMPLETED':pts.includes('S')?'IN_SCREENING':'QUEUED']},
    security_events:r=>{const v=visits.get(r.visit_id),st=cp.get(v.checkpoint_id).zone;return [st,r.point==='Q'?'QUEUE_MONITOR':'SCREENING_SYSTEM',st+'-'+(r.point==='Q'?'QUEUE':'SCREEN')+'-'+pad(hash(seed,'secdev',r.visit_id)%4+1,2),r.point==='Q'?'SENSOR':'SYSTEM_RECORD',choose(['VALIDATED','VALIDATED','VALIDATED','UNREVIEWED'],'quality',r.event_id)]},
    airlines:r=>{const d=T.flight_dispatch.find(x=>byAircraft.get(x.tail_id).airline_id===r.airline_id);return [flights.get(d.flight_id).flight_no.slice(0,2),'KR','ICN','PASSENGER']},
    airports:r=>[...ap[r.airport_id],'INTERNATIONAL'],
    aircraft:r=>['DEMO-'+r.tail_id,r.model==='A320'?'Airbus':'Boeing',r.model==='A320'?'A320':'B738',2013+hash(seed,'year',r.tail_id)%11,r.model==='A320'?180:189,'ACTIVE'],
    employees:r=>['Synthetic Dispatcher '+r.employee_id,'OPERATIONS_CONTROL','ICN','CURRENT','ACTIVE'],
    flight_dispatch:r=>['IFR',r.destination==='ICN'?'GMP':r.destination==='KIX'?'ITM':'HND',7200+100*(hash(seed,'fuel',r.flight_id)%21),5500+100*(hash(seed,'minfuel',r.flight_id)%11),'ASSIGNED','OCC']
  };
  const byAircraft=by('aircraft');
  for(const [t,fields] of Object.entries(schema)){
    const rec=records[t];rec.columns.push(...fields.map(x=>x[0]));
    rec.rows.forEach((row,i)=>{const r=T[t][i],extra=methods[t](r);if(extra.length!==fields.length||extra.some((v,j)=>v===null&&fields[j][1].includes('NOT NULL')))throw Error('enrichment arity/null '+t);row.push(...extra);if(t==='passengers')row[rec.columns.indexOf('display_name')]=extra[0]+' '+extra[1]});
  }
  return records;
}
