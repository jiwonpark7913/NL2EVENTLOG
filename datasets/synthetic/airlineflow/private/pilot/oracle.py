"""Independent row-oriented Gold oracle from v6; no SQL/ESpec rule generator consumed."""
def rows(c,t):
    return [dict(r) for r in c.execute('SELECT * FROM '+t)]

def oracle(c):
    t=rows(c,'turnarounds'); b=rows(c,'boarding_sessions'); j=rows(c,'handling_jobs'); m=rows(c,'movement_reports')
    turn={r['turn_id']:r for r in t}; out={r['outbound_id']:r['turn_id'] for r in t}; inc={r['inbound_id']:r['turn_id'] for r in t}
    g={f'Q{i:02d}':[] for i in range(1,13)}
    def add(q,c,a,ts): g[q].append((c,a,ts))
    for r in b:
        for a,ts in [('Boarding Start',r['started_at']),('Boarding Close',r['closed_at'])]:
            for q in ['Q01','Q11']: add(q,r['session_id'],a,ts)
            if r['flight_id'] in out:
                for q in ['Q03','Q06','Q10','Q12']: add(q,r['flight_id'],a,ts)
                add('Q04',out[r['flight_id']],a,ts)
    job_names={'DP':'Disembarkation Complete','UL':'Baggage Unloading Complete','CL':'Cabin Cleaning Complete','FU':'Refuelling Complete','CA':'Catering Loading Complete','BL':'Baggage Loading Close'}
    for r in j:
        add('Q02',r['job_id'],'Job Start',r['started_at']);add('Q02',r['job_id'],'Job Complete',r['finished_at'])
        code=r['job_code'];u=r['turn_id'];flight=turn[u]['outbound_id'];ts=r['finished_at']
        if code in job_names:add('Q04',u,job_names[code],ts)
        if code in {'CL','FU'}:add('Q05',u,job_names[code],ts)
        if code in {'UL','CL','FU','CA','BL'}:add('Q07',flight,job_names[code],ts)
        if code=='BL':add('Q03',flight,job_names[code],ts)
    for r in t:
        for q in ['Q04','Q05']:
            add(q,r['turn_id'],'Handling Start',r['handling_started_at']);add(q,r['turn_id'],'Aircraft Ready',r['ready_at'])
        add('Q03',r['outbound_id'],'Aircraft Ready',r['ready_at'])
    for r in m:
        k=r['kind'];f=r['flight_id'];ts=r['value_at']
        if k in {'LAND','IN'} and f in inc:
            for q in ['Q04','Q08']:add(q,inc[f],{'LAND':'Landing','IN':'In-block'}[k],ts)
        if k in {'OUT','AIR'}:
            a={'OUT':'Off-block','AIR':'Take-off'}[k]
            if f in out:
                for q in ['Q09','Q12']:add(q,f,a,ts)
                for q in ['Q04','Q08']:add(q,out[f],a,ts)
                for q in ['Q06']+(['Q03','Q10'] if k=='OUT' else []):add(q,f,a,ts)
    return g
