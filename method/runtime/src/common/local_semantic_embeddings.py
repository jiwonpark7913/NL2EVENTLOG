"""Local sentence embeddings for public runtime evidence; no downloads or API calls."""

from __future__ import annotations
import atexit
import contextlib
import selectors
import subprocess
import sys
import threading
from collections import OrderedDict
from functools import lru_cache
import json
import os
from pathlib import Path
DEFAULT_MODEL = 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
DEFAULT_REVISION = 'e8f8c211226b894fcb81acc59f3b34ba3efd5f42'


class LocalSemanticEncoder:
    """Batch and cache a bounded number of embeddings from one local CPU model."""

    def __init__(self, model, identity, cache_size=4096):
        """PURPOSE: Bind one loaded encoder to its model identity.
        INPUT: SentenceTransformer-compatible model, public identity and vector cache bound.
        OUTPUT: Encoder with an in-memory LRU cache; source DBs remain untouched.
        """
        self.model, self.identity, self.cache_size = model, identity, cache_size
        self.vectors = OrderedDict()

    def encode(self, texts):
        """PURPOSE: Encode missing texts together and reuse unchanged evidence vectors.
        INPUT: Ordered list of public text strings.
        OUTPUT: Same-order numeric vectors; no persistence, network or source mutation.
        """
        missing = list(dict.fromkeys(text for text in texts if text not in self.vectors))
        fresh = self.model.encode(missing, normalize_embeddings=True, show_progress_bar=False,
                                  batch_size=32) if missing else []
        resolved = {text: list(map(float, vector)) for text, vector in zip(missing, fresh)}
        result = []
        for text in texts:
            vector = resolved.get(text, self.vectors.get(text))
            if vector is None:
                raise ValueError('semantic_encoder_missing_vector')
            self.vectors[text] = vector
            self.vectors.move_to_end(text)
            result.append(vector)
            while len(self.vectors) > self.cache_size:
                self.vectors.popitem(last=False)
        return result


@lru_cache(maxsize=4)
def _load_local_encoder(model_name, revision):
    """PURPOSE: Load a CPU encoder once without downloads or remote code.
    INPUT: Local path or cached Hugging Face model ID, plus optional revision.
    OUTPUT: (encoder, availability audit); missing dependencies/models yield an explicit fallback.
    """
    identity = {'model': model_name, 'revision': revision or None, 'device': 'cpu'}
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(model_name, device='cpu', local_files_only=True,
                                    trust_remote_code=False, **({'revision': revision} if revision else {}))
        lock = Path(model_name) / 'source_lock.json'
        if lock.is_file():
            identity.update(json.loads(lock.read_text()))
        return LocalSemanticEncoder(model, identity), dict(identity, status='available')
    except (ImportError, OSError, RuntimeError, ValueError) as exc:
        return None, dict(identity, status='unavailable', reason=type(exc).__name__,
                          fallback='bm25_and_character_cosine')


def local_semantic_encoder():
    """PURPOSE: Resolve configured offline meaning retrieval without mandatory ML dependencies.
    INPUT: NL2EL_SEMANTIC_MODEL/REVISION environment; 'off' disables dense retrieval.
    OUTPUT: (encoder or None, configuration audit); never implicitly downloads a model.
    """
    prepared = Path(__file__).resolve().parents[2] / '.cache' / 'semantic_model'
    default = str(prepared) if (prepared / 'config.json').exists() else DEFAULT_MODEL
    model_name = os.environ.get('NL2EL_SEMANTIC_MODEL', default)
    if model_name.casefold() in {'off', 'none', 'disabled'}:
        return None, {'status': 'disabled', 'fallback': 'bm25_and_character_cosine'}
    revision = os.environ.get('NL2EL_SEMANTIC_REVISION', DEFAULT_REVISION if model_name == DEFAULT_MODEL else '')
    python = os.environ.get('NL2EL_SEMANTIC_PYTHON')
    runtime = prepared / 'runtime.json'
    if python is None and runtime.is_file():
        try:
            python = json.loads(runtime.read_text()).get('python')
        except (ValueError, OSError, AttributeError):
            return None, {'status': 'unavailable', 'reason': 'invalid_local_runtime_configuration',
                          'fallback': 'bm25_and_character_cosine'}
    if python and Path(python).resolve() != Path(sys.executable).resolve():
        return _load_process_encoder(python, model_name, revision)
    return _load_local_encoder(model_name, revision)


