"""Build fresh AirlineFlow DBs from canonical synthetic records and schema files."""
from pathlib import Path
import sqlite3,json,shutil,hashlib,sys,subprocess
ROOT=Path(__file__).resolve().parent
if len(sys.argv)!=2:raise SystemExit('Usage: python generate.py EMPTY_OUTPUT_DIRECTORY')
OUT=Path(sys.argv[1]).resolve()
if OUT.exists() and any(OUT.iterdir()):raise ValueError('Output must be empty')
shutil.copytree(ROOT,OUT,dirs_exist_ok=True,ignore=shutil.ignore_patterns('*.sqlite','__pycache__'))
records=json.loads((OUT/'source/records.json').read_text());manifest=json.loads((OUT/'evaluation/variant_manifest.json').read_text())
for v in manifest:
 p=OUT/v['database_path'];p.parent.mkdir(parents=True,exist_ok=True)
 with sqlite3.connect(p) as db:
  db.execute('PRAGMA foreign_keys=ON');db.executescript(p.with_name('schema.sql').read_text())
  for t, in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY rowid").fetchall():
   r=records[t];assert len(r['rows'])==v['table_rows'][t];db.executemany('INSERT INTO '+t+' ('+','.join(r['columns'])+') VALUES ('+','.join('?' for _ in r['columns'])+')',r['rows'])
  assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok' and not db.execute('PRAGMA foreign_key_check').fetchall()
 with sqlite3.connect(p) as db,sqlite3.connect(ROOT/v['database_path']) as original:
  for t in v['table_rows']:assert db.execute('SELECT * FROM '+t+' ORDER BY 1').fetchall()==original.execute('SELECT * FROM '+t+' ORDER BY 1').fetchall(),t
 v['database_sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
(OUT/'evaluation/variant_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');shutil.copy2(OUT/'variants/l15/input/database.sqlite',OUT/'input/database.sqlite');subprocess.run([sys.executable,str(OUT/'verify.py')],check=True)
print('PASS: regenerated all four databases from canonical records, same logical rows and Gold.')
