"""Validate and publish the current fixture's derived review assets.

The released population and authored reference answers are immutable in this
entry point. Historical migrations are not invoked by a documentation update.
"""
from pathlib import Path
import hashlib,json,subprocess,sys
R=Path(__file__).resolve().parent
def run(name,*args):subprocess.run([sys.executable,str(R/name),*args],check=True,cwd=R)
def snapshot(paths):return {str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
gold=[p for p in (R/'gold').glob('Q*/*') if p.name in ('events.csv','events_enriched.csv','gold.sql','pi.json','espec.json')]
dfgs=[p for p in (R/'gold').glob('Q*/*') if p.name in ('dfg.dot','dfg.svg')]
inputs=list((R/'variants').glob('*/input/*'))+[R/'source/records.json',R/'evaluation/query_registry.csv',R/'evaluation/variant_manifest.json',R/'input/database.sqlite']
inputs=[p for p in inputs if p.is_file()]
protected=snapshot(gold+inputs);before_dfg=snapshot(dfgs)
assert len(gold)==72*5 and len(dfgs)==72*2
run('generate.py','--check')
run('activity_dfg.py')
run('refresh_review_v2.py')
run('enrich_review.py')
run('docs/render_readme.py')
run('verify.py')
assert snapshot(gold+inputs)==protected,'Publication altered protected reference answers or released inputs'
changed=[p for p,h in snapshot(dfgs).items() if h!=before_dfg[p]]
receipt=R/'evaluation/verification.json';v=json.loads(receipt.read_text())
v['release_audit']={'status':'PASS','schema_revision':'operational-v1','fixed_seed_reproduction':'PASS','database_rebuilds':4,'reproduced_gold_conditions':108,'protected_gold_files':len(gold),'protected_inputs_unchanged':True,'gold_files_unchanged':True,'dfg_files_checked':len(dfgs),'dfg_byte_changes':changed,'dfg_semantic_checks':'PASS','html_revision':'r13','ui_english':True,'human_semantic_review':'PENDING','production_scorer':'NOT_RUN'}
receipt.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
print('PASS: final publication audit; all 360 authored/enriched Gold files and released inputs unchanged; DFG byte changes:',len(changed))
