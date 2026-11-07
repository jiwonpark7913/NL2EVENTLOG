"""Offline tests only: fixtures never claim real GPT-generated outputs."""
import contextlib
import copy
import hashlib
import io
import os
from pathlib import Path
import shutil
import sys
import subprocess
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'/'questions'))
import paraphrase_questions as m


class FakeAPI:
    calls = 0

    def __init__(self, model, *args):
        self.model = model

    def json_call(self, system, payload):
        FakeAPI.calls += 1
        allowed = {'source_id','source_type','target_type','question'}
        if system==m.SYSTEM:
            assert set(payload)==allowed
            answer = dict(source_id=payload['source_id'],target_type=payload['target_type'],paraphrase='Please provide the following: '+payload['question'])
        else:
            assert set(payload)==allowed|{'paraphrase'}
            answer = dict(equivalent=True,implicit_scope_preserved=True,reason='Offline test fixture')
        return answer,dict(model=self.model,usage={'total_tokens':0},test_fixture=True)


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.item = dict(source_id='X1',source_type='Q3',target_id='X1P',target_type='Q4',question='Extract the full recorded lifecycle event log for each student.')
        self.item['source_hash'] = m.fingerprint(self.item)

    def test_semantic_failure_never_published(self):
        class Reject(FakeAPI):
            def json_call(self, system, payload):
                result,raw = super().json_call(system,payload)
                if system==m.VERIFY_SYSTEM:
                    result['equivalent'] = False
                return result,raw
        with self.assertRaises(ValueError):
            m.generate_one(Reject('offline-fixture'),self.item,attempts=2)

    def test_wrong_mapping_rejected(self):
        class Wrong(FakeAPI):
            def json_call(self, system, payload):
                result,raw = super().json_call(system,payload)
                if system==m.SYSTEM:
                    result['source_id'] = 'OTHER'
                return result,raw
        with self.assertRaises(ValueError):
            m.generate_one(Wrong('offline-fixture'),self.item,attempts=1)

    def test_stale_cache_rejected(self):
        record = m.generate_one(FakeAPI('offline-fixture'),self.item)
        changed = dict(self.item,question='Extract only completed admissions.')
        changed['source_hash'] = m.fingerprint(changed)
        with self.assertRaises(ValueError):
            m.validate_record(changed,record)

    def test_all_six_datasets_prepare_resume_and_restore_pairs(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            shutil.copytree(m.ROOT/'datasets',root/'datasets')
            shutil.copy(m.ROOT/'README.md',root/'README.md')
            for file in m.ROOT.glob('*.py'):
                shutil.copy(file,root/file.name)
            baseline = {str(f.relative_to(root)):hashlib.sha256(f.read_bytes()).hexdigest() for f in root.glob('datasets/*/private/gold_logs/*.csv')}
            original_sources = {}
            for name in m.DATASETS:
                for q in m.readjl(m.question_file(root/'datasets'/name)):
                    if q['question_type'] in m.TARGET:
                        original_sources[name,m.qid(q)] = m.text(q)
            output = io.StringIO()
            with patch.object(m,'ROOT',root),patch.object(m,'API',FakeAPI),patch.dict(os.environ,{'OPENAI_API_KEY':'offline-placeholder'}),contextlib.redirect_stdout(output):
                def run(args):
                    with patch.object(sys,'argv',['paraphrase_questions.py',*args]):
                        m.main()
                run(['prepare'])
                seeds = sum(len(m.readjl(m.question_file(root/'datasets'/name))) for name in m.DATASETS)
                self.assertEqual(seeds,150)
                for path,prior in baseline.items():
                    f = root/path
                    if f.exists():
                        self.assertEqual(hashlib.sha256(f.read_bytes()).hexdigest(),prior)
                run(['prepare'])  # idempotent IDs and sources
                run(['generate','--model','offline-fixture','--limit','2'])
                self.assertEqual(sum(len(m.readjl(m.question_file(root/'datasets'/name))) for name in m.DATASETS),150)
                FakeAPI.calls = 0
                run(['generate','--model','offline-fixture'])
                self.assertEqual(FakeAPI.calls,296)  # two cached pairs, 148 x (generate + verify)
                self.assertEqual(sum(len(m.readjl(m.question_file(root/'datasets'/name))) for name in m.DATASETS),300)
                for name in m.DATASETS:
                    for q in m.readjl(m.question_file(root/'datasets'/name)):
                        if q['question_type'] in m.TARGET:
                            self.assertEqual(m.text(q),original_sources[name,m.qid(q)])
                for path,prior in baseline.items():
                    self.assertEqual(hashlib.sha256((root/path).read_bytes()).hexdigest(),prior)
                subprocess.run([sys.executable,str(root/'validate_lifecycles.py')],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                FakeAPI.calls = 0
                run(['generate','--model','offline-fixture'])
                self.assertEqual(FakeAPI.calls,0)
                run(['validate'])


if __name__=='__main__':
    unittest.main()
