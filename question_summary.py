"""Refresh README query statistics from question-level annotations."""
import json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parent
NOTE='- Avg. requested activity types = sum of requested activity-type counts / all questions in that row, including non-answerable questions. Q3/Q4 counts use the Gold catalog scope. This counts distinct activity types, not event occurrences.\n'
def stats(p):
 questions=[json.loads(l) for l in (p/'input/questions.jsonl').read_text().splitlines()];out=[]
 for typ in ['Q1','Q2','Q3','Q4']:
  qs=[q for q in questions if q['question_type']==typ];answerable=sum(q['answerability']=='answerable' for q in qs);total=sum(q['requested_activity_count'] for q in qs);assert qs
  out.append((typ,len(qs),answerable,len(qs)-answerable,total/len(qs)))
 assert out[0][1:]==out[1][1:] and out[2][1:]==out[3][1:]
 return out
HEADER='| Type | Questions | Answerable | Non-answerable | Avg. requested activity types |\n|---|---:|---:|---:|---:|\n'
def refresh():
 for n in ['warehouseflow','universityflow','plateflow','hospitalflow']:
  f=ROOT/'datasets'/n/'input/questions.jsonl'
  if not f.exists() or any('question_type' not in json.loads(x) for x in f.read_text().splitlines()):return []
 allrows=[]
 for name,title in [('warehouseflow','WarehouseFlow'),('universityflow','UniversityFlow'),('plateflow','PlateFlow'),('hospitalflow','HospitalFlow')]:
  p=ROOT/'datasets'/name;rows=stats(p);table=HEADER+''.join(f'| {t} | {n} | {a} | {x} | {avg:.2f} |\n' for t,n,a,x,avg in rows);readme=p/'README.md';s=readme.read_text();start=s.index('## Question types and pairs');head=s[:start];tail=s[start:]
  tail=re.sub(r'\| Type \| Questions \|.*?(?=\n\n)',table.rstrip(),tail,count=1,flags=re.S);tail=re.sub(r'\n- Avg\. requested activity types =[^\n]*\n','\n',tail);tail=tail.replace(table.rstrip(),table.rstrip()+'\n\n'+NOTE.rstrip(),1);readme.write_text(re.sub(r"\n{3,}","\n\n",head+tail))
  allrows.extend((title,*r) for r in rows)
 p=ROOT/'README.md';s=p.read_text();s=s.replace('## Question counts by type','### Question statistics by dataset and type');table='| Dataset | Type | Questions | Answerable | Non-answerable | Avg. requested activity types |\n|---|---|---:|---:|---:|---:|\n'+''.join(f'| {name} | {t} | {n} | {a} | {x} | {avg:.2f} |\n' for name,t,n,a,x,avg in allrows)
 start=s.index('## Question types and pairs');head=s[:start];tail=s[start:];tail=re.sub(r'\| Dataset \|.*?(?=\n\n)',table.rstrip(),tail,count=1,flags=re.S);tail=re.sub(r'\n- Avg\. requested activity types =[^\n]*\n','\n',tail);tail=tail.replace(table.rstrip(),table.rstrip()+'\n\n'+NOTE.rstrip(),1);p.write_text(re.sub(r"\n{3,}","\n\n",head+tail))
 return allrows
if __name__=='__main__':
 for row in refresh():print(row)
