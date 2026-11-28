"""Question-independent, content/version-addressed native and runtime EEG cache."""

from __future__ import annotations
from collections import OrderedDict
from contextlib import contextmanager
import fcntl
from copy import deepcopy
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import tempfile
import threading
import time
from src.common.runtime_input_contract import require_public_path, validate_runtime_graph
from src.common.llm_usage import experiment_settings
from src.eeg.eeg_store import EEGStore, INDEX_VERSION, write_index
from src.eeg.evidence_graph_storage import (
    FORMAT_VERSION, digest_bytes, json_bytes, read_eeg_layers, write_eeg_layers, write_json,
)
VERSION = 'eeg-cache-v5-carrier-identification'
ROOT = Path(__file__).resolve().parents[2]
_LOCK = threading.RLock()
_MEMORY = OrderedDict()
_FILE_DIGESTS = {}
_MAX_MEMORY = 4


def _file_digest(path):
    """PURPOSE: Hash changing DB/DD/code content once per inode/stat version.
    INPUT: Existing path. OUTPUT: Digest, with bounded metadata memoization and no key material.
    """
    path=Path(path).resolve(); stat=path.stat()
    token=(str(path),stat.st_ino,stat.st_size,stat.st_mtime_ns,stat.st_ctime_ns)
    if token not in _FILE_DIGESTS:
        digest=hashlib.sha256()
        with path.open('rb') as stream:
            for block in iter(lambda:stream.read(1024*1024),b''):
                digest.update(block)
        if len(_FILE_DIGESTS)>512:
            _FILE_DIGESTS.clear()
        _FILE_DIGESTS[token]=digest.hexdigest()
    return _FILE_DIGESTS[token]


def code_digest():
    """PURPOSE: Invalidate cached EEGs after runtime code or prompt changes.
    INPUT: This standalone project's src/ and prompt/ files.
    OUTPUT: Deterministic content digest; original NL2EL paths are never consulted.
    """
    paths = sorted((ROOT / 'src').rglob('*.py')) + sorted((ROOT / 'prompts').rglob('*.md'))
    return digest_bytes(json_bytes([(str(p.relative_to(ROOT)), _file_digest(p)) for p in paths]))


def cache_root(directory=None):
    """PURPOSE: Share one cache location across API, CLI, evaluation and demo.
    INPUT: Optional explicit directory or NL2EL_EEG_CACHE_DIR. OUTPUT: Resolved writable cache root.
    """
    return Path(directory or os.environ.get('NL2EL_EEG_CACHE_DIR') or ROOT/'.cache/eeg').resolve()


def _source_contract(database,dictionary,config,client):
    """PURPOSE: Identify DB data, public dictionary, effective settings and model availability.
    INPUT: Public DB/DD paths or dictionary mapping, immutable config and optional SDK client.
    OUTPUT: Non-secret immutable cache contract; changed WAL contents also invalidate reuse.
    """
    database=require_public_path(database)
    if isinstance(dictionary,(str,Path)):
        dd_path=require_public_path(dictionary)
        dd={'digest':digest_bytes(json_bytes(json.loads(dd_path.read_text(encoding='utf-8'))))}
    else:
        dd={'digest':digest_bytes(json_bytes(dictionary))}
    wal=Path(str(database)+'-wal')
    endpoint=str(getattr(client,'base_url','')) if client is not None else ''
    return {'version':VERSION,'database':str(database),'database_digest':_file_digest(database),
        'wal_digest':_file_digest(wal) if wal.is_file() else None,'dictionary':dd,
        'configuration':json.loads(json_bytes(asdict(config))),'model_settings':experiment_settings(config.model),
        'configuration_digest':config.digest(),'code_digest':code_digest(),
        'model_available':client is not None,'provider_digest':digest_bytes(endpoint.encode())}