class EncoderProcess:
    """Keep a prepared local encoder in its dependency environment across retrieval batches."""

    def __init__(self, python, model_name, revision):
        """PURPOSE: Start a local CPU encoder without changing the caller's Python environment.
        INPUT: Explicitly configured interpreter, local/cached model and revision.
        OUTPUT: Ready JSON-lines subprocess; no sockets, external APIs or implicit downloads.
        """
        self.lock = threading.Lock()
        self.process = subprocess.Popen(
            [python, '-u', str(Path(__file__).resolve()), '--worker', model_name, revision],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, encoding='utf-8')
        atexit.register(self.close)
        response = self._read()
        if response.get('status') != 'ready':
            self.close()
            raise RuntimeError('local_semantic_worker_failed')

    def _read(self):
        """PURPOSE: Bound waits on the local encoder and reject missing/malformed replies.
        INPUT: One outstanding worker request. OUTPUT: Parsed JSON reply, or RuntimeError.
        """
        with selectors.DefaultSelector() as selector:
            selector.register(self.process.stdout, selectors.EVENT_READ)
            if not selector.select(timeout=60):
                self.close()
                raise RuntimeError('local_semantic_worker_timeout')
        line = self.process.stdout.readline()
        if not line:
            self.close()
            raise RuntimeError('local_semantic_worker_closed')
        response = json.loads(line)
        if 'error' in response:
            raise RuntimeError('local_semantic_worker_error:' + response['error'])
        return response

    def encode(self, texts, **options):
        """PURPOSE: Batch public evidence through one isolated local model process.
        INPUT: Strings and SentenceTransformer-compatible options (fixed by the worker).
        OUTPUT: Numeric vectors; calls are serialized so concurrent requests cannot mix responses.
        """
        with self.lock:
            try:
                self.process.stdin.write(json.dumps(texts, ensure_ascii=False) + '\n')
                self.process.stdin.flush()
                return self._read()['vectors']
            except (BrokenPipeError, OSError, KeyError) as exc:
                self.close()
                raise RuntimeError('local_semantic_worker_unavailable') from exc

    def close(self):
        """PURPOSE: Reap the owned worker on shutdown or protocol failure.
        INPUT: None. OUTPUT: Terminates only this local child process; no source changes.
        """
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
        for stream in (self.process.stdin, self.process.stdout):
            if stream and not stream.closed:
                stream.close()


@lru_cache(maxsize=2)
def _load_process_encoder(python, model_name, revision):
    """PURPOSE: Reuse a local encoder worker when caller dependencies are unavailable.
    INPUT: Prepared interpreter/model identity. OUTPUT: Encoder and explicit availability/fallback audit.
    """
    identity = {'model': model_name, 'revision': revision or None, 'device': 'cpu', 'python': python}
    try:
        process = EncoderProcess(python, model_name, revision)
        lock = Path(model_name) / 'source_lock.json'
        if lock.is_file():
            identity.update(json.loads(lock.read_text()))
        return LocalSemanticEncoder(process, identity), dict(identity, status='available', backend='local_process')
    except (OSError, RuntimeError, ValueError) as exc:
        return None, dict(identity, status='unavailable', reason=type(exc).__name__,
                          fallback='bm25_and_character_cosine')


def encoder_worker(model_name, revision):
    """PURPOSE: Serve local embedding batches in the explicitly prepared dependency environment.
    INPUT: Model arguments and JSON-lines string arrays on stdin.
    OUTPUT: Ready/error/vector JSON lines on stdout; diagnostics go to stderr, never network.
    """
    try:
        with contextlib.redirect_stdout(sys.stderr):
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer(model_name, device='cpu', local_files_only=True,
                                        trust_remote_code=False, **({'revision': revision} if revision else {}))
        print(json.dumps({'status': 'ready'}), flush=True)
        for line in sys.stdin:
            try:
                texts = json.loads(line)
                if not isinstance(texts, list) or not all(isinstance(t, str) for t in texts):
                    raise ValueError('expected_string_array')
                with contextlib.redirect_stdout(sys.stderr):
                    vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=False,
                                           batch_size=32).tolist()
                print(json.dumps({'vectors': vectors}), flush=True)
            except Exception as exc:
                print(json.dumps({'error': type(exc).__name__}), flush=True)
    except Exception as exc:
        print(json.dumps({'error': type(exc).__name__}), flush=True)


if __name__ == '__main__':
    if len(sys.argv) != 4 or sys.argv[1] != '--worker':
        raise SystemExit('Expected --worker MODEL REVISION')
    encoder_worker(sys.argv[2], sys.argv[3])
