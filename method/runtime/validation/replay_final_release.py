"""Prove the official paths preserve the native development outputs without model traffic."""

import argparse
from collections import Counter
from contextlib import ExitStack
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from development.s2.runtime import run as development
from evaluation_harness.contract import ROOT, digest, read
from evaluation_harness.final_runner import MODEL_SETTINGS, run_condition
from src.release_runtime import prepare_eeg, release_identity, release_public_path, run_release


class SavedRoleResponses:
    """Return locally saved structured replies only after checking the exact wire."""

    def __init__(self, calls):
        """PURPOSE: Bind a fixture to a fixed role sequence. INPUT: Saved calls. OUTPUT: SDK-style double."""
        self.saved = iter(calls)
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **options):
        """PURPOSE: Reject a different prompt, schema or call. INPUT: Current wire. OUTPUT: Original response."""
        call = next(self.saved)
        schema = options['response_format']['json_schema']
        messages = options['messages']
        wire = call['prompt']
        if (schema['name'] != call['role'] or schema['schema'] != wire['schema']
                or messages[0]['content'] != wire['system'] or messages[-1]['content'] != wire['user']):
            raise AssertionError('Recorded role wire changed: ' + call['role'])
        message = SimpleNamespace(content=call['raw_response'], refusal=None)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)], usage=None)


def checked_file(workspace, relative, expected):
    """PURPOSE: Verify a named replay file. INPUT: Evidence workspace, relative path and SHA-256.
    OUTPUT: Public path with the expected bytes.
    """
    path = release_public_path(workspace/relative)
    if not path.is_relative_to(workspace) or digest(path) != expected:
        raise ValueError(f'Replay input differs from the release manifest: {relative}')
    return path


def normalized(payload):
    """PURPOSE: Compare scientific receipts independently of machine timing.
    INPUT: Nested receipt object. OUTPUT: Same fields except recorded execution timings.
    """
    if isinstance(payload, dict):
        return {key: normalized(value) for key, value in payload.items()
                if key not in ('elapsed_seconds', 'execution_seconds', 'seconds', 'wall_seconds')}
    if isinstance(payload, list):
        return [normalized(value) for value in payload]
    return payload


def main():
    """PURPOSE: Replay all 36 measured S0 development conditions on both release paths.
    INPUT: Native S0 replies and the original admitted development snapshots.
    OUTPUT: JSON equivalence receipt on stdout. No provider client is initialized.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence-workspace', type=Path, default=ROOT.parent,
                        help='Workspace containing the exact original read-only replay snapshots and saved responses')
    args = parser.parse_args()
    workspace = args.evidence_workspace.resolve()
    inputs = read(ROOT/'verification/REPLAY_INPUTS.json')
    checked_file(workspace, inputs['source_experiment_plan'], inputs['source_experiment_plan_sha256'])
    method = release_identity()
    counts, roles = Counter(), Counter()
    conditions = []
    with ExitStack() as stack:
        for function in ('src.pipeline.run_pipeline',
                         'src.step2_retrieve_and_interpret.pipeline.interpret_process_request',
                         'src.step2_retrieve_and_interpret.recover_source_knowledge.recover_source_graph',
                         'src.step3_execute.pipeline.run_repair_pipeline'):
            stack.enter_context(patch(function, side_effect=AssertionError('legacy workflow was called')))
        for cohort, panel in inputs['panels'].items():
            db = checked_file(workspace, panel['database'], panel['database_sha256'])
            dictionary = checked_file(workspace, panel['dictionary'], panel['dictionary_sha256'])
            index_manifest = checked_file(workspace, panel['eeg_directory']+'/snapshot.json', panel['snapshot_sha256'])
            eeg = prepare_eeg(db, dictionary, snapshot=index_manifest.parent)
            assert (eeg.identity['eeg_sha256'], eeg.identity['index_sha256']) == (
                panel['eeg_sha256'], panel['index_sha256'])
            for item in panel['conditions']:
                location = checked_file(workspace, item['receipt'], item['receipt_sha256'])
                obs = read(location)
                assert obs['binding_sha256'] == inputs['binding_sha256'] and obs['qid'] == item['qid']
                calls = obs['calls']
                request_path = checked_file(workspace, item['request'], item['request_sha256'])
                request = read(request_path)['text']
                model = obs['model']
                dev = development(db, request, index=eeg.index, arm='S0', client=SavedRoleResponses(calls), model=model)
                release = run_release(db, request, eeg=eeg, client=SavedRoleResponses(calls), model=model,
                                      model_settings=MODEL_SETTINGS[model], method=method)
                arm = run_condition(db, request, eeg=eeg, client=SavedRoleResponses(calls), model=model, method=method)['M3']
                observed = normalized(obs['outcome'])
                assert (dev['outcome'].get('es') == release['outcome'].get('es') ==
                        arm.get('es') == obs['outcome'].get('es')), str(location) + ' whole ESpec'
                assert normalized(dev['outcome']) == observed, str(location)+' original replay'
                assert normalized(release['outcome']) == observed, str(location)+' official output'
                assert normalized({key:arm[key] for key in obs['outcome']}) == observed, str(location)+' M3 output'
                for sequence in (dev['calls'], release['calls'], arm['model_calls']):
                    assert [(c['role'],c['prompt'],c['parsed_response']) for c in sequence] == [
                        (c['role'],c['prompt'],c['parsed_response']) for c in calls]
                for candidate in (dev['outcome'], release['outcome'], arm):
                    assert not (candidate.get('execution_review') or {}).get('repair_entered')
                counts[cohort] += 1
                counts[obs['outcome']['status']] += 1
                roles.update(c['role'] for c in calls)
                conditions.append({'cohort':cohort,'qid':obs['qid'],'model':model,'status':obs['outcome']['status'],
                                   'logical_roles':len(calls),'development_official_and_m3_equal':True})
    if len(conditions) != inputs['conditions'] or len(conditions) != 36:
        raise ValueError('Expected all 36 pinned development conditions')
    print(json.dumps({'counts': dict(counts), 'roles': dict(roles), 'method': method, 'conditions': conditions}, indent=2))


if __name__ == '__main__':
    main()
