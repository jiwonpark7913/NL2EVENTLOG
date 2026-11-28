# NL2EventLog Final Method Freeze

**Refreshed S0 v1.0.0 is the final NL2EventLog method.** The release tag `nl2eventlog-refreshed-s0-v1.0.0` points to the exact verified GitHub revision `9429fd6e850894abce89e8970363a39005a2f94f`. The freeze documents record this source revision. The release assets carry the freeze manifest and verification evidence. [Verified source](https://github.com/jiwonpark7913/NL2EVENTLOG/tree/9429fd6e850894abce89e8970363a39005a2f94f/method) · [GitHub release](https://github.com/jiwonpark7913/NL2EVENTLOG/releases/tag/nl2eventlog-refreshed-s0-v1.0.0) · [Freeze manifest](FINAL_METHOD_FREEZE.json)

The released method constructs reusable EEG knowledge, runs request-only Intent followed by Case/scope and Event/attribution selection, and produces a log through Scoped Union, ESpec, deterministic SQLite compilation and read-only integrity validation. The default CLI and paper arm M3 invoke the same Refreshed S0 API. The release preserves the selected method's behavior. Promotion and standalone packaging affect release identity and dependency location.

| Frozen setting | Contract |
| --- | --- |
| Stage 1 EEG construction | Claude Haiku 5.5 `claude-haiku-5-5`, adaptive thinking and medium effort, with the recorded `DbuConfig`. Construction is independent of test requests. |
| Stage 2 PI | Claude Haiku 5.5 adaptive/medium or Gemini 3.5 Flash-Lite `gemini-3.5-flash-lite` with MINIMAL thinking and temperature 0. Both paths use the frozen three-role PI contract and identical Case-conditioned delivery. |
| Stage 3 | Bound PI, typed Case population, Scoped Union and versioned ESpec v6. Read-only SQLite extraction and integrity checks preserve occurrence identity, attribution and multiplicity. |
| Verified platform | CPython 3.13.9, SQLite 3.50.2, Linux x86-64. The checked dependency lock fixes installed package versions and wheel hashes. |
| Research scope | One read-only relational snapshot, its Original DD and one request. One analytical Case notion and up to one assigned Case per physical occurrence. Supported structural scope is applied jointly to the selected events. |

General analytical filtering and downstream process analysis are outside the research scope. Early Case commitment, EEG evidence quality, native-model behavior and complete delivery within context limits constrain the method. Existing evidence is limited to the measured development panel. See the [method specification](COMPLETE_METHODOLOGY_SPEC.md), [known limitations](ASSUMPTIONS_AND_LIMITATIONS.md) and [runtime contracts](verification/METHOD_CONTRACTS.json).

The release ships the common evaluation runner and its active generation transports. Offline v4 scoring and M1 Compact EEG serialization use the original hash-verified companion in research custody. This Method Freeze covers the approved runtime and retains historical Evaluation v4 and v5-dev. Final evaluation policy, adjudication, benchmark registration and budgets remain separately governed. The existing GitHub data, documentation and review-tool trees match the prior revision. The archived replay inputs and Independent Audit ZIP remain in their existing custody.
