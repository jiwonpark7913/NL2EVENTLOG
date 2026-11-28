# Complete NL2EventLog methodology specification

## Exact research problem

Automatically extract a process-specific event log from a relational database, its Original Data Dictionary (DD) and a natural-language request. The method builds reusable database-level extraction knowledge, resolves the requested analytical perspective into exact evidence identifiers, and deterministically generates and validates the resulting event log. The approved method is **Refreshed S0**, method identifier `nl2eventlog-refreshed-s0-v1.0.0`. The default CLI `python -m src` and paper evaluation arm M3 both use `src.release_runtime.run_release`, which delegates to the validated three-call S0 implementation. [Official runtime](src/release_runtime.py) · [CLI](src/__main__.py) · [Evaluation runner](evaluation_harness/final_runner.py)

| Interface | Operational contract |
| --- | --- |
| Database | An inspectable, read-only SQLite snapshot with schemas, typed values and source records. SQLite is the tested backend. |
| Original DD | General-purpose descriptions of business meaning, record roles, encodings, columns, timestamps and relationships. Coverage can be incomplete. The DD contains no evaluation answers as runtime authority. |
| Request | Original natural-language description of the Case perspective, activities or lifecycle, and any supported process-specific roles. One request yields one analytical Case Entity Type (ET). |
| Readable result | A Bound PI and, when executable, ESpec, deterministic SQL, ordered provenance-bearing event rows and validation diagnostics. Unknown evidence, invalid binding and failed execution remain explicit. An accepted zero-event result has a distinct status. |

A structural Case Scope can narrow a documented process-role population. Arbitrary date ranges, numeric thresholds, attribute cohorts, analytical predicates, attribute enrichment and downstream process analysis are outside the research task. One Case ET can admit occurrences from other ETs and tables and multiple roles across different events. Each physical occurrence has at most one Case assignment in the current log. [Population contract](src/common/entity_population.py)

The proposed automation contribution has two parts. The system connects the source to a verified event log end to end. It also automatically constructs a reusable Event Extraction Graph that combines process semantics and executable rules, using domain-independent construction mechanisms applied to domain-specific evidence. Ontology, Mapping and VKG provide conceptual context for discussing this single implemented graph. [EEG Index contract](src/eeg/eeg_store.py)

## Stage 1 · Construct reusable EEG

**Purpose.** Establish reusable entity and occurrence facts before any request. **Inputs.** Public DB, Original DD and DbuConfig. **Outputs.** Versioned EEG JSON and a SQLite Index. Its inputs are independent of requests and evaluation.

1. Profile declared keys/constraints, bounded values, temporal and carrier candidates. Interpret business sources, conditions, actual clocks and occurrence identities using reusable evidence. Optional configured model review addresses semantic ambiguity in construction.
2. Build and validate business ET representations, grain and typed populations. Derive EDs with canonical labels, source predicates, admitted occurrence clocks and identity contracts.
3. Enumerate finite simple attribution paths through admitted relationships. Validate shape, cardinality, endpoint, source-to-Case map and available role evidence. Preserve physical validation and grounded business review separately. Retain unresolved candidates and their evidence.
4. Apply any configured bounded, evidence-scoped construction correction before publishing the graph. Freeze snapshot/DB identity and write normalized Index relations and provenance. The verified construction configuration uses Claude Haiku 5.5 with adaptive thinking and medium effort. The measured inference configurations use that same Haiku setting or Gemini 3.5 Flash-Lite with MINIMAL thinking and temperature 0. Both providers reused the same Haiku-built graphs and Indexes. [Construction and inference contracts](verification/METHOD_CONTRACTS.json)

Default probes are bounded and thresholds are empirical settings. The executable snapshot defines eligible worlds for later interpretation. [Builder](src/step1_understand/pipeline.py) · [Configuration](src/step1_understand/eeg_configuration.py)

## Stage 2 · Process interpretation and scoped binding

**Purpose.** Use the original request and EEG to decide the Case perspective and event-to-Case assignments. **Output.** One Bound PI or a precise unresolved/failed result.

1. **Request Interpretation.** Read only the original request. Return objective, case_intent, activity_intent and activity_mode. The two selectors receive the structured Intent and original request. The three prose fields persist in ESpec V_q provenance.
2. **Case and Scope Selection.** Use the original request, Intent and complete population Case Catalog to select the Case ET and optional scope or report insufficient evidence. Commit one eligible Case before the detailed lookup.
3. **Event and Attribution Selection.** Use the original request, Intent, committed Case and scope, and the full eligible Event view to choose exact ED/path pairs or report insufficient evidence. Bind the selected pairs and use the Intent activity mode in the Bound PI.

At Case commitment, validate one ET and one optional scope against the complete population-only catalog. Applicable activity names and path capabilities are delivered after that decision, so there can be an information loss when Case selection requires detailed activity reachability. Once a Case is selected, index its complete eligible ED and attribution closure. Admission uses the deterministic graph and physical eligibility rules. Documentary review contributes evidence to the model. Events can come from other entities when their EDs have a qualified path. Raw execution join maps and SQL stay local. [Input contracts](verification/INPUT_CONTRACTS.json) · [Response schemas](verification/STEP2_RESPONSE_SCHEMAS.json)

