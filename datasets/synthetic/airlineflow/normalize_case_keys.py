"""Evaluator-only reference. Caller supplies explicit ET, declared ordered key columns, and structured values.
Never infer a composite key from a display string; do not treat different ETs as the same ET.
Input event triples are (case key scalar/tuple, canonical activity label, timestamp)."""
from collections import Counter
from datetime import datetime

CANONICAL={'Flight':'flight_id','Passenger Leg':'leg_id','Bag Leg':'bag_leg_id','Security Visit':'visit_id','Turnaround':'turn_id','Boarding Session':'session_id','Handling Job':'job_id','Ticket':'ticket_id','Booking':'booking_id','Passenger':'passenger_id'}
APPROVED={('Flight',('flight_no','operating_date')):"SELECT flight_no,date(scheduled_offblock),flight_id FROM flights",('Passenger Leg',('ticket_id','flight_id')):'SELECT ticket_id,flight_id,leg_id FROM passenger_legs',('Passenger Leg',('passenger_id','flight_id')):'SELECT t.passenger_id,l.flight_id,l.leg_id FROM passenger_legs l JOIN tickets t USING(ticket_id)',('Bag Leg',('bag_tag','flight_id')):'SELECT b.bag_tag,l.flight_id,b.bag_leg_id FROM bag_legs b JOIN passenger_legs l USING(leg_id)'}
SECONDARY={('Q09','Turnaround'):'SELECT turn_id,outbound_id FROM turnarounds',('Q12','Turnaround'):'SELECT turn_id,outbound_id FROM turnarounds',('Q12','Boarding Session'):'SELECT session_id,flight_id FROM boarding_sessions',('Q51','Bag'):'SELECT bag_tag,bag_leg_id FROM bag_legs',('Q52','Bag'):'SELECT bag_tag,bag_leg_id FROM bag_legs',('Q55','Passenger Leg'):'SELECT leg_id,visit_id FROM security_visits',('Q56','Passenger Leg'):'SELECT leg_id,visit_id FROM security_visits',('Q51','Passenger Leg'):'SELECT leg_id,bag_leg_id FROM bag_legs',('Q52','Passenger Leg'):'SELECT leg_id,bag_leg_id FROM bag_legs'}

def strict_score(gold,pred):
 def counter(rs):return Counter((c,a,datetime.fromisoformat(t)) for c,a,t in rs)
 g,p=counter(gold),counter(pred);tp=sum((g&p).values());gn,pn=sum(g.values()),sum(p.values());pr=tp/pn if pn else 0.;re=tp/gn if gn else 0.
 return dict(exact=g==p,tp=tp,fp=pn-tp,fn=gn-tp,precision=pr,recall=re,f1=2*tp/(gn+pn) if gn+pn else 1.)

def mapping(conn,sql,scope):
 # Full-scope bijection, but reject an alternate key if it maps to any other DB entity.
 pairs=[(tuple(r[:-1]),r[-1]) for r in conn.execute(sql)]; scoped=[(k,v) for k,v in pairs if v in scope]
 if len(scoped)!=len(scope) or len({k for k,_ in scoped})!=len(scope) or {v for _,v in scoped}!=scope:raise ValueError('not a full-scope bijection')
 d=dict(scoped)
 if any(k in d and d[k]!=v for k,v in pairs):raise ValueError('ambiguous alternate key outside scope')
 return d

def convert(pred,d):
 def key(k):return tuple(k) if isinstance(k,(tuple,list)) else (k,)
 # Preserve out-of-scope predictions as unmatched keys rather than silently discarding them.
 return [(d.get(key(k),('__unmapped__',key(k))),a,t) for k,a,t in pred]

def evaluate(conn,query_id,gold,pred,gold_et,pred_et,key_columns):
 gold,pred=list(gold),list(pred);scope={r[0] for r in gold};kc=tuple(key_columns);canonical=CANONICAL.get(gold_et)
 if pred_et==gold_et and kc==(canonical,):return {'primary':strict_score(gold,pred),'secondary_exact':None,'diagnostic_exact':None}
 if pred_et==gold_et and (gold_et,kc) in APPROVED:
  d=mapping(conn,APPROVED[gold_et,kc],scope);return {'primary':strict_score(gold,convert(pred,d)),'secondary_exact':None,'diagnostic_exact':None}
 # Wrong entity is not primary-equivalent, even if IDs happen to coincide.
 raw=[(('__wrong_entity_or_key__',str(k)),a,t) for k,a,t in pred];out={'primary':strict_score(gold,raw),'secondary_exact':None,'diagnostic_exact':None}
 sql=SECONDARY.get((query_id,pred_et));expected=('bag_tag',) if pred_et=='Bag' else (CANONICAL.get(pred_et),)
 if sql and kc==expected:
  if query_id in ('Q09','Q12') and pred_et=='Turnaround':
   if not any(r[2]=='flights' and r[3]=='outbound_id' and r[4]=='flight_id' for r in conn.execute('PRAGMA foreign_key_list(turnarounds)')):return out
  try:d=mapping(conn,sql,scope);ok=strict_score(gold,convert(pred,d))['exact']
  except ValueError:ok=False
  field='diagnostic_exact' if (query_id=='Q12' and pred_et=='Boarding Session') or (query_id in ('Q51','Q52') and pred_et=='Passenger Leg') else 'secondary_exact';out[field]=ok
 return out
