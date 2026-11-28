# Release verification report

The deployed source was downloaded into a new checkout from GitHub at `9429fd6e850894abce89e8970363a39005a2f94f`. The staged public SHA-256 payload matched the downloaded files. Git tree object IDs were unchanged for datasets, tools, docs, tests, workflows and the original airline release support tree. The source release adds a method subtree and a repository README link. [Remote source](https://github.com/jiwonpark7913/NL2EVENTLOG/tree/9429fd6e850894abce89e8970363a39005a2f94f/method)

## Installation and isolation

CPython 3.13.9 and SQLite 3.50.2 were verified in a fresh virtual environment installed from the locked wheels. `pip check` reported no broken dependencies and SQLite JSON support passed. The release API, native adapter and final runner resolved from the downloaded tree. Both command-line entry points opened successfully. The test environment omitted provider credentials and used a Python TCP socket block. Provider calls and API cost were zero. [Environment evidence](verification/RELEASE_ENVIRONMENT.json)

The public runtime tree does not carry historical raw responses, EEG snapshots, evaluator-only labels or the full archived scorer/runtime trees. Full regression uses the existing hash-pinned v4 companion and historical paired-test modules from research custody. Those inputs are separate from the public release and its inference path.

## Verified behavior

| Check | Result |
| --- | --- |
| Default CLI and paper arm M3 | Default Refreshed S0 routing was verified with scripted replies. The M3 runner and the release API use the same Refreshed S0 entry point. |
| Original S0 replay | **36/36** conditions reproduced on their exact original EEG and SQLite Index. Development, release and M3 matched on Bound PI, whole ESpec, SQL, rows, terminal status and flags. Elapsed-time instrumentation is excluded. |
| Terminal and role behavior | **35 accepted and one unresolved** outcome preserved. The 107 recorded roles comprised 36 Intent, 36 Case and 35 Event. |
| EEG reuse and fresh construction | Pinned prior snapshots were read and verified. Scripted Stage 1 checks exercised a new build, disk reuse and rejection of a mismatched Original DD. |
| Legacy and evaluator isolation | Tripwires prohibited legacy interpretation, targeted recovery and Global Repair during replay. Fixture tests checked that private reference paths were rejected during inference and that offline scoring used a separate process. |
| Standalone public regressions | **142 tests and 23 subtests** passed using the downloaded tree and locked environment only. |
| Full regression | **155 tests and 23 subtests** passed in the same clean environment with the existing compatibility and evaluator fixtures. It includes all four release-integration tests. |

[Condition-level equivalence](verification/OFFLINE_EQUIVALENCE.json) · [Pinned original replay inputs](verification/REPLAY_INPUTS.json) · [Method Freeze manifest](FINAL_METHOD_FREEZE.json)
