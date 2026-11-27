"""Reproduce the released AirlineFlow fixture without rewriting reference answers."""
from pathlib import Path
from collections import Counter
import argparse,csv,hashlib,json,shutil,sqlite3,subprocess,sys,tempfile
ROOT=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def gold(q):
    with (ROOT/'gold'/q/'events.csv').open(encoding='utf-8-sig',newline='') as f:
        return Counter((r['case_id'],r['activity'],r['timestamp']) for r in csv.DictReader(f))
def build_database(p,ddl,records,v):
    p.parent.mkdir(parents=True,exist_ok=True)
    with sqlite3.connect(p) as db:
        db.execute('PRAGMA foreign_keys=ON');db.executescript(ddl.read_text())
        for t, in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY rowid").fetchall():
            r=records[t];assert len(r['rows'])==v['table_rows'][t]
            db.executemany('INSERT INTO '+t+' ('+','.join(r['columns'])+') VALUES ('+','.join('?' for _ in r['columns'])+')',r['rows'])
        assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok' and not db.execute('PRAGMA foreign_key_check').fetchall()
def reproduce(out,seed_check=False):
    records=read(ROOT/'source/records.json');manifest=read(ROOT/'evaluation/variant_manifest.json')
    if seed_check:
        generated=out/'seed'
        subprocess.run(['node',str(ROOT/'source/generate_records_v2.mjs'),str(generated)],check=True,stdout=subprocess.DEVNULL)
        assert read(generated/'records.json')==records,'Fixed-seed source records differ from published records'
    conditions=0
    for v in manifest:
        path=Path(v['database_path']);p=out/path;original=ROOT/path
        build_database(p,original.with_name('schema.sql'),records,v)
        dd=read(ROOT/v['dictionary_path']);standard=read(original.with_name('data_dictionary_standard.json'))
        with sqlite3.connect(p) as db,sqlite3.connect(original.resolve().as_uri()+'?mode=ro',uri=True) as src:
            for t in v['table_rows']:
                cols=[x[1] for x in db.execute('PRAGMA table_info('+t+')')]
                assert cols==records[t]['columns']==list(dd[t]['columns'])==list(standard[t]['columns']),(v['variant_id'],t,'column mismatch')
                assert db.execute('SELECT * FROM '+t+' ORDER BY 1').fetchall()==src.execute('SELECT * FROM '+t+' ORDER BY 1').fetchall(),(v['variant_id'],t)
            for q in v['question_ids']:
                assert Counter(db.execute((ROOT/'gold'/q/'gold.sql').read_text()).fetchall())==gold(q),(v['variant_id'],q)
                conditions+=1
        v['database_sha256']=sha(p)
    assert conditions==108
    print('PASS: four independently rebuilt databases, all shared data and dictionary columns, 108 Gold SQL comparisons.'+(' Fixed-seed source generation also matches.' if seed_check else ''))
    return manifest
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('output',nargs='?');ap.add_argument('--check',action='store_true');args=ap.parse_args()
    if args.check:
        if args.output:ap.error('--check does not accept an output directory')
        with tempfile.TemporaryDirectory() as t:reproduce(Path(t),seed_check=True)
        return
    if not args.output:ap.error('specify an empty output directory or --check')
    out=Path(args.output).resolve()
    if out==ROOT or ROOT in out.parents:ap.error('output must be outside the source directory')
    if out.exists() and any(out.iterdir()):ap.error('output must be empty')
    shutil.copytree(ROOT,out,dirs_exist_ok=True,ignore=shutil.ignore_patterns('*.sqlite','__pycache__'))
    manifest=reproduce(out)
    (out/'evaluation/variant_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    shutil.copy2(out/'variants/l15/input/database.sqlite',out/'input/database.sqlite')
    subprocess.run([sys.executable,str(out/'verify.py')],check=True)
if __name__=='__main__':main()
