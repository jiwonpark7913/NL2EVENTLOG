"""Official three-stage NL2EventLog release candidate backed by the measured S0."""

from dataclasses import dataclass
from pathlib import Path

from development.s2.runtime import PATH_PROMPT, SCOPE_PROMPT, run as run_s0
from evaluation_harness.contract import ROOT, digest, read, value_digest, write
from src.common.runtime_input_contract import RuntimeInputError, require_public_path, sanitize_dictionary, validate_runtime_graph
from src.common.schema_metadata import database_fingerprint
from src.eeg.eeg_store import EEGStore
from src.eeg.evidence_graph_cache import load_or_build
from src.eeg.evidence_graph_storage import read_eeg_layers
from src.step1_understand.eeg_configuration import DbuConfig
from src.step2_retrieve_and_interpret.execute_model_roles import SCHEMAS

METHOD_VERSION = 'nl2eventlog-refreshed-s0-v1.0.0'
HAIKU = 'claude-haiku-5-5'
ROLES = ('minimal_intent', 'minimal_case', 'minimal_events')


@dataclass(frozen=True)
class PreparedEEG:
    """A verified graph and index shared by the release method and applicable baselines."""

    graph: dict
    index: EEGStore
    identity: dict


def release_identity():
    """PURPOSE: Pin shipped runtime source, prompts and S0 schemas.
    INPUT: Local release tree. OUTPUT: Canonical source and contract digests without credentials.
    """
    roots = ('src', 'development/case_catalog_m0', 'development/s2', 'development/scope_attribution_m0')
    source = [p for name in roots for p in (ROOT/name).rglob('*.py')]
    templates = [*(ROOT/'prompts').rglob('*.md'), PATH_PROMPT, SCOPE_PROMPT]
    inventory = lambda files: {str(p.relative_to(ROOT)): digest(p) for p in sorted(files)}
    return {'method': METHOD_VERSION, 'arm': 'S0', 'source_sha256': value_digest(inventory(source)),
            'prompt_sha256': value_digest(inventory(templates)),
            'schema_sha256': value_digest({role: SCHEMAS[role] for role in ROLES})}


def release_public_path(path):
    """PURPOSE: Check the release's explicit inference boundary before any input read.
    INPUT: Public artifact path. OUTPUT: Resolved path or a rejection of known evaluator assets.
    """
    location = require_public_path(path)
    if ({part.casefold() for part in location.parts} & {'gold', 'evaluator', 'evaluator_only', 'references'}
            or location.name.casefold().startswith(('gold.', 'reference.', 'gold_', 'reference_'))):
        raise RuntimeInputError('Evaluator-only file cannot be a release input')
    return location

def public_identity(database, dictionary):
    """PURPOSE: Bind exact standalone SQLite and Original DD bytes before inference.
    INPUT: Public database and dictionary paths. OUTPUT: Their hashes. Rejects an active WAL.
    """
    database, dictionary = map(release_public_path, (database, dictionary))
    wal = database.with_name(database.name + '-wal')
    if wal.exists() and wal.stat().st_size:
        raise ValueError('Release requests require a standalone immutable SQLite snapshot')
    return {'database_sha256': digest(database), 'dictionary_sha256': digest(dictionary)}


