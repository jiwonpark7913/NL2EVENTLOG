"""Run the paper arms through the Refreshed S0 release candidate."""

import argparse
from contextlib import contextmanager
from pathlib import Path
import json
import subprocess
import sys
from time import perf_counter

from cross_model_evaluation.providers import entries
from evaluation_harness.contract import (
    FROZEN, RELEASE_V4_DESCRIPTOR_SHA256, digest, read, value_digest, write,
)
from src.common.runtime_input_contract import require_no_oracle_payload
from src.release_runtime import (
    HAIKU, prepare_eeg, public_identity, release_identity, release_public_path, run_release,
)
from src.release_providers import SETTINGS, check_limit, release_clients

RUNNER_VERSION = 'nl2eventlog-final-evaluation-rc1'
ARMS = ('M0', 'M1', 'M2', 'M3', 'S-LLM', 'S-Gen')
MODEL_SETTINGS = {settings['id']: settings for settings in SETTINGS.values()}


def companion_worker(*args, input_text=None):
    """PURPOSE: Isolate legacy scorer and Compact EEG imports from the current runtime namespace.
    INPUT: Worker command and optional public EEG on stdin. OUTPUT: JSON worker result.
    """
    descriptor = FROZEN/'FINAL_EVALUATION_FREEZE_V4.json'
    if not descriptor.is_file() or digest(descriptor) != RELEASE_V4_DESCRIPTOR_SHA256:
        raise ValueError('Set NL2EVENTLOG_COMPANION_DIR to the original hash-verified v4 companion')
    env = {'PYTHONPATH': str(FROZEN), 'PYTHONDONTWRITEBYTECODE': '1', 'LANG': 'C.UTF-8'}
    result = subprocess.run([sys.executable, str(Path(__file__).with_name('final_worker.py').resolve()), *map(str, args)],
                            cwd=FROZEN, env=env, input=input_text, text=True, capture_output=True, check=True)
    return json.loads(result.stdout)


@contextmanager
def measure_operation(measurements, name, ledgers):
    """PURPOSE: Observe one completed or interrupted operation without changing its model wire.
    INPUT: Optional receipt mapping, operation name and provider-to-ledger paths.
    OUTPUT: Adds elapsed seconds and half-open native attempt ranges for the operation.
    """
    if measurements is None:
        yield
        return
    start = perf_counter()
    offsets = {model: len(entries(path)) for model, path in ledgers.items()}
    try:
        yield
    finally:
        measurements[name] = {'wall_seconds': perf_counter() - start,
                              'provider_attempt_ranges': {
                                  model: [offsets[model], len(entries(path))] for model, path in ledgers.items()}}


def run_condition(database, question, *, client, model, arms=('M3',), eeg=None,
                  base=None, tools=None, compact=None, method=None, measurements=None, ledgers=None):
    """PURPOSE: Execute one matched paper-arm group from public information only.
    INPUT: Original request, release EEG, optional shared Direct SQL inputs, and configured client.
    OUTPUT: Arm receipts and optional operation timings and native attempt spans. Dependent arms share one S0.
    """
    from evaluation_harness.final_baselines import direct_result

    if not arms or len(set(arms)) != len(arms) or set(arms) - set(ARMS):
        raise ValueError('Expected distinct registered paper arms')
    if any(arm != 'M0' for arm in arms) and eeg is None:
        raise ValueError('These arms require a prepared EEG')
    if set(arms) & {'M0', 'M1', 'M2', 'S-LLM'} and (base is None or tools is None):
        raise ValueError('The Direct SQL arms require the common public context and frozen tools')
    if 'M1' in arms and (compact is None or compact['eeg_sha256'] != eeg.identity['eeg_sha256']):
        raise ValueError('M1 requires the Compact EEG from the same graph as S0')

    def model_sql(arm, context):
        """PURPOSE: Measure one generation arm. INPUT: Arm and its public context. OUTPUT: Raw SQL baseline receipt."""
        with measure_operation(measurements, arm, ledgers or {}):
            return direct_result(database, question, context, client, model, tools)

    records = {}
    if 'M0' in arms:
        records['M0'] = model_sql('M0', base)
    if 'M1' in arms:
        payload = compact['payload']
        records['M1'] = {**model_sql('M1', {**base, 'evidence_graph': payload}),
                         'eeg_sha256': eeg.identity['eeg_sha256'], 'm1_eeg_format': payload['format'],
                         'm1_eeg_sha256': value_digest(payload)}
    if set(arms) <= {'M0', 'M1'}:
        return records

    with measure_operation(measurements, 'shared_s0', ledgers or {}):
        run = run_release(database, question, eeg=eeg, client=client, model=model,
                          model_settings=MODEL_SETTINGS[model], method=method)
    outcome = run['outcome']
    pi, es = outcome.get('pi'), outcome.get('es')
    shared = {'eeg_sha256': eeg.identity['eeg_sha256'], 'pi': pi,
              'pi_sha256': value_digest(pi) if pi is not None else None,
              'es_sha256': value_digest(es) if es is not None else None}
    if 'M3' in arms:
        records['M3'] = {**outcome, **shared, 'initial_pi': run.get('initial'),
                         'model_calls': run['calls'], 'wall_seconds': run['elapsed_seconds'], 'release': run['release']}
    if 'M2' in arms:
        if pi is None:
            output = {'status': 'selection_required', 'rows': [], 'sql': None, 'reason': 'shared_pi_unavailable'}
        else:
            context = {**base, 'process_interpretation': pi,
                       'generation_contract': 'Implement the supplied process interpretation without changing its selections.'}
            output = model_sql('M2', context)
        records['M2'] = {**shared, **output}
    if 'S-LLM' in arms:
        if es is None or es['status'] != 'accepted':
            output = {'status': 'selection_required', 'rows': [], 'sql': None, 'reason': 'shared_es_unavailable'}
        else:
            context = {**base, 'fixed_extraction_ir': es,
                       'generation_contract': 'Render the supplied extraction specification as SQL without modifying it.'}
            output = model_sql('S-LLM', context)
        records['S-LLM'] = {**shared, **output, 'es': es}
    if 'S-Gen' in arms:
        records['S-Gen'] = {**outcome, **shared}
    return records


