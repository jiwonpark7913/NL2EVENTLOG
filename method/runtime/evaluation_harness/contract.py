"""Bind the candidate study to the exact public Pilot and frozen evaluator."""

from hashlib import file_digest, sha256
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
AUDIT = WORKSPACE/'NL2EVENTLOG_v2_pi_comparison/results/verification-audit-20261128'
FROZEN = Path(os.environ.get('NL2EVENTLOG_COMPANION_DIR', WORKSPACE/'NL2EVENTLOG')).resolve()
RELEASE_V4_DESCRIPTOR_SHA256 = '27a280ea46c5bc0df6850b6edd4944b3b8122f4523226bf60e6b9580ad5fa2cd'
INPUTS = AUDIT/'inputs'
VERSION = 'nl2eventlog-v2-minimal-step2-dev1'
MODEL = 'claude-haiku-5-5'
QIDS = tuple(f'Q{i:02d}' for i in range(1, 13))
PUBLIC = {'database':'variants/l20/input/database.sqlite', 'dictionary':'variants/l20/input/data_dictionary.json',
          'questions':'evaluation/model_questions.jsonl'}


def read(path):
    """PURPOSE: Decode one JSON receipt. INPUT: Local path. OUTPUT: Parsed object."""
    return json.loads(path.read_text(encoding='utf-8'))


def digest(path):
    """PURPOSE: Check byte integrity. INPUT: Local path. OUTPUT: SHA-256 hex."""
    with path.open('rb') as file:
        return file_digest(file, 'sha256').hexdigest()


def value_digest(value):
    """PURPOSE: Bind one public study descriptor. INPUT: JSON object. OUTPUT: Canonical SHA-256."""
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def write(path, value):
    """PURPOSE: Publish a complete receipt atomically. INPUT: Path and JSON object. OUTPUT: Local file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile('w', encoding='utf-8', dir=path.parent, delete=False) as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        temp = Path(stream.name)
    try:
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)


def verify_public_inputs():
    """PURPOSE: Admit exactly the audit's revalidated latest public inputs.
    INPUT: Pinned latest-data audit receipt. OUTPUT: Public paths and Pilot without reference fields.
    """
    latest = read(AUDIT/'EXPERIMENT_MANIFEST.json')['latest']
    paths = {name: INPUTS/path for name, path in PUBLIC.items()}
    hashes = {name: digest(path) for name, path in paths.items()}
    for name, key in PUBLIC.items():
        if hashes[name] != latest['admitted_file_sha256'][key]:
            raise ValueError(f'Public input changed: {name}')
    items = [json.loads(line) for line in paths['questions'].read_text().splitlines()]
    if tuple(r.get('question_id') for r in items) != QIDS or any(r.keys() != {'question_id','text'} for r in items):
        raise ValueError('Unexpected public Pilot IDs or fields')
    return paths, items, latest['commit'], hashes


def binding():
    """PURPOSE: Pin model settings and versions before transport. INPUT: Local allowlisted data and code.
    OUTPUT: Paths, fixed questions and self-identifying experiment descriptor.
    """
    paths, items, commit, inputs = verify_public_inputs()
    evaluation_path = FROZEN/'FINAL_EVALUATION_FREEZE_V4.json'
    for file, expected in read(evaluation_path)['hashes'].items():
        if digest(FROZEN/file) != expected:
            raise ValueError('Frozen Evaluation v4 changed')
    groups = {'src': '*.py', 'prompts': '*.md', 'evaluation_harness': '*.py'}
    runtime = {str(p.relative_to(ROOT)): digest(p) for group, pattern in groups.items()
               for p in sorted((ROOT/group).rglob(pattern))}
    descriptor = {'version':VERSION, 'dataset_commit':commit, 'public_sha256':inputs,
                  'model':MODEL, 'effort':'medium', 'thinking':'adaptive',
                  'retrieval':'shared_progressive_graph_no_dense_encoder','arm_names':['existing','M0','M1'],
                  'pi_limits':{'calls':32,'estimated_input_tokens':240000},'modelled_reviews':{'M0':0,'M1':1},
                  'evaluation_v4_sha256':digest(evaluation_path),'runtime_sha256':runtime,
                  'initial_legacy_disclosure':'Same initial retrieval; separate original Case and Activity interpreter',
                  'execution_disclosure':'Same compiler/physical validator; M0/M1 use deterministic-only execution'}
    return paths, items, descriptor
