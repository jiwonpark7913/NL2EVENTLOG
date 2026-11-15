# NL2EventLog — terminology and stage contracts

This is the authoritative target-method terminology. Tables, keys and references describe physical storage; Entity Types (ETs) and Entities describe business targets; Event definitions describe how occurrences can be read. Step 1 constructs a request-independent Event Extraction Graph (EEG). Step 2 interprets a request; Steps 3–4 ground and execute its extraction decisions.

## Implementation and evaluation boundary

This repository contains dataset builders, review generators, and authored reference artifacts. Updating their terminology does not implement or evaluate the complete target extraction pipeline. Existing reference labels, SQL/CSV, questions, and recorded scores retain their original meaning. Legacy table/type groups are reviewer annotations, not a newly validated semantic ET ground truth. Review manifests are excluded from model input.

## Core terminology

| Term | Meaning |
|---|---|
| Table / Row | A physical relational table / one stored record. Do not introduce a separate representation concept for a table. |
| Primary, unique, foreign key | Declared row-identity and reference constraints. Their existence does not by itself establish business meaning or entity identity. |
| Entity Type (ET) | A class of Entities sharing business meaning and instance granularity: what counts as one individual. |
| Entity | A distinguishable individual business target, such as order O1. It is not a table, key value, or stored row. |
| Key value | A stored identifier value or complete ordered composite-key tuple. |
| Entity identification rule | A validated interpretation of a table, key columns, applicable conditions and any required correspondence that identifies an Entity. |
| Identity mapping | A verified correspondence establishing that different database expressions identify the same Entity. |
| Activity | A kind of business action, such as Approved. |
| Activity value | A raw stored representation, such as A, interpreted through a validated mapping. |
| Event definition | A schema-level extraction definition combining activity meaning, source table, row condition, occurrence-time expression, occurrence identity, and evidence/status. |
| Event / Event occurrence | One actual occurrence obtained by applying an Event definition to source data. Distinct occurrences can share the same case/activity/time triple. |
| Temporal field / expression | A source column, supported column combination, or supported expression from which time can be read. |
| Time role | Occurrence, recording, or planned time, with finer roles such as start/completion where supported. |
| Event–entity attribution rule | A validated rule resolving an applicable occurrence to an individual Entity of a target ET. |
| EEG | Request-independent schema-level evidence: tables, definitions, identification and attribution rules, alternatives, and uncertainty. It does not materialize every Entity and occurrence. |

A list under consideration in Step 2 can be called **candidate Event definitions**; definitions finally selected are **selected Event definitions**. The graph node is an Event definition, not an already observed individual event. Physical source summaries that list only activity labels must not be presented as complete extracted Event definitions.

### Identity without a separate abstraction

Use `identify(t, r, k) = n`, where table `t`, row `r`, and key columns `k`, interpreted under a validated rule, identify Entity `n`. Include a required row condition or explicit correspondence in that rule. Different tables can identify the same Entity; a single table can identify or reference several ETs through different keys. Equal raw values alone do not establish identity. If an ET consistently uses one identifier convention, `(ET, key value)` can identify its Entities; otherwise resolve the source-specific interpretation or correspondence. No additional globally required identity-domain node or composite identifier component is imposed.

ET classification and instance identity are separate. Current and archived orders may share Order as their ET without sharing individual orders. A one-to-one relation between an order and invoice does not make them the same ET or Entity. A row key may also be an entity key, but record uniqueness alone does not establish that interpretation.

## Step 1 — Event Extraction Graph Construction

| Substage | Purpose and output |
|---|---|
| 1.1 Table Profiling | Inspect all tables, ordered keys, references, temporal fields and observed evidence. Keep non-temporal tables for identification and attribution. |
| 1.2 Event Definition Interpretation | In tables with supported temporal fields, interpret activities, carrier values or non-carrier evidence, row conditions, time roles and occurrence identities. Retain uncertainty and alternatives. |
| 1.3 Entity Identification | Discover what keys identify/reference; classify targets by meaning and granularity; then resolve same-Entity correspondences within ETs and build identification rules. |
| 1.4 Event–Entity Linking | Validate direct identification or supported forward FK-to-referenced-PK/unique-key routes from occurrences to Entities. Keep structural references separate from validated attribution. |

The default directional policy does not traverse a foreign key in reverse; path bounds and validation apply. A structural path is not proof of an appropriate attribution. SQL checks must preserve occurrence identity and verify single-target attribution under the declared applicable-row policy. Invalid or missing times and unresolved keys remain diagnosed, not guessed. Identity mappings and relationships between distinct Entities remain different kinds of evidence.

An Event definition records its ID, business activity, source table, carrier/value or non-carrier meaning, condition, temporal expression/role, occurrence key/discriminator, supporting evidence, and status. SQL executability, activity/time support, attribution validity, and validity of the ET's case population are separate statuses. An executable-only visualization is a filtered view; it must not discard unresolved evidence from the underlying graph. Planned and recording times may remain as evidence but are not automatically emitted as occurrence times.

## Step 2 — Process Interpretation

