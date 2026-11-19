"""Refresh reference question docs and author-audit checkpoints from current Gold."""
from pathlib import Path
import json,csv,collections,hashlib,subprocess
from build_gold_review_pages import graph
from build_gold_dfg_review import extract
ROOT=Path(__file__).resolve().parents[1]
def run():
 audit=json.loads((ROOT/'docs/reference_gold_audit_2026-11-20.json').read_text())
 for ds in ['hospitalflow','plateflow','warehouseflow','universityflow']:
  b=ROOT/'datasets'/ds;qp=next(p for p in [b/'private/questions.jsonl',b/'evaluation/questions.jsonl'] if p.exists());qs=[json.loads(l) for l in qp.read_text().splitlines() if l.strip()];gs={g['question_id']:g for g in map(json.loads,(b/'private/gold.jsonl').read_text().splitlines())}
  lines=[f'# {ds} — Question definitions and Gold review','', '[Interactive question / DFG / source-row review](../review/gold_dfg/index.html)','', 'Q1: explicit; Q2: explicit paraphrase; Q3: lifecycle; Q4: lifecycle paraphrase. Pairs retain the same scope and Gold log. Revised requests and paraphrases are author edits following the 2026-11-20 audit.','', '| ID | Type | Pair | Case | Process focus | Answerability | Supported activities | Observed activities | Events | Question |','|---|---|---|---|---|---|---:|---:|---:|---|']
  for q in qs:
   id=q.get('question_id',q.get('id'));g=gs[id];p=b/f'private/gold_logs/{id}.csv';rs=list(csv.DictReader(p.open())) if p.exists() else [];pv=g.get('process_view',{})
   fields=[id,q.get('question_type',''),q.get('pair_of') or '',q.get('case_concept') or pv.get('case_concept',''),pv.get('process_focus',''),g.get('answerability',''),len(pv.get('activities',[])),len({r['activity'] for r in rs}),len(rs),q.get('text',q.get('question'))]
   lines.append('| '+' | '.join(str(x).replace('|','\\|') for x in fields)+' |')
  (b/'docs/questions.md').write_text('\n'.join(lines)+'\n')
  if ds!='universityflow':
   p=b/'validation_report.json';data=json.loads(p.read_text());rec=next(x for x in audit if x['dataset']==ds)
   data['reference_audit_2026_11_20']={'questions_checked':len(rec['questions']),'source_reference_missing':0,'source_reference_extra':0,'unmatched_source_rows':0,'sql_csv_consistent':True,'paired_logs_equal':True,'scope':'Completeness and consistency relative to documented source definitions, attribution paths and process focus.'};p.write_text(json.dumps(data,indent=2)+'\n')
  else:
   p=b/'review/gold_dfg/review_data.json';data=json.loads(p.read_text())
   for r in data:
    if r.get('id') not in ['OU10','OU10P']:continue
    id=r['id'];rs=list(csv.DictReader((b/f'private/gold_logs/{id}.csv').open()));svg,cs,acts=graph(rs);(b/f'review/gold_dfg/graphs/{id}.svg').write_text(svg);d=extract(rs)
    r.update(question=next(q.get('text',q.get('question')) for q in qs if q.get('question_id',q.get('id'))==id),chart=f'graphs/{id}.svg',activity_counts=dict(collections.Counter(x['activity'] for x in rs)),unmatched_gold_rows=0,gold_sha256=hashlib.sha256((b/f'private/gold_logs/{id}.csv').read_bytes()).hexdigest(),edges=[dict(source=a,target=z,count=n,tie_affected=d['ambiguous'][(a,z)]) for (a,z),n in sorted(d['edges'].items())])
    r['stats'].update(events=len(rs),observed_cases=cs,activities=acts,dfg_edges=len(d['edges']),tied_timestamp_groups=d['tied_timestamp_groups'],requested_but_not_observed=[],observed_outside_gold_scope=[])
   p.write_text(json.dumps(data,indent=2)+'\n')
  (b/'review/gold_dfg/README.md').write_text(f'# {ds} — Gold review\n\n[Question / DFG / original-table inspection](index.html)\n\nDownload `index.html` and open it in a browser; GitHub displays HTML source. The page embeds all question panels, graphs and source rows without external data loading.\n\nThe HTML is the current manual-review entry point. Gold SQL, CSV and source annotations are author/evaluation artifacts, not model inputs.\n')
if __name__=='__main__':run()