def public_plan(args):
    """PURPOSE: Bind a public inference lane before approval or provider initialization.
    INPUT: CLI paths, arms, provider model and phase. OUTPUT: Checked questions and exact binding.
    """
    question_path = release_public_path(args.questions)
    questions = read(question_path)
    if not isinstance(questions, list) or not questions:
        raise ValueError('Provide a nonempty public question array')
    for item in questions:
        if (not isinstance(item, dict) or item.keys() != {'qid', 'question'}
                or not isinstance(item['qid'], str) or not item['qid'].isascii() or not item['qid'].isalnum()
                or not isinstance(item['question'], str) or not item['question'].strip()):
            raise ValueError('Only public qid/question records are accepted')
    qids = [item['qid'] for item in questions]
    if len(set(qids)) != len(qids) or len(set(args.arms)) != len(args.arms):
        raise ValueError('Question IDs and arms must be distinct')
    method = release_identity()
    adapter_sources = [Path(__file__), Path(__file__).with_name('final_baselines.py'),
                       Path(__file__).with_name('final_worker.py'), Path(__file__).with_name('direct_sql_protocol.py')]
    binding = {**public_identity(args.database, args.dictionary),
               'runner': RUNNER_VERSION, 'runner_sha256': value_digest([digest(path) for path in adapter_sources]),
               'method': method, 'questions_sha256': digest(question_path), 'qids': qids,
               'question_sha256': {item['qid']: value_digest(item) for item in questions},
               'phase': args.phase, 'arms': args.arms, 'model': MODEL_SETTINGS[args.model],
               'construction_model': HAIKU, 'evaluation_v4_sha256': RELEASE_V4_DESCRIPTOR_SHA256}
    if args.eeg_snapshot is not None:
        snapshot = release_public_path(args.eeg_snapshot)
        binding['input_snapshot'] = {name: digest(release_public_path(snapshot/name)) for name in ('eeg.json', 'index.sqlite', 'snapshot.json')}
    return questions, binding


