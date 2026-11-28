# Official NL2EventLog method

**Refreshed S0 v1.0.0** constructs an Event Extraction Graph (EEG), interprets one natural-language request and deterministically extracts and validates a case-centric event log from a read-only SQLite database.

- [Method specification](runtime/COMPLETE_METHODOLOGY_SPEC.md)
- [BISE Main Paper and Supplement synchronization](runtime/MANUSCRIPT_SYNCHRONIZATION_REPORT.md)
- [Executable schemas and replay input hashes](runtime/verification/)
- [Release and Method Freeze records](https://github.com/jiwonpark7913/NL2EVENTLOG/releases/tag/nl2eventlog-refreshed-s0-v1.0.0)

## Install and verify

The verified platform is CPython 3.13.9 on Linux x86-64 with SQLite 3.50.2 and JSON support. The dependency lock pins the wheels for this platform. Use a virtual environment from the checked-out repository.

~~~sh
cd method/runtime
python -m venv .venv
. .venv/bin/activate
python -m pip install --require-hashes -r requirements-lock.txt
python -m pip check
python -m src --help
python -m evaluation_harness.final_runner --help
NL2EL_SEMANTIC_MODEL=off python -m pytest -q tests \
  --ignore=tests/test_release_integration.py
~~~

The regression tests use scripted replies. The standalone command checks the release tests that need only the public tree. The full regression also uses the preserved research workspace's v4 companion, paired-runtime test dependency and development activity-policy tests.

~~~sh
research=/path/to/research-workspace
NL2EVENTLOG_COMPANION_DIR="$research/NL2EVENTLOG" NL2EL_SEMANTIC_MODEL=off \
  PYTHONPATH=".:$research/NL2EVENTLOG_v2_step2_redesign:$research/NL2EVENTLOG_v2_pi_comparison" \
  python -m pytest -q tests \
    "$research/NL2EVENTLOG_v2_step2_redesign/tests/test_paired_evaluation.py" \
    "$research/NL2EVENTLOG_v2_step2_redesign/tests/test_s3_candidate.py" \
    "$research/NL2EVENTLOG_v2_step2_redesign/development/activity_policy_v5/tests"
~~~ Tiktoken may obtain its public tokenizer asset on first use. For disconnected verification, pre-cache the tokenizer asset resolved by the pinned Tiktoken package.

The complete 36-condition replay uses the original admitted DBs, Original DDs, shared EEG snapshots and saved S0 responses. The public [replay manifest](runtime/verification/REPLAY_INPUTS.json) pins their identities. Those research inputs remain in their existing custody and the replay performs no network inference. The existing internal workspace provides the original file layout and database fingerprints.

~~~sh
python -m validation.replay_final_release --evidence-workspace /path/to/original/research-workspace
~~~

## Entry points

`python -m src` defaults to the official Refreshed S0 runtime. Supply a read-only SQLite snapshot, its Original DD, one request, a new output directory and an approved native provider budget. An optional `--eeg-snapshot` accepts a verified directory containing the EEG JSON, SQLite Index and snapshot manifest. A fresh build uses the existing query-independent cache and defaults to Haiku. The runtime records source, prompt, schema, graph, configuration and exact wire hashes.

The final evaluation runner is `python -m evaluation_harness.final_runner`. Its M3 arm uses the same release API as the CLI. Its inference path requires an approval matched to the public plan and provider cost cap. Its offline v4 log scoring reads a separate private manifest. Offline scoring and M1 Compact EEG serialization use the original companion in research custody, configured with `NL2EVENTLOG_COMPANION_DIR` and checked against the pinned v4 hash. The approved M3 runtime and the Direct SQL transport dependencies are part of the public source release. The official method is frozen separately from the evaluation and final experiment.

The method supports one analytical Case entity and at most one assigned Case per physical occurrence. Supported structural Case scopes restrict all selected events. General analytical filters, attribute enrichment and downstream process analysis are outside the extraction contract.