The output is **Process Information (PI), `I_q`**, not an event log or SQL. It fixes the case notion, request mode, any process focus, and selected Event definition IDs.

### Request parsing

Parse the original request once by default. Extract:

- `request_mode`: explicit or implicit;
- `case_requirement`: the analysis-unit wording and its original text span, or null when unspecified;
- `activity_requirements`: activities actually named by the user;
- `process_focus`: an additional business-process restriction such as production or delivery, with its source span, or null.

Do not invent ET IDs or activity lists without EEG evidence. There is no mandatory second parsing-review call. The parsed result is a fallible checklist, not the answer key. The original request guides initial case/definition selection and all later checks.

### Case notion and candidate retrieval

Compare the original wording with the EEG ET catalog, including meaning, instance granularity and validated identification rules. Explicit grouping such as “for each order” takes precedence over a process word such as “delivery.” If needed, examine multiple ET interpretations and select one validated interpretation; do not union their cases or selections into a composite case.

For ET `tau`, define `D(tau)` as all supported Event definitions with validated attribution to that ET. Simple graph adjacency is insufficient. Collect definitions across all eligible physical sources rather than limiting selection to the ET's principal source table.

| Request | Selection policy |
|---|---|
| Explicit | Match the activities requested in the original text to supported attributable definitions; preserve any explicit restrictions. |
| Implicit, no process focus | Include all of `D(tau)` deterministically; no activity-by-activity LLM selection. |
| Implicit, with process focus | Use the original text and EEG meanings/source evidence to select the definitions in `D(tau)` matching that focus. |

Examples: “each order's approval and delivery completion” is explicit; “each order's entire history” is implicit without focus; “each order's production process” is implicit with production focus. “For each shipment” selects the grouping unit Shipment, not automatically an additional delivery-only focus.

A process focus restricts Event definitions, not the case Entity population. Do not filter whole ETs or tables as a substitute for definition-level selection. No separate target-method classification into own/desc/expanded is used, and no request-independent lifecycle-membership gate is required. Request-specific focus selection still requires semantic evidence; it is not claimed to be fully deterministic or error-free.

### Review, expansion, revision and finalization

Compare the original request, parsed requirements, selected ET, selected definitions and EEG evidence. Check case-unit agreement, requested coverage, over-selection, IDs, activity/time support, attribution and conflicts. Do not remove an event just because parsing omitted its requirement, or add an event to satisfy an unsupported parsed requirement.

Existing bounded revision can add/remove/replace definitions or reconsider the case notion. Targeted expansion may search the **entire EEG**, but a definition can be added to the current interpretation only with validated attribution to its selected ET. Changing ET rebuilds the candidate set and selection. Implicit-without-focus must again include the full supported attributable set after an ET change. Use bounded budgets and repeated-state detection; do not introduce an unlimited parsing rewrite loop. A comparator selects one validated interpretation unchanged or returns unresolved. Database unanswerability is not established merely by an unsuccessful model interpretation.

## Cases and their identifiers

| Term | Meaning |
|---|---|
| Case notion | The chosen ET whose Entities form the analysis units. |
| Case | An individual Entity in its role as an analysis unit under that case notion. |
| Case population | All identifiable Entities of the selected ET under the validated identification rules; no request-specific case filter in the current scope. |
| Case ID | A collision-free serialization of the case's resolved Entity identity. It need not equal a single table PK. |
| Trace | The ordered occurrence history attributed to one case. |

Multiple representations of the same Entity create one case. Selecting activities or a process focus does not reduce the case population; a case with no selected occurrence remains in the population although it contributes no event-row CSV record. Preserve complete composite keys and prevent collisions between source-specific identifiers without requiring an additional public identity concept.

## Step 3 — Extraction Specification and SQL Generation

**Extraction Specification (ES)** grounds frozen PI into case identification, Event Sources, Activity Rules, validated attribution routes, temporal expressions, occurrence identities and execution policies for nulls, multiplicity and deduplication. These physical decisions are inspectable before deterministic template-based SQL generation. The LLM does not freely author extraction SQL. Event definitions in the EEG and request-specific Event Sources/Activity Rules in ES are related but not interchangeable objects.

## Step 4 — Verification and Repair

Verify ES, SQL execution and log diagnostics. Existing supported physical alternatives may repair extraction rules without silently changing the frozen case notion, requested focus, definition selection, entity identity or case population. Changes to those semantic decisions require an explicit interpretation revision. Passing structural/execution checks does not establish semantic correctness. The exact available repair operators depend on the actual implementation and must not be inferred from this terminology update.

## Legacy artifacts and external vocabulary

Legacy reference schemas can retain fields such as `ot`, `object_type`, old view scopes and author-assigned table groups. This documentation does not reinterpret or regenerate those answers. Ordinary ERD terminology and object-centric terminology in cited external work remain valid. `tools/migrate_eeg_terminology.py` updates presentation and reviewer manifests only; its file name is retained for workflow compatibility. New reviewer manifests are versioned and must not be supplied as model inputs or mistaken for runtime implementation results.