def infer(args, questions, binding):
    """PURPOSE: Run only the separately approved public lane and checkpoint immutable outcomes.
    INPUT: Public plan, signed-off approval record and new output directory. OUTPUT: Raw receipts and native usage.
    """
    from evaluation_harness.final_baselines import direct_context, direct_tools

    approval = read(args.approval)
    required = {'scope': RUNNER_VERSION, 'binding_sha256': value_digest(binding), 'authorized': True}
    if any(approval.get(key) != expected for key, expected in required.items()):
        raise ValueError('Inference requires approval of this exact final-runner plan')
    billing = approval.get('gemini_billing')
    if (args.model != HAIKU and (billing not in {'paid_cap_permitted', 'verified_free_only'}
                                or (billing == 'verified_free_only' and approval.get('free_project_verified') is not True))):
        raise ValueError('Gemini needs a registered paid cap or verified free project')
    args.output.mkdir(parents=True, exist_ok=False)
    uses_eeg = set(args.arms) != {'M0'}
    needs_build = uses_eeg and args.eeg_snapshot is None
    models = {args.model, HAIKU} if needs_build else {args.model}
    ledgers = {model: args.output/'provider'/('claude.json' if model == HAIKU else 'gemini.json')
               for model in sorted(models)}
    setup_measurements = {}
    with release_clients(args.output/'provider', models=models, maximum=approval['max_usd'],
                         gemini_billing=billing) as (clients, guards):
        eeg = None
        if uses_eeg:
            with measure_operation(setup_measurements, 'eeg_preparation', ledgers):
                eeg = prepare_eeg(args.database, args.dictionary, snapshot=args.eeg_snapshot,
                                  build_client=clients.get(HAIKU), cache=args.eeg_cache)
            write(args.output/'eeg.json', eeg.graph)
        check_limit(guards, clients)
        tools = direct_tools() if set(args.arms) & {'M0', 'M1', 'M2', 'S-LLM'} else None
        base = direct_context(args.database, args.dictionary, tools) if tools is not None else None
        compact = None
        if 'M1' in args.arms:
            with measure_operation(setup_measurements, 'compact_eeg_preparation', ledgers):
                payload = companion_worker('compact', input_text=json.dumps(eeg.graph, ensure_ascii=False))
            require_no_oracle_payload(payload)
            compact = {'payload': payload, 'eeg_sha256': eeg.identity['eeg_sha256']}
            write(args.output/'m1-eeg.json', compact)
        if public_plan(args)[1] != binding:
            raise ValueError('Public or method inputs changed after approval')
        manifest = {'runner': RUNNER_VERSION, 'binding': binding, 'binding_sha256': value_digest(binding),
                    'approval_sha256': digest(args.approval), 'eeg': eeg.identity if eeg else None,
                    'setup_measurements': setup_measurements,
                    'm1_eeg_sha256': value_digest(compact['payload']) if compact else None}
        write(args.output/'run.json', manifest)
        for item in questions:
            clients[args.model].reset_request_state()
            start = perf_counter()
            ledger = ledgers[args.model]
            measurements = {}
            first_attempt = len(entries(ledger))
            records = run_condition(args.database, item['question'], client=clients[args.model], model=args.model,
                                    arms=args.arms, eeg=eeg, compact=compact, base=base, tools=tools,
                                    method=binding['method'], measurements=measurements, ledgers={args.model: ledger})
            condition = {'binding_sha256': manifest['binding_sha256'], 'qid': item['qid'],
                         'question_sha256': value_digest(item), 'wall_seconds': perf_counter() - start,
                         'provider_attempt_range': [first_attempt, len(entries(ledger))], 'operations': measurements}
            write(args.output/(item['qid']+'.json'), {'_condition': condition, **records})
            check_limit(guards, clients)
        if public_plan(args)[1] != binding:
            raise ValueError('Public or method inputs changed during inference')
        write(args.output/'complete.json', {'binding_sha256': value_digest(binding), 'conditions': len(questions)})


def main(argv=None):
    """PURPOSE: Separate plan and approved public inference from offline v4 scoring.
    INPUT: CLI arguments for one operation. OUTPUT: Plan, raw receipts, or a private score document.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('plan', 'infer'):
        command = commands.add_parser(name)
        for key in ('database', 'dictionary', 'questions'):
            command.add_argument('--'+key, required=True, type=Path)
        command.add_argument('--eeg-snapshot', type=Path)
        command.add_argument('--eeg-cache', type=Path)
        command.add_argument('--phase', required=True, choices=('pilot', 'test', 'development'))
        command.add_argument('--model', required=True, choices=MODEL_SETTINGS)
        command.add_argument('--arms', nargs='+', choices=ARMS, default=['M3'])
        if name == 'infer':
            command.add_argument('--approval', required=True, type=Path)
            command.add_argument('--output', required=True, type=Path)
    score = commands.add_parser('score-v4')
    for key in ('database', 'references', 'predictions', 'output'):
        score.add_argument('--'+key, required=True, type=lambda text: Path(text).resolve())
    args = parser.parse_args(argv)
    if args.command == 'score-v4':
        if args.output.exists() or args.output.is_relative_to(args.predictions):
            raise ValueError('Write offline scores to a new file outside the inference receipts')
        write(args.output, companion_worker('score-v4', args.database, args.references, args.predictions))
    else:
        questions, binding = public_plan(args)
        if args.command == 'plan':
            print(json.dumps({'binding': binding, 'binding_sha256': value_digest(binding)}, ensure_ascii=False, indent=2))
        else:
            infer(args, questions, binding)


if __name__ == '__main__':
    main()