def prepare_eeg(database, dictionary, *, build_client=None, config=None, cache=None, snapshot=None):
    """PURPOSE: Load a verified EEG or use the existing request-independent construction cache.
    INPUT: Public DB/DD paths, optional build client/config and a captured snapshot directory.
    OUTPUT: Graph, checked read-only Index and exact DB/DD/graph/configuration identity.
    """
    database, dictionary = map(release_public_path, (database, dictionary))
    inputs = public_identity(database, dictionary)
    if snapshot is None:
        config = config or DbuConfig(model=HAIKU)
        store, _ = load_or_build(database, dictionary, client=build_client, config=config,
                                 directory=cache, include_native=False, prepare_summary=False, indexed=True)
        location = Path(store.cache_audit['directory'])
        cache_manifest = read(location/'manifest.json')
        graph, _ = read_eeg_layers(location, cache_manifest['artifacts'])
        graph_hash, index_hash = value_digest(graph), digest(store.path)
        origin = store.cache_audit['status']
    else:
        directory = release_public_path(snapshot)
        manifest = read(release_public_path(directory/'snapshot.json'))
        graph = read(release_public_path(directory/'eeg.json'))
        index_file = release_public_path(directory/'index.sqlite')
        graph_hash, index_hash = value_digest(graph), digest(index_file)
        if (manifest['eeg_sha256'], manifest['index_sha256']) != (graph_hash, index_hash):
            raise ValueError('EEG or Index differs from its snapshot manifest')
        if any(manifest.get(key, value) != value for key, value in inputs.items()):
            raise ValueError('Snapshot DB/DD hashes differ from supplied inputs')
        store = EEGStore(index_file, manifest.get('index_snapshot_id', graph_hash))
        origin = 'supplied_snapshot'
    validate_runtime_graph(graph)
    _, dd_audit = sanitize_dictionary(read(dictionary))
    if graph.get('input_contract_audit', {}).get('input_sha256') != dd_audit['input_sha256']:
        raise ValueError('Original DD does not match the EEG construction input')
    if graph.get('database_fingerprint') != database_fingerprint(database):
        raise ValueError('Database does not match the prepared EEG')
    if config is not None and value_digest(graph.get('build_configuration')) != value_digest(vars(config)):
        raise ValueError('EEG construction configuration differs from the requested configuration')
    with store.open(database):
        pass
    identity = {**inputs, 'eeg_sha256': graph_hash, 'index_sha256': index_hash,
                'index_snapshot_id': store.snapshot_id, 'origin': origin,
                'database_fingerprint': graph['database_fingerprint'],
                'construction_configuration': graph.get('build_configuration'),
                'construction_configuration_sha256': value_digest(graph.get('build_configuration'))}
    return PreparedEEG(graph, store, identity)


def run_release(database, question, *, eeg, client, model, model_settings, method=None):
    """PURPOSE: Invoke the measured S0 branch and record release provenance.
    INPUT: Public DB, original question, prepared EEG and configured model client.
    OUTPUT: Unmodified development receipt with added source/configuration binding.
    """
    if eeg.identity['database_fingerprint'] != database_fingerprint(database):
        raise ValueError('Prepared EEG belongs to another database snapshot')
    if model_settings.get('id') != model:
        raise ValueError('Model settings do not identify the requested model')
    result = run_s0(database, question, index=eeg.index, client=client, model=model, arm='S0')
    receipt = {**(method or release_identity()), **eeg.identity,
               'model': model, 'model_settings': model_settings,
               'model_settings_sha256': value_digest(model_settings),
               'wire_sha256': [value_digest(call['prompt']) for call in result['calls']],
               'terminal_status': result['outcome']['status']}
    return {**result, 'release': receipt}


def save_release(result, directory, eeg):
    """PURPOSE: Publish a new standalone result and a reusable verified EEG snapshot.
    INPUT: Completed S0 receipt, new output directory and prepared public EEG.
    OUTPUT: Manifest, PI, ESpec, validation and accepted SQL/CSV when available.
    """
    from shutil import copy2
    from src.__main__ import write_event_artifacts

    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    if (directory/'manifest.json').exists():
        raise ValueError('Output already contains a published release')
    snapshot = directory/'eeg'
    write(snapshot/'eeg.json', eeg.graph)
    copy2(eeg.index.path, snapshot/'index.sqlite')
    if digest(snapshot/'index.sqlite') != eeg.identity['index_sha256']:
        raise ValueError('EEG Index changed before publication')
    write(snapshot/'snapshot.json', eeg.identity)
    outcome = result['outcome']
    write(directory/'process_information.json', outcome.get('pi'))
    write(directory/'extraction_specification.json', outcome.get('es'))
    write(directory/'verification.json', {'structural': outcome.get('structural'),
                                          'execution_review': outcome.get('execution_review')})
    if outcome['status'] == 'accepted':
        write_event_artifacts(directory, {'sql': outcome['sql'], 'event_log': outcome['rows']}, 'event_log.csv')
    write(directory/'receipt.json', result)
    write(directory/'manifest.json', result['release'])