def _restore_native(bundle):
    """PURPOSE: Restore native render/CLI metadata without profiling or model calls.
    INPUT: Validated public cache bundle. OUTPUT: Independent EvidenceGraph facade.
    """
    from src.eeg.evidence_graph_models import EvidenceGraph, Table, Column
    native=EvidenceGraph(deepcopy(bundle['data']))
    for field in ('report','llm_calls','normalized_dictionary','profiles'):
        setattr(native,field,deepcopy(bundle[field]))
    native.physical_tables=[Table(**{**table,'columns':[Column(**c) for c in table['columns']]})
                            for table in bundle['physical_tables']]
    return native


def _cache_audit(status,key,directory,manifest,elapsed):
    """PURPOSE: Distinguish historical build audits from actual work on a question cache hit.
    INPUT: Cache disposition and public manifest. OUTPUT: Small per-access cost/provenance mapping.
    """
    return {'status':status,'hit':status!='built','key':key,'directory':str(directory),
            'source_digest':manifest['contract']['database_digest'],
            'actual_build_llm_requests':manifest.get('build_llm_requests',0) if status=='built' else 0,
            'snapshot_build_llm_completed_requests':manifest['build_llm_completed_requests'],
            'elapsed_seconds':elapsed,'scope':'database_dictionary_configuration_code_not_question'}


@contextmanager
def _disk_lock(root,key):
    """PURPOSE: Share one build across separate API/CLI processes on the same host.
    INPUT: Cache root/key. OUTPUT: Exclusive file lock released even after build failure.
    """
    root.mkdir(parents=True,exist_ok=True)
    with (root/(key+'.lock')).open('a') as stream:
        fcntl.flock(stream.fileno(),fcntl.LOCK_EX)
        try:yield
        finally:fcntl.flock(stream.fileno(),fcntl.LOCK_UN)


def _return_index(location, key, manifest, started, status, runtime=None):
    """PURPOSE: Reuse a disk index or publish it once from a verified canonical snapshot.
    INPUT: Cache directory, identity, manifest, timing and optional full graph for one-time construction.
    OUTPUT: Read-only store or None if the canonical graph must be loaded to build it.
    """
    path = location / 'indexed-eeg.sqlite'
    index = manifest.get('index') or {}
    if index.get('version') != INDEX_VERSION or not path.is_file():
        if runtime is None:
            return None
        index = {'version': INDEX_VERSION, **write_index(path, runtime, key)}
        manifest['index'] = index
        write_json(location / 'manifest.json', manifest)
    audit = _cache_audit(status, key, location, manifest, time.perf_counter() - started)
    audit['index'] = index
    return EEGStore(path, key, audit)