Resolve returned ED–path pairs to exact offered IDs. Validate selected population, Case namespace/key, ED occurrence identity and clock, source definitions/predicates, exact path eligibility and physical dependency hashes. Unknown IDs, a mismatched Case/scope, empty Event selection, and missing dependencies stop before SQL. A model refusal or unusable schema/transport response is retained separately. The terminal handling belongs to the current stage.

### Scoped assignment proof

The path tells which Case receives each occurrence. The Case Scope tells which instances of the selected ET may appear. A Case population predicate can make a valid direct path sufficient, while an event-specific relationship still requires the appropriate path. For an ED with multiple paths the runtime verifies each path's local structure, status, coverage and typed assignment before composition. In the same read-only transaction, it reads the compiler's typed Case population CTE and intersects each proved occurrence–Case pair set. It checks shared assignments and conflicts after applying that restriction. A Case outside the population cannot create an in-scope collision.

Identical assignments count once. Equal path sets can collapse to one retained branch with the proof recorded. A functional union can retain some shared or disjoint assignments using its snapshot-bound certificate. A remaining unsupported conflict fails closed. An authorized documented multi-role assignment to different Cases is reported as documented_multiple_case_assignments_unsupported under the single-Case-per-occurrence policy. Distinct EDs and occurrences can use different roles. [Exact scoped proof](development/s2/scoped_union.py) · [Common binding](development/s2/extraction.py)

## Stage 3 · Deterministic extraction and publication

**Purpose.** Implement the Bound PI with an executable program that preserves selected occurrence and assignment semantics. **Inputs.** Bound PI, physical graph closure, read-only DB. **Outputs.** ESpec v6, deterministic SQL, validated event log and diagnostics or failure.

1. Materialize ESpec with the selected Case type, typed identity and population, exact event rules and source groups, carrier filters, selected clock, keys, occurrence identifiers, path decisions and canonical labels. Validate ESpec structure, selected IDs and hashes, physical references and graph eligibility. Compatibility code can read earlier ESpec versions. The benchmark evaluator version is independent of the ESpec version.
2. Generate an SQL Case population CTE, deterministic source branches and validated joins. Filter occurrence assignments through the typed Case population. Compile identity-conflict diagnostics and the log. Repeated projections of the same bound occurrence and Case collapse. Independently identified records with the same Case, activity and timestamp remain distinct.
3. Keep compilation and read-only execution tied to the validated DB snapshot. Source witnesses recompute live key, conditioned timestamp/predicate, coverage and cardinality information. Verify references, clocks, scope, collisions, null requirements and output identity. Check the snapshot before and after extraction.
4. Publish SQL and rows only with the required check states and no hard diagnostic violation. Preserve failure reasons and structural diagnostics. The legacy reason strings not_needed, needs_step2_revision and repair_unresolved are reporting states for this stage. Singleton cases, ties, rework and activity frequencies are observational. They do not cause a repair, rule replacement or relabeling.

The validator preserves named four-state checks (pass, fail, unknown, not_run). It compares the entity population contract and live keys, selected binding evidence, frozen PI, occurrence granularity, ESpec static/data/semantic contracts, physical IDs, and binding clocks. Full execution additionally requires live_keys, live_attribution, timestamp_population_and_predicates, sql_execution and event_collision_and_deduplication to pass. The semantics of the intended timestamp are inherited from Stage 2 and explicitly recorded as unknown to the deterministic validator. Binding hash conflicts, missing source tables/columns, unverified relational predicate joins, invalid namespaces or key columns, and attribution relationship defects have separate structural issues. Some check names and reason strings remain for backward-compatible receipts. The runtime does not dispatch on a repair hint.

The active runtime has one Stage 3 verification/extraction pass and no global repair search, independent semantic review or cross-stage revision. It performs deterministic exact binding and deduplication and never chooses an alternative clock, role or activity after execution. Stage 1's construction-local corrections are separate. [Full validator](src/common/validate_extraction_contract.py) · [ESpec materialization](src/step3_execute/materialize_extraction_specification.py) · [SQL compiler](src/step3_execute/compile_event_log_sql.py)

The exact ordered output schema is case_id, event_id, activity, activity_original, source_event_definition_id, source_occurrence_id, timestamp, timestamp_kind, timestamp_raw_value, timestamp_raw_column, timestamp_json_path, timestamp_day, timestamp_day_column, timestamp_clock, timestamp_clock_column, timestamp_clock_encoding, timestamp_timezone, source_table, source_record_id and object_refs. The compiler orders the projected rows by case_id, timestamp and event_id. Provenance identifies the source clock, typed occurrence and Case assignment for each record.

## Evidence, reproduction and external validity

All development grades follow offline v4/v5-dev. References never enter the inference or EEG construction environment. Report final exactness and event-level scores separately from physical provenance, retrieval, PI, Case, ED and path facets. The audit includes full representative JSON wires, exact configuration/source hashes and the executable model adapters. [Pinned replay inputs](verification/REPLAY_INPUTS.json) · [Independent offline scoring](evaluation_harness/final_worker.py) · [Limitations](ASSUMPTIONS_AND_LIMITATIONS.md) · [Method Freeze release](https://github.com/jiwonpark7913/NL2EVENTLOG/releases/tag/nl2eventlog-refreshed-s0-v1.0.0)
