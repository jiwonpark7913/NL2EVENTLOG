"""Format explanatory Markdown as short bullets while keeping tables and code intact."""
import re
from pathlib import Path

def bullet_prose(text):
 lines=text.splitlines();out=[];paragraph=[];fenced=False
 def flush():
  if paragraph:
   prose=' '.join(x.strip() for x in paragraph)
   for sentence in re.split(r'(?<=[.!?])\s+(?=[A-Z])',prose):out.append('- '+sentence)
   paragraph.clear()
 for line in lines:
  if line.startswith('```'):
   flush();fenced=not fenced;out.append(line)
  elif fenced or line.startswith(('    ','\t')):
   flush();out.append(line)
  elif not line.strip() or line.startswith(('#','|','- ','* ','![','> ')) or re.match(r'^\d+\. ',line):
   flush();out.append(line)
  else:paragraph.append(line)
 flush();return '\n'.join(out)+'\n'

def format_documents(root):
 for p in Path(root).rglob('*.md'):
  if '.git' not in p.parts:p.write_text(bullet_prose(p.read_text(encoding='utf-8')),encoding='utf-8')
if __name__=='__main__':format_documents(Path(__file__).resolve().parent)
