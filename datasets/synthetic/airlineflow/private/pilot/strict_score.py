"""Primary exact canonical event multiset + Policy C; evaluator only."""
from collections import Counter
from datetime import datetime

def score(gold,pred):
    # The caller must first apply the evaluator-approved one-to-one activity label mapping.
    def normalize(rs):
        result=[]
        for c,a,t in rs:
            if not all(isinstance(x,str) for x in (c,a,t)):
                raise ValueError('case ID, activity, timestamp must be strings')
            result.append((c,a,datetime.fromisoformat(t)))
        return Counter(result)
    g,p=normalize(gold),normalize(pred)
    tp=sum((g&p).values()); gn,pn=sum(g.values()),sum(p.values())
    precision=tp/pn if pn else 0; recall=tp/gn if gn else 0
    return {'exact':g==p,'tp':tp,'fp':pn-tp,'fn':gn-tp,'precision':precision,'recall':recall,
            'f1':2*precision*recall/(precision+recall) if precision+recall else 0}

def score_policy_c(query_id,gold,pred,connection):
    gold,pred=list(gold),list(pred)
    primary=score(gold,pred)
    result={'primary':primary,'turnaround_equivalent':None,
            'boarding_session_equivalent_diagnostic':None,'turnaround_mapping_eligible':None}
    if query_id not in {'Q09','Q12'}:
        return result
    pairs=[tuple(r) for r in connection.execute('SELECT turn_id,outbound_id FROM turnarounds')]
    target={f for _,f in pairs}; gold_ids={c for c,_,_ in gold}
    declared_fk=any(r[2]=='flights' and r[3]=='outbound_id' and r[4]=='flight_id'
                    for r in connection.execute('PRAGMA foreign_key_list(turnarounds)'))
    eligible=declared_fk and bool(pairs) and all(t is not None and f is not None for t,f in pairs) and len(pairs)==len({t for t,_ in pairs})==len(target) and target==gold_ids
    result['turnaround_mapping_eligible']=eligible
    def equivalent(mapping):
        if primary['exact'] or not pred or not all(c in mapping for c,_,_ in pred):
            return False
        return score(gold,[(mapping[c],a,t) for c,a,t in pred])['exact']
    result['turnaround_equivalent']=equivalent(dict(pairs)) if eligible else False
    if query_id=='Q12':
        sessions=[tuple(r) for r in connection.execute('SELECT session_id,flight_id FROM boarding_sessions') if r[1] in target]
        valid=bool(sessions) and len(sessions)==len({s for s,_ in sessions})==len({f for _,f in sessions}) and {f for _,f in sessions}==gold_ids
        result['boarding_session_equivalent_diagnostic']=equivalent(dict(sessions)) if valid else False
    return result
