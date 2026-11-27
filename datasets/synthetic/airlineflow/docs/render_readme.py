"""Regenerate full documentation from verified fixture metadata (no DB/Gold writes)."""
from pathlib import Path
import json,re
R=Path(__file__).resolve().parents[1]
def rd(p):return json.loads((R/p).read_text(encoding='utf-8-sig'))
def wr(p,s):(R/p).write_text(s,encoding='utf-8')
def fmt(n):return f'{n:,}'
def esc(s):return s.replace('|',r'\|')
def render(t,v):return re.sub(r'@([A-Z0-9_]+)@',lambda x:str(v[x.group(1)]),t)
m=rd('evaluation/variant_manifest.json');s=rd('docs/dataset_statistics.json');r=rd('evaluation/verification.json');g=r['generator_summary'];p=rd('gold/Q04/pi.json')
domains=['Core aircraft turnaround','Passenger and booking','Baggage and security','Operating resources']
vt=(R/'docs/variant_readme_template.md').read_text()
rows=[];prior=set()
for i,v in enumerate(m):
    l=v['variant_id'];L=l.upper();dd=rd(v['dictionary_path']);cols=sum(len(x['columns']) for x in dd.values())
    assert cols==s['variants'][l]['columns'] and set(dd)==set(v['table_rows'])
    assert (R/f'variants/{l}/docs/schema.svg').is_file()
    rows.append(f"| [{L}](variants/{l}/README.md) | {v['table_count']} | {cols} | {fmt(v['row_count'])} | {domains[i]} | [SQLite]({v['database_path']}) · [ERD](variants/{l}/docs/schema.svg) · [DD (JSON)]({v['dictionary_path']}) · [DD (readable)](variants/{l}/docs/data_dictionary.md) · [EEG example](docs/eeg_examples.md#{l}) |")
    intro='\n'.join(f"| {chr(96)}{t}{chr(96)} | {fmt(n)} | {esc(dd[t]['description'])} |" for t,n in v['table_rows'].items() if t not in prior)
    base='Base schema.' if i==0 else f"Extends {m[i-1]['variant_id'].upper()} by five tables; shared records are unchanged."
    wr(f'variants/{l}/README.md',render(vt,dict(LEVEL=L,DOMAIN=domains[i],TABLES=v['table_count'],COLUMNS=cols,COUNT=fmt(v['row_count']),EXTENDS=base,LOWER=l,INTRO=intro,SCOPE=len(v['question_ids']),VERSION=r['version'])))
    out=f"# {L} — data dictionary\n\n[Back to variant](../README.md) · [Original JSON](../input/data_dictionary.json)\n\n{v['table_count']} tables · {cols} columns · {fmt(v['row_count'])} rows\n\n"
    for t in sorted(dd):
        x=dd[t];out+=f"## {chr(96)}{t}{chr(96)}\n\n{x['description']} ({fmt(v['table_rows'][t])} rows)\n\n| Column | Declaration | Description |\n|---|---|---|\n"
        out+='\n'.join(f"| {chr(96)}{c}{chr(96)} | {chr(96)}{z['declaration']}{chr(96)} | {esc(z['description'])} |" for c,z in x['columns'].items())+'\n\n'
    wr(f'variants/{l}/docs/data_dictionary.md',out);prior=set(v['table_rows'])
vr='\n'.join(rows)
wr('variants/README.md','# Database variants\n\n[Dataset home](../README.md)\n\n| Variant | Tables | Columns | Rows | Domain | Files |\n|---|---:|---:|---:|---|---|\n'+vr.replace('variants/','').replace('(docs/eeg_examples.md','(../docs/eeg_examples.md')+'\n')
acts={a for i in range(1,73) for a in rd(f'gold/Q{i:02d}/pi.json')['activities']}
v=dict(REQUESTS=s['requests'],CONDITIONS=s['conditions'],ACTIVITIES=len(acts),VERSION=r['version'],TURNS=fmt(g['counts']['turnarounds']),FLIGHTS=fmt(g['counts']['flights']),LEGS=fmt(g['counts']['passenger_legs']),ROWS=vr,TEST=s['test'],DISTINCT=s['distinct_test_gold'],FAMILIES=s['test_family_count'],Q04_CASES=fmt(p['expected_case_count']),Q04_ACTS=len(p['activities']),Q04_EVENTS=fmt(p['expected_event_count']),SQL=r['sqlite_conditions_passed'],SEMANTIC=r['independent_occurrence_comparisons'])
wr('README.md',render((R/'docs/readme_template.md').read_text(),v))
a='# AirlineFlow — dataset analysis\n\n[Dataset home](../README.md) · [Statistics JSON](dataset_statistics.json) · [Realized generator distributions](../source/stochastic_v2_generator_preview.json)\n\n![Test request distributions](dataset_statistics.svg)\n\n## Schema size\n\n| Variant | Tables | Columns | Rows |\n|---|---:|---:|---:|\n'+'\n'.join(f"| {v['variant_id'].upper()} | {v['table_count']} | {s['variants'][v['variant_id']]['columns']} | {fmt(v['row_count'])} |" for v in m)
a+='\n\n## Population and behavior\n\n| Table | Rows |\n|---|---:|\n'+'\n'.join(f"| {k} | {fmt(n)} |" for k,n in g['counts'].items())
a+='\n\n## Passenger states\n\n| State | Passenger legs |\n|---|---:|\n'+'\n'.join(f"| {k} | {fmt(n)} |" for k,n in g['passenger_state_histogram'].items())
a+=f"\n\n{s['requests']} requests; {s['conditions']} evaluation conditions; {s['test']} test requests / {s['distinct_test_gold']} distinct Gold logs / {s['test_family_count']} families; {fmt(s['reference_event_rows'])} reference rows across all queries (not unique physical events).\n\nSource-diversity event counts are not forced equal. Fixed six jobs and one boarding session per flight preserve the ground-service experiment structure. Human approval and production scorer integration remain pending.\n"
wr('docs/dataset_analysis.md',a)
print('PASS: full README, variant ERDs and data dictionary documentation regenerated')