def load_or_build(database,dictionary,*,client,config,response_cache=None,directory=None,force=False,include_native=True,prepare_summary=False,indexed=False):
    """PURPOSE: Build each DB EEG once, reusing immutable memory/disk snapshots across questions.
    INPUT: Public DB/DD, client/config, optional response cache/root and explicit rebuild flag.
    OUTPUT: (independent runtime graph, native facade); stale/corrupt artifacts are rebuilt, never trusted.
    Concurrent calls share a build lock; neither API keys nor question text are stored in cache keys.
    """
    from src.step1_understand.pipeline import build_evidence_graph
    from src.step1_understand.project_runtime_evidence_graph import to_runtime_graph
    from src.step1_understand.describe_business_entities_and_events import eeg_summary
    if client is None:
        raise ValueError('EEG construction requires an LLM client')
    started=time.perf_counter()
    with _LOCK:
        contract=_source_contract(database,dictionary,config,client)
        key=digest_bytes(json_bytes(contract)); root=cache_root(directory)
        with _disk_lock(root,key):
            location=root/key; memory_key=(str(root),key)
            if not indexed and not force and memory_key in _MEMORY and (not prepare_summary or 'revision_summary' in _MEMORY[memory_key][1]) and (location/'manifest.json').is_file():
                bundle,runtime,manifest=_MEMORY.pop(memory_key)
                _MEMORY[memory_key]=(bundle,runtime,manifest)
                graph=deepcopy(runtime)
                graph['eeg_cache']=_cache_audit('memory_hit',key,location,manifest,time.perf_counter()-started)
                return graph,_restore_native(bundle) if include_native else None
            if not force and (location/'manifest.json').is_file():
                try:
                    manifest=json.loads((location/'manifest.json').read_text())
                    if manifest['contract']!=contract or manifest['key']!=key:
                        raise ValueError('cache_contract_mismatch')
                    if manifest.get('build_llm_completed_requests',0) < 1:
                        raise ValueError('EEG cache has no completed model requests')
                    if manifest['storage_format'] != FORMAT_VERSION:
                        raise ValueError('cache_storage_format_mismatch')
                    if indexed and (store := _return_index(location, key, manifest, started, 'disk_hit')):
                        return store, None
                    runtime,bundle=read_eeg_layers(location,manifest['artifacts'])
                    if bundle is None:
                        raise ValueError('cache_native_bundle_missing')
                    validate_runtime_graph(runtime)
                    if indexed:
                        return _return_index(location, key, manifest, started, 'disk_hit', runtime), None
                    if prepare_summary and 'revision_summary' not in runtime and client is not None:
                        runtime['revision_summary'] = eeg_summary(runtime,client,config.model)
                        manifest['artifacts'] = write_eeg_layers(location,runtime,native_bundle=bundle)
                        write_json(location/'manifest.json',manifest)
                    _MEMORY[memory_key]=(bundle,runtime,manifest)
                    while len(_MEMORY)>_MAX_MEMORY:_MEMORY.popitem(last=False)
                    graph=deepcopy(runtime)
                    graph['eeg_cache']=_cache_audit('disk_hit',key,location,manifest,time.perf_counter()-started)
                    return graph,_restore_native(bundle) if include_native else None
                except (OSError,ValueError,KeyError,TypeError):
                    pass
            if dictionary is None:raise ValueError('Public dictionary is required')
            from src.common.llm_usage import MeteredClient
            build_client=MeteredClient(client)
            if isinstance(dictionary,(str,Path)):
                native=build_evidence_graph(Path(database),Path(dictionary),config,build_client,cache=response_cache)
            else:
                with tempfile.TemporaryDirectory(prefix='nl2el-public-dd-') as temporary:
                    path=Path(temporary)/'dictionary.json';path.write_bytes(json_bytes(dictionary))
                    native=build_evidence_graph(Path(database),path,config,build_client,cache=response_cache)
            completed = sum(request['status']=='completed' for request in build_client.requests)
            if not completed:
                raise RuntimeError('EEG construction did not complete any LLM requests')
            runtime=to_runtime_graph(native,database)
            validate_runtime_graph(runtime)
            if prepare_summary:
                runtime['revision_summary'] = eeg_summary(runtime,build_client,config.model)
            if contract!=_source_contract(database,dictionary,config,client):
                raise RuntimeError('Public DB/DD changed while building EEG; snapshot was not cached')
            bundle={'data':native.data,'report':native.report,'llm_calls':native.llm_calls,
                    'normalized_dictionary':native.normalized_dictionary,'profiles':native.profiles,
                    'physical_tables':[asdict(t) for t in native.physical_tables]}
            requests=len(build_client.requests)
            native.report['summary']['actual_llm_requests']=requests
            native.report['summary']['actual_llm_usage']=build_client.requests
            manifest={'key':key,'contract':contract,'build_llm_requests':requests,
                      'build_llm_completed_requests':completed,
                      'storage_format':FORMAT_VERSION,
                      'artifacts':write_eeg_layers(location,runtime,native_bundle=bundle)}
            write_json(location/'manifest.json',manifest)
            if indexed:
                return _return_index(location, key, manifest, started, 'built', runtime), None
            _MEMORY[memory_key]=(deepcopy(bundle),deepcopy(runtime),manifest)
            while len(_MEMORY)>_MAX_MEMORY:_MEMORY.popitem(last=False)
            runtime['eeg_cache']=_cache_audit('built',key,location,manifest,time.perf_counter()-started)
            return runtime,native if include_native else None


def clear_memory():
    """PURPOSE: Release process snapshots for tests or explicit cache invalidation.
    INPUT: None. OUTPUT: No memory cache entries; persistent files remain controlled by maintenance tools.
    """
    with _LOCK:_MEMORY.clear()
