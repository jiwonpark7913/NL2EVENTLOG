"""Command-line entrypoint for the current NL2EventLog pipeline."""
import argparse
import csv
import json
from pathlib import Path

from src.common.llm_usage import DEFAULT_MODEL
from src.step1_understand.eeg_configuration import load_config
from src.eeg.evidence_graph_storage import FORMAT_VERSION, write_eeg_layers, write_json


def save_run(result, directory):
    """PURPOSE: Save reviewable stage artifacts from one completed request.
    INPUT: run_pipeline result and destination directory.
    OUTPUT: Layered EEG, a flat EEG export, stage JSON, and SQL and CSV on success.
    """
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    eeg_directory = directory / 'eeg'
    eeg_artifacts = write_eeg_layers(eeg_directory, result['graph'])
    write_json(eeg_directory / 'manifest.json', {
        'storage_format': FORMAT_VERSION, 'artifacts': eeg_artifacts,
    })
    artifacts = {
        'evidence_graph': result['graph'],
        'process_information': result['query'],
        'extraction_bindings': result['retrieval'],
        'extraction_specification': result['es'],
        'verification': result['verification'],
        'manifest': result['manifest'],
    }
    for name, value in artifacts.items():
        (directory / f'{name}.json').write_text(
            json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    terminal = result.get('terminal_status') or result['es'].get('status')
    execution = result.get('execution') or {}
    if terminal == 'accepted' and execution.get('passed'):
        write_event_artifacts(directory, execution, 'event_log.csv')
    else:
        for name in ('extraction.sql', 'event_log.csv'):
            (directory / name).unlink(missing_ok=True)
        diagnostic = result.get('diagnostic_execution') or execution
        if diagnostic.get('sql'):
            folder = directory / 'diagnostic'
            folder.mkdir(exist_ok=True)
            write_event_artifacts(folder, diagnostic, 'partial_event_log.csv' if terminal == 'partial' else 'rows.csv')


def write_event_artifacts(directory, execution, csv_name):
    """PURPOSE: Save one accepted or diagnostic execution under its caller-selected path.
    INPUT: Output folder, SQL/row receipt and CSV name. OUTPUT: SQL and optional CSV.
    """
    from src.step3_execute.compile_event_log_sql import OUTPUT_COLUMNS
    (directory / 'extraction.sql').write_text(execution['sql'] + '\n', encoding='utf-8')
    rows = execution.get('event_log')
    if rows is not None:
        with (directory / csv_name).open('w', newline='', encoding='utf-8') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]) if rows else list(OUTPUT_COLUMNS))
            writer.writeheader()
            writer.writerows(rows)


def main(argv=None):
    """PURPOSE: Run the three method stages from public DB/DD and one natural-language request.
    INPUT: CLI paths, request, model and optional JSON/YAML EEG config; SDK reads environment credentials.
    OUTPUT: Saved artifacts and printed status; returns zero on acceptance, two on unresolved/failed extraction.
    """
    parser = argparse.ArgumentParser(description='Extract a verified event log from SQLite and a public data dictionary.')
    parser.add_argument('--database', required=True, type=Path)
    parser.add_argument('--dictionary', required=True, type=Path)
    request = parser.add_mutually_exclusive_group(required=True)
    request.add_argument('--question')
    request.add_argument('--question-file', type=Path)
    parser.add_argument('--model')
    parser.add_argument('--method', choices=('refreshed-s0', 'legacy'), default='refreshed-s0')
    parser.add_argument('--eeg-snapshot', type=Path, help='Directory with eeg.json, index.sqlite and snapshot.json')
    parser.add_argument('--eeg-cache', type=Path)
    parser.add_argument('--max-usd', help='Explicit combined provider limit for the requested standalone run')
    parser.add_argument('--config', type=Path)
    parser.add_argument('--no-event-recovery', action='store_true')
    parser.add_argument('--max-pi-calls', type=int)
    parser.add_argument('--max-pi-input-tokens', type=int)
    parser.add_argument('--pi-mode', choices=('sequential', 'unified'))
    parser.add_argument('--retrieval-mode', choices=('graph', 'semantic', 'full'))
    parser.add_argument('--output-dir', required=True, type=Path)
    args = parser.parse_args(argv)
    config = load_config(args.config) if args.config else None
    from src.release_runtime import release_public_path

    question = args.question if args.question is not None else (
        release_public_path(args.question_file).read_text(encoding='utf-8').strip())
    if args.method == 'legacy':
        from openai import OpenAI
        from src.pipeline import run_pipeline
        if args.eeg_snapshot or args.eeg_cache or args.max_usd is not None:
            parser.error('The legacy entry point does not accept S0 snapshot or native budget options')
        model = args.model or (config.model if config else DEFAULT_MODEL)
        result = run_pipeline(args.database, args.dictionary, question, client=OpenAI(), model=model, config=config,
                              recovery_enabled=not args.no_event_recovery, retrieval_mode=args.retrieval_mode or 'graph',
                              pi_mode=args.pi_mode or 'sequential', max_pi_calls=args.max_pi_calls if args.max_pi_calls is not None else 32,
                              max_pi_input_tokens=args.max_pi_input_tokens if args.max_pi_input_tokens is not None else 240_000)
        save_run(result, args.output_dir)
        status, es_status = result['terminal_status'], result['es'].get('status')
    else:
        if any(x is not None for x in (args.pi_mode, args.retrieval_mode, args.max_pi_calls, args.max_pi_input_tokens)) or args.no_event_recovery:
            parser.error('Legacy interpretation options require --method legacy')
        if args.max_usd is None:
            parser.error('Native Refreshed S0 requires --max-usd for the requested run')
        status, es_status = run_official(args, question, config)
    print(json.dumps({'status': status, 'es_status': es_status, 'output_dir': str(args.output_dir)}, ensure_ascii=False))
    return 0 if status == 'accepted' else 2


def run_official(args, question, config):
    """PURPOSE: Connect the default standalone CLI to Refreshed S0 with audited native providers.
    INPUT: CLI arguments, original question and optional compatible EEG build settings.
    OUTPUT: Terminal and ESpec statuses from the official result writer.
    """
    from src.release_providers import SETTINGS, release_clients, check_limit
    from src.release_runtime import HAIKU, prepare_eeg, public_identity, run_release, save_release

    model = args.model or HAIKU
    settings = {value['id']: value for value in SETTINGS.values()}
    build_model = config.model if config is not None else HAIKU
    public_identity(args.database, args.dictionary)
    args.output_dir.mkdir(parents=True, exist_ok=False)
    models = {model} if args.eeg_snapshot is not None else {model, build_model}
    with release_clients(args.output_dir/'provider', models=models, maximum=args.max_usd) as (clients, guards):
        eeg = prepare_eeg(args.database, args.dictionary, config=config, snapshot=args.eeg_snapshot,
                          cache=args.eeg_cache, build_client=clients.get(build_model))
        check_limit(guards, clients)
        result = run_release(args.database, question, eeg=eeg, client=clients[model], model=model,
                             model_settings=settings[model])
        save_release(result, args.output_dir, eeg)
        check_limit(guards, clients)
    outcome = result['outcome']
    return outcome['status'], (outcome.get('es') or {}).get('status')


if __name__ == '__main__':
    raise SystemExit(main())
