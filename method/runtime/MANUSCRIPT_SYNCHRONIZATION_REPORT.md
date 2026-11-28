# BISE v46 methodology synchronization

The Main Paper and Supplement should use the same three-stage architecture and the same runtime contracts. The final method is **Refreshed S0 v1.0.0**. Cite the method release tag and the pinned source revision from its Method Freeze manifest. The numerical evidence below describes development data and the recorded model configurations. The default CLI and paper arm M3 use the same released runtime.

## Core contributions and narrative

1. **End-to-End Automation of Event Log Extraction from Relational Databases.** Given an Original Data Dictionary, a relational snapshot and a supported natural-language process-analysis request, the method reuses database-specific extraction evidence to produce an event log. Connect independently constructed knowledge to constrained interpretation, executable specification and output integrity.
2. **Definition and Domain-independent Automatic Construction of the Event Extraction Graph.** Define the EEG as a process-specific knowledge structure combining semantics and executable rules. Entity meaning and grain connect to typed identity and physical representation. Activity and temporal meaning connect to source predicates and timestamp bindings. Business attribution roles connect to executable Case mappings and join paths. Domain-independent construction describes the shared procedure, whose evidence inputs and completeness vary by domain.

Use Ontology, Mapping and VKG as Related Work and conceptual context. The EEG is a single implemented structure. Its process-semantics and execution-rule views describe the information in the graph and its links. Keep the case and Event role count in the implementation and experimental discussion. The central research claim is the design and use of reusable extraction knowledge.

## Main Paper and Figure

| Stage | Input | Responsible operations | Output |
| --- | --- | --- | --- |
| 1. EEG Construction | Relational snapshot and Original DD | Profile tables, qualify carriers and clocks, validate entity grain, occurrence identities, relationship paths and extraction evidence. Evidence-scoped construction corrections occur here. | Versioned EEG and SQLite Index |
| 2. Process Interpretation | Original request and reusable EEG/Index | Run separate request-only Intent, Case/scope, and Event/attribution roles. The Case and Event roles receive both the original request and Intent. Deterministically bind exact references, apply Case scope and qualify the joint assignment. | Bound PI or explicit terminal decision |
| 3. Event Log Extraction | Bound PI, executable dependency closure and database | Materialize ESpec, compile read-only SQL, execute against the typed Case population and validate provenance, occurrence identity and output multiplicity. | Validated event log or failed extraction |

Draw the complete population-based Case Catalog before the selected-Case detailed lookup. Commit one ET and optional structural scope. Show the Event view with all eligible connected EDs, attribution candidates and existing documentary and relationship review evidence. Place SQL generation, execution and integrity validation inside Stage 3. The stage layout has three boxes and a Stage 1-to-Stage 2 EEG input.

## Supplement contracts and validation

- Show real role inputs and schemas, the Case card, the eligible graph projection, and observed role responses. Case cards carry ID, name, grain, definition, populations and scope. The Event role receives full selected-Case ED/path evidence including cross-entity occurrences and role review. State which intermediate fields travel downstream.
- Bound PI contains one canonical Case, any structural Case scope, one or more selected ED/path options for the same Case, and activity mode. The compiler uses the same typed Case population used to validate the scoped assignments. ESpec pins keys, predicates, clocks, filters, validated maps and output shape. Repeat assignment paths to the same occurrence and Case collapse, and distinct witnessed occurrences remain.
- Scope filters the included population. An Event-specific role can still determine a distinct assignment. Explain the scoped union checks and the unresolved terminal result when a physical occurrence maps to multiple in-scope Cases. Multiple EDs and multiple relationship roles are supported within this single-Case-per-occurrence contract.
- Construction checks, Stage 2 exact binding and Stage 3 integrity checks have distinct responsibilities. The current basic path comprises the three stages above. Independent Verification, Targeted Recovery, repeated Semantic Revision, and global or post-execution repair belong to historical comparisons.
- General analytical filtering over date, numeric or arbitrary attribute predicates, attribute enrichment and downstream process analysis are outside the extraction contract. Detailed prompt, schema and source links are in the audit package. Low-volume fixtures establish feasibility examples; early Case commitment, missed events or roles, incomplete DD coverage, and complete delivery at larger scale remain limitations.

## Evaluation questions for the Main Paper and Supplement

- **EQ1 — End-to-End Effectiveness.** M3 versus M0 measures extraction accuracy, completion, efficiency and scalability.
- **EQ2 — EEG Construction and Contribution.** Assess automatically constructed ET, ED and attribution correctness and coverage. Use M1 versus M0 to measure the contribution of providing the EEG. Record build, reuse and per-request costs.
- **EQ3 — What–How Separation.** Test supplying explicit PI with M2 versus M0 and compare M3 and M2 on the same PI. Use a fixed-ESpec LLM-versus-deterministic comparison for SQL generation and stage diagnostics to localize errors. PI correctness is one diagnostic.

The approved methodology leaves the final comparison groups, cohorts, metrics and paid budget to a separate evaluation registration. Keep the three original evaluation questions and tie each claim to a registered comparison.

## Verified evidence and pending decisions

The fresh matched campaign scored 72/72 conditions. S0 and S3 achieved Physical Exact 34/36 and 25/36, Semantic Exact v4 12/36 and 6/36, and Semantic Exact v5-dev 34/36 and 25/36. Completion was 35/36 and 30/36. Logical calls were 107 and 67. Mean end-to-end seconds were 15.12 and 10.47. Combined request cost was USD 0.1739602 from native usage; Gemini uses the frozen paid-list equivalent. Each pair supplies one response sequence per arm and model. No graph was rebuilt.

The paired fresh S0/S3 comparison removes both the separate Intent call and use of its text. The earlier S0/S2 contrast couples joint Intent–Case selection with an activity-aware catalog and is reported separately. The second independent human Activity Equivalence adjudication is pending. The manuscript can report the observed development evidence with sample sizes and scoring versions. Final Evaluation Freeze, Held-out estimates, and a final Direct LLM benchmark remain pending.

[Complete specification](COMPLETE_METHODOLOGY_SPEC.md) · [Exact Stage 2 contracts](verification/INPUT_CONTRACTS.json) · [Pinned replay inputs](verification/REPLAY_INPUTS.json) · [Release and Freeze evidence](https://github.com/jiwonpark7913/NL2EVENTLOG/releases/tag/nl2eventlog-refreshed-s0-v1.0.0)
