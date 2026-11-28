"""Legacy-package worker for public Compact EEG serialization and offline v4 log scoring."""

from contextlib import closing
from pathlib import Path
from statistics import mean
import json
import sys

from evaluation import final_runner as v4
from evaluation.compact_eeg import compact_eeg
from evaluation.extraction_scoring import grade_extraction
from evaluation.scoring_v3 import aggregate
from src.common.database_io import connect_readonly


def score_saved(database, references, predictions):
    """PURPOSE: Score paired saved logs through the unchanged v4 witnesses and semantic scorer.
    INPUT: Standalone DB, private registered reference file, public-run manifest and raw receipts.
    OUTPUT: Per-query log scores and common v4 aggregates. No inference is performed.
    """
    freeze = v4.verify_evaluation()
    run = v4.read_json(predictions/'run.json')
    manifest = v4.read_json(references)
    binding = run['binding']
    items = {item['qid']: item for item in manifest['queries']}
    if (v4.file_digest(database) != binding['database_sha256'] or manifest['database_sha256'] != binding['database_sha256']
            or v4.json_digest(binding) != run['binding_sha256']
            or binding['evaluation_v4_sha256'] != v4.file_digest(v4.EVALUATION_FREEZE)
            or len(items) != len(manifest['queries']) or set(items) != set(binding['qids'])):
        raise ValueError('Reference and prediction bindings differ')
    if run['eeg'] and v4.json_digest(v4.read_json(predictions/'eeg.json')) != run['eeg']['eeg_sha256']:
        raise ValueError('Saved EEG differs from the inference binding')
    if run['m1_eeg_sha256']:
        compact = v4.read_json(predictions/'m1-eeg.json')
        if (compact['eeg_sha256'] != run['eeg']['eeg_sha256']
                or v4.json_digest(compact['payload']) != run['m1_eeg_sha256']):
            raise ValueError('Saved Compact EEG differs from the inference binding')
    scores = {}
    with closing(connect_readonly(database)) as connection:
        for qid in binding['qids']:
            if not qid.isascii() or not qid.isalnum():
                raise ValueError('Invalid registered question ID')
            ref = items[qid]
            evaluator, effective, gold = v4.open_reference(ref, connection, references.parent, manifest['timezone'])
            gold_status = 'accepted' if effective.get('answerable', True) else 'unsupported'
            check = v4.grade({'status': gold_status, 'case': {'table': effective['case_table']},
                              'sql': effective.get('sql'), 'rows': gold}, evaluator, effective, gold)
            if (gold_status == 'accepted' and not all(check[key]['exact_match'] for key in v4.DIMENSIONS)
                    or gold_status == 'unsupported' and check.get('abstention') != 'correct_abstention'):
                raise ValueError('Registered reference failed self-check')
            file = predictions/(qid+'.json')
            receipts = v4.read_json(file) if file.exists() else {}
            if file.exists():
                condition = receipts.get('_condition', {})
                expected = {'qid': qid, 'binding_sha256': run['binding_sha256'],
                            'question_sha256': binding['question_sha256'][qid]}
                if any(condition.get(key) != value for key, value in expected.items()):
                    raise ValueError('Prediction condition does not match the public plan')
            scores[qid] = {}
            for arm in binding['arms']:
                record = receipts.get(arm, {'status': 'not_run'})
                if arm == 'M3' and record['status'] != 'not_run' and any(
                        record.get('release', {}).get(key) != value for key, value in binding['method'].items()):
                    raise ValueError('M3 receipt has a different runtime identity')
                if record.get('eeg_sha256') is not None and record['eeg_sha256'] != run['eeg']['eeg_sha256']:
                    raise ValueError('Receipt has a different EEG')
                if arm == 'M1' and record['status'] != 'not_run' and record['m1_eeg_sha256'] != run['m1_eeg_sha256']:
                    raise ValueError('M1 receipt used a different Compact EEG')
                scores[qid][arm] = grade_extraction(record, evaluator, effective, gold)
    summary = {}
    for arm in binding['arms']:
        grades = [item[arm] for item in scores.values()]
        summary[arm] = {}
        for axis in ('extraction', 'semantic'):
            combined = aggregate(grades, axis)
            for measure in ('precision', 'recall'):
                available = [item[axis][measure] for item in grades if axis in item]
                combined['macro_' + measure] = mean(available) if available else None
            summary[arm][axis] = combined
    return {'evaluation': freeze['version'], 'prediction_binding_sha256': run['binding_sha256'],
            'references_sha256': v4.file_digest(references), 'scores': scores, 'summary': summary,
            'component_status': 'final_reference_policy_pending'}


def main():
    """PURPOSE: Dispatch one isolated companion operation. INPUT: Mode and explicit local files.
    OUTPUT: JSON on stdout for the release runner.
    """
    if sys.argv[1:] == ['compact']:
        v4.verify_evaluation()
        output = compact_eeg(json.load(sys.stdin))
    elif len(sys.argv) == 5 and sys.argv[1] == 'score-v4':
        output = score_saved(*map(Path, sys.argv[2:]))
    else:
        raise ValueError('Expected compact or score-v4 with three explicit paths')
    print(json.dumps(output, ensure_ascii=False))


if __name__ == '__main__':
    main()
