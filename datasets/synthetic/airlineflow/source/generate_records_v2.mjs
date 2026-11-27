// Candidate generator; Node.js 18+; no dependencies. Never overwrites a released fixture.
import { readFileSync, writeFileSync, mkdirSync, existsSync, readdirSync } from 'node:fs';
import { resolve, join } from 'node:path';
import { fileURLToPath } from 'node:url';
export function generateAirlineFlow(config) {
  const seed=config.seed;
  function random(s) {return ()=>{s|=0;s=s+0x6D2B79F5|0;let z=Math.imul(s^s>>>15,1|s);z=z+Math.imul(z^z>>>7,61|z)^z;return ((z^z>>>14)>>>0)/4294967296;};}
  const sched=random(seed+1), itin=random(seed+2), beh=random(seed+3), timing=random(seed+4), ids=random(seed+5), order=random(seed+6);
  const int=(r,a,b)=>a+Math.floor(r()*(b-a+1));
  const pick=(r,a)=>a[int(r,0,a.length-1)];
  const weighted=(r,vals,w)=>{let x=r();for(let i=0;i<vals.length;i++){x-=w[i];if(x<0)return vals[i];}return vals.at(-1);};
  const shuffle=(r,a)=>{for(let i=a.length-1;i>0;i--){let j=int(r,0,i);[a[i],a[j]]=[a[j],a[i]];}return a;};
  const keyset=new Set();
  function id(prefix){let k;do{k=prefix+"-"+Array.from({length:3},()=>int(ids,0,0xffffffff).toString(16).padStart(8,"0")).join("");}while(keyset.has(k));keyset.add(k);return k;}
  const cols={
    flights:"flight_id flight_no scheduled_offblock scheduled_inblock",turnarounds:"turn_id inbound_id outbound_id handling_started_at ready_at",boarding_sessions:"session_id flight_id started_at closed_at",handling_jobs:"job_id turn_id job_code started_at finished_at posted_at service_provider_code priority_code work_zone_code",movement_reports:"report_id flight_id kind value_at received_at source_code validation_code message_format_code",bookings:"booking_id booked_at",passengers:"passenger_id display_name date_of_birth nationality_code gender_code",tickets:"ticket_id booking_id passenger_id",passenger_legs:"leg_id ticket_id flight_id",passenger_actions:"action_id leg_id action_code action_at",bag_legs:"bag_leg_id leg_id bag_tag",bag_scans:"scan_id bag_leg_id scan_code scanned_at",checkpoints:"checkpoint_id zone",security_visits:"visit_id leg_id checkpoint_id",security_events:"event_id visit_id point observed_at received_at",airlines:"airline_id name",airports:"airport_id city",aircraft:"tail_id airline_id model",employees:"employee_id airline_id role",flight_dispatch:"dispatch_id flight_id tail_id origin destination dispatcher_id assigned_at"
  };
  const records=Object.fromEntries(Object.entries(cols).map(([t,c])=>[t,{columns:c.split(" "),rows:[]}]));
  const add=(t,...r)=>{if(r.length!==records[t].columns.length)throw Error("row arity: "+t);records[t].rows.push(r);};
  const stamp=t=>new Date(t*1000).toISOString().slice(0,19).replace("T"," ");
  // All three synthetic airports share UTC+09; timestamps are wall-clock KST/JST.
  const base=Date.UTC(2026,11,1)/1000;
  const minute=60,day=86400;
  const mins=(a,b)=>int(timing,a*minute,b*minute);
  const airlines=[id("AL"),id("AL")], staff=[id("EM"),id("EM")];
  airlines.forEach((a,i)=>{add("airlines",a,"Demo Air "+(i+1));add("employees",staff[i],a,"Dispatcher");});
  [["ICN","Incheon"],["KIX","Osaka"],["NRT","Tokyo"]].forEach(a=>add("airports",...a));
  const tails=Array.from({length:config.aircraft},(_,i)=>({key:id("AC"),airline:i%2,remote:i%2?"NRT":"KIX",num:i}));
  tails.forEach(t=>add("aircraft",t.key,airlines[t.airline],t.airline?"B737":"A320"));
  const checkpoints=Array.from({length:3},(_,i)=>({key:id("CP"),zone:["ICN","KIX","NRT"][i]}));
  checkpoints.forEach(c=>add("checkpoints",c.key,c.zone));
  const flights=[], turns=[], scenarios={};
  function flight(t,origin,destination,sout,sin,out,air,land,inb,bs,bc,bl) {
    const f={key:id("FL"),origin,destination,sout,sin,out,air,land,inb,bs,bc,bl,tail:t.key,target:int(itin,config.passengers_per_flight[0],config.passengers_per_flight[1])};
    f.remaining=f.target;
    const no=(t.airline?"BX":"AX")+String(100+t.num*2+(origin==="ICN"?1:0));
    add("flights",f.key,no,stamp(sout),stamp(sin));
    add("boarding_sessions",id("BS"),f.key,stamp(bs),stamp(bc));
    [["EST",sout+mins(-8,12),out-mins(12,30)],["OUT",out,out+mins(0,5)],["AIR",air,air+mins(0,5)],["LAND",land,land+mins(0,5)],["IN",inb,inb+mins(0,5)]].forEach(([k,v,r])=>add("movement_reports",id("MR"),f.key,k,stamp(v),stamp(r),pick(timing,["AODB","ACARS"]),pick(timing,["AUTO_CHECKED","OPS_REVIEWED"]),pick(timing,["AIDX","MVT","LOCAL"])));
    add("flight_dispatch",id("FD"),f.key,t.key,origin,destination,staff[t.airline],stamp(sout-3*3600));
    flights.push(f);return f;
  }
  for(let n=0;n<config.turnarounds;n++){
    const t=tails[n%tails.length], d=Math.floor(n/tails.length);
    const sout=base+d*day+(6+t.num)*3600;
    const out=sout+int(sched,-5,12)*minute, air=out+mins(8,18), land=air+mins(85,105), inb=land+mins(5,12);
    const bc=out-mins(8,13),bs=bc-mins(22,42);
    const inbound=flight(t,t.remote,"ICN",sout,sout+120*minute,out,air,land,inb,bs,bc,[bs-mins(10,18),bc-mins(1,3)]);
    const handling=inb+mins(1,4);
    const scenario=weighted(sched,["normal","clean","fuel","bag","boarding","overlap"],config.scenario_weights);
    scenarios[scenario]=(scenarios[scenario]||0)+1;
    const jobs={};
    const duration=(code)=>{let [lo,hi]=config.job_minutes[code];if(scenario==="clean"&&code==="CL"||scenario==="fuel"&&code==="FU"||scenario==="bag"&&code==="BL")lo=hi-5;return mins(lo,hi);};
    function job(code,start){jobs[code]=[start,start+duration(code)];}
    job("DP",handling+mins(1,4));
    job("UL",handling+mins(1,5));
    job("CL",jobs.DP[1]+mins(1,scenario==="overlap"?3:8));
    job("FU",jobs.DP[1]+mins(1,scenario==="overlap"?3:8));
    job("CA",jobs.DP[1]+mins(1,scenario==="overlap"?4:9));
    job("BL",Math.max(jobs.UL[1]+mins(1,5),handling+mins(18,26))+(scenario==="bag"?mins(10,20):0));
    const bs2=Math.max(jobs.CL[1],jobs.FU[1],jobs.CA[1])+mins(1,5);
    const bc2=bs2+mins(scenario==="boarding"?40:22,scenario==="boarding"?55:38);
    const ready=Math.max(bc2,...Object.values(jobs).map(x=>x[1]))+mins(1,6);
    const out2=ready+mins(3,10),air2=out2+mins(8,18),land2=air2+mins(85,105),in2=land2+mins(5,12);
    const outbound=flight(t,"ICN",t.remote,sout+220*minute,sout+340*minute,out2,air2,land2,in2,bs2,bc2,jobs.BL);
    const tid=id("TU");add("turnarounds",tid,inbound.key,outbound.key,stamp(handling),stamp(ready));
    const zones={DP:"PAX_BRIDGE",UL:"CARGO_HOLD",CL:"CABIN",FU:"RAMP",CA:"CABIN",BL:"CARGO_HOLD"};
    for(const [code,[start,finish]] of Object.entries(jobs))add("handling_jobs",id("HJ"),tid,code,stamp(start),stamp(finish),stamp(finish+mins(1,15)),pick(timing,["AIRLINE_GND","CONTRACTOR"]),timing()<.12?null:pick(timing,["STANDARD","HIGH","CRITICAL"]),zones[code]);
    turns.push({inbound,outbound,handling,ready,jobs});
  }
  // Allocate real airport-contiguous itineraries against flight-level sample capacities.
  const paths=[], partyHist={}, lengthHist={};
  const ordered=flights.slice().sort((a,b)=>a.out-b.out);
  while(ordered.some(f=>f.remaining>0)){
    const first=ordered.find(f=>f.remaining>0);
    const size=Math.min(first.remaining,weighted(itin,[1,2,3,4,5,6],config.party_weights));
    const intended=weighted(itin,[1,2,3,4],config.itinerary_weights);
    const route=[first];
    while(route.length<intended){
      const prev=route.at(-1);
      const candidates=ordered.filter(f=>f.origin===prev.destination&&f.out>=prev.inb+4*3600&&f.out<=prev.inb+8*day&&f.remaining>=size&&!route.includes(f));
      if(!candidates.length)break;
      route.push(pick(itin,candidates.slice(0,Math.min(12,candidates.length))));
    }
    for(const f of route)f.remaining-=size;
    const booking=id("BK");add("bookings",booking,stamp(first.sout-int(itin,7,45)*day));
    partyHist[size]=(partyHist[size]||0)+1;lengthHist[route.length]=(lengthHist[route.length]||0)+size;
    for(let k=0;k<size;k++){
      const p=id("PX"),ticket=id("TK");
      add("passengers",p,"Synthetic passenger "+p.slice(-8),`${int(itin,1945,2018)}-${String(int(itin,1,12)).padStart(2,"0")}-${String(int(itin,1,28)).padStart(2,"0")}`,itin()<.10?null:pick(itin,["KR","JP","US","DE","SG"]),pick(itin,["MALE","FEMALE","UNKNOWN"]));
      add("tickets",ticket,booking,p);
      const legs=route.map(f=>{let leg=id("PL");add("passenger_legs",leg,ticket,f.key);return {f,leg,state:"normal"};});
      paths.push(legs);
    }
  }
  const all=paths.flat(), terminals=shuffle(beh,paths.map(p=>p.at(-1)));
  const no=Math.round(all.length*config.state_weights.no_show), partial=Math.round(all.length*config.state_weights.incomplete), retry=Math.round(all.length*config.state_weights.retry);
  if(no+partial>terminals.length)throw Error("insufficient terminal legs");
  terminals.slice(0,no).forEach(x=>x.state="no_show");
  terminals.slice(no,no+partial).forEach(x=>x.state="incomplete");
  shuffle(beh,all.filter(x=>x.state==="normal")).slice(0,retry).forEach(x=>x.state="retry");
  const stateHist={},bagHist={},visitHist={},rejectHist={};
  function action(l,c,t){add("passenger_actions",id("PA"),l,c,stamp(t));}
  function visit(l,f,t,complete=true){const v=id("SV"),cp=checkpoints.find(c=>c.zone===f.origin);add("security_visits",v,l,cp.key);const st=t+mins(2,12),en=st+mins(1,5);let phases=complete?[["Q",t],["S",st],["C",en]]:beh()<.5?[["Q",t]]:[["Q",t],["S",st]];for(const [p,x] of phases)add("security_events",id("SE"),v,p,stamp(x),stamp(x+mins(0,4)));return en;}
  for(const x of all){
    const {f,leg:l,state}=x;stateHist[state]=(stateHist[state]||0)+1;
    if(state==="no_show"){bagHist[0]=(bagHist[0]||0)+1;visitHist[0]=(visitHist[0]||0)+1;rejectHist[0]=(rejectHist[0]||0)+1;continue;}
    const success=state==="normal"||state==="retry";
    const incomplete=state==="incomplete"?pick(beh,["pre_security","during_security","pre_gate","gate_reject"]):null;
    // Check-in precedes security and both remote and focal baggage loading windows.
    const ck=Math.min(f.bs-95*minute,f.bl[0]-35*minute)-mins(0,35);
    action(l,"CK",ck);
    const nb=weighted(beh,[0,1,2,3],config.bag_weights);
    bagHist[nb]=(bagHist[nb]||0)+1;
    for(let j=0;j<nb;j++){const bag=id("BG");add("bag_legs",bag,l,id("TAG"));add("bag_scans",id("SC"),bag,"B101",stamp(ck+mins(1,5)));if(success){const load=int(timing,f.bl[0],f.bl[1]);add("bag_scans",id("SC"),bag,"B204",stamp(load));}}
    let nv=0,rej=0;
    if(incomplete!=="pre_security"){
      let end=visit(l,f,ck+mins(10,22),incomplete!=="during_security");nv++;
      if(incomplete!=="during_security"&&beh()<config.revisit_rate){end=visit(l,f,end+mins(3,10),true);nv++;}
      if(end>f.bs)throw Error("security chronology");
      if(success||incomplete==="gate_reject"){
        rej=state==="retry"||incomplete==="gate_reject"?int(beh,1,3):0;
        // Quarter-minute discretization of boarding captures independently coincident scans.
        const slots=Math.floor((f.bc-f.bs-90)/15);
        const gate=f.bs+15*int(timing,8,slots);
        for(let i=0;i<rej;i++)action(l,"RJ",gate-(rej-i)*20);
        if(success)action(l,"BD",gate);
      }
    }
    visitHist[nv]=(visitHist[nv]||0)+1;rejectHist[rej]=(rejectHist[rej]||0)+1;
  }
  function assert(v,m){if(!v)throw Error(m);}
  const counts=Object.fromEntries(Object.entries(records).map(([k,v])=>[k,v.rows.length]));
  const perFlight=Object.fromEntries(flights.map(f=>[f.key,f.target]));
  const actualLegs={};for(const l of records.passenger_legs.rows)actualLegs[l[2]]=(actualLegs[l[2]]||0)+1;
  assert(flights.length===2*config.turnarounds&&turns.length===config.turnarounds,"flight/turnaround totals");
  assert(flights.every(f=>f.remaining===0&&actualLegs[f.key]===f.target),"capacity");
  assert(paths.every(p=>p.slice(1).every((x,i)=>p[i].f.destination===x.f.origin&&p[i].f.inb+4*3600<=x.f.out)),"itinerary continuity");
  assert(turns.every(t=>t.inbound.tail===t.outbound.tail&&t.inbound.inb<=t.handling&&t.ready<=t.outbound.out&&Object.values(t.jobs).every(j=>j[0]<=j[1]&&j[1]<=t.ready)),"turnaround constraints");
  for(const t of tails){const f=flights.filter(x=>x.tail===t.key).sort((a,b)=>a.out-b.out);assert(f.slice(1).every((x,i)=>f[i].inb<x.out&&f[i].destination===x.origin),"aircraft continuity");}
  const legFlights=Object.fromEntries(records.passenger_legs.rows.map(x=>[x[0],x[2]]));
  const seen=new Set();let duplicateBoarding=0;for(const x of records.passenger_actions.rows.filter(x=>x[2]==="BD")){const k=legFlights[x[1]]+"|"+x[3];if(seen.has(k))duplicateBoarding++;seen.add(k);}
  assert(bagHist[0]>0&&bagHist[2]>0&&visitHist[2]>0&&rejectHist[2]>0&&stateHist.incomplete>0&&stateHist.no_show>0&&duplicateBoarding>0,"coverage gates");
  for(const r of Object.values(records))shuffle(order,r.rows);
  const summary={seed,counts,flight_population:{min:Math.min(...Object.values(perFlight)),max:Math.max(...Object.values(perFlight)),total:all.length},party_histogram:partyHist,ticket_leg_histogram:lengthHist,passenger_state_histogram:stateHist,bags_per_leg:bagHist,visits_per_leg:visitHist,rejections_per_leg:rejectHist,turnaround_scenarios:scenarios,duplicate_flight_boarding_triples:duplicateBoarding,checks:"generator-level checks passed; SQLite and Gold not yet validated"};
  // Keep the original RNG consumption and business fixture exactly unchanged.
  // Independent seeded, collision-free numeric aliases are assigned only after generation.
  const groups=new Map();
  for(const r of Object.values(records))for(const row of r.rows)for(const v of row){
    if(typeof v==='string'&&keyset.has(v)){
      const prefix=v.split('-')[0];
      if(!groups.has(prefix))groups.set(prefix,new Set());
      groups.get(prefix).add(v);
    }
  }
  const shortRng=random(seed+871923),idMap={};
  for(const [prefix,values] of [...groups.entries()].sort(([a],[b])=>a.localeCompare(b))){
    const keys=[...values].sort();
    const width=keys.length<=1000?4:5,lo=10**(width-1),hi=10**width-1,used=new Set();
    if(keys.length>hi-lo+1)throw Error('ID capacity '+prefix);
    for(const k of keys){
      let n;do{n=int(shortRng,lo,hi);}while(used.has(n));used.add(n);
      idMap[k]=prefix+'-'+String(n);
    }
  }
  for(const r of Object.values(records))for(const row of r.rows)for(let i=0;i<row.length;i++)if(typeof row[i]==='string'&&Object.hasOwn(idMap,row[i]))row[i]=idMap[row[i]];
  summary.identifier_policy='short opaque seeded numeric IDs (4–5 digits; no business-role encoding)';
  summary.identifier_count=Object.keys(idMap).length;
  return {records,summary,idMap};
}
if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  if (process.argv.length !== 3) throw Error('Usage: node generate_records_v2.mjs EMPTY_OUTPUT_DIRECTORY');
  const out=resolve(process.argv[2]);
  if (existsSync(out) && readdirSync(out).length) throw Error('Output must be empty');
  mkdirSync(out,{recursive:true});
  const config=JSON.parse(readFileSync(new URL('./stochastic_v2_config.json',import.meta.url),'utf8'));
  const {records,summary,idMap}=generateAirlineFlow(config);
  writeFileSync(join(out,'records.json'),JSON.stringify(records)+'\n');
  writeFileSync(join(out,'generator_summary.json'),JSON.stringify(summary,null,2)+'\n');
  writeFileSync(join(out,'identifier_map.json'),JSON.stringify(idMap)+'\n');
  console.log(JSON.stringify(summary,null,2));
}
