# NL2EventLog Methodology — Entity Model and Event Extraction Graph

## Scope and migration status

NL2EventLog translates a natural-language process request and a relational database into an event log by separating **What** (process interpretation) from **How** (deterministic extraction). The methodology uses an **Event Extraction Graph (EEG)**, which is a *request-independent, schema-level* representation of candidate events, physical source bindings, entity descriptions and evidence for case attribution. **EEG is not an Event Knowledge Graph (EKG)** containing all concrete event/entity instances.

This document specifies the **target methodology**. The four existing datasets and their current SQL/CSV Gold logs predate the Entity Type / Identity Namespace redesign. Their existing author-assigned Object Type groups are *legacy evaluation annotations*, not independently validated Gold ET groupings. Updated review diagrams use ET/ER terminology to describe their **existing table membership projection**, but this does not establish that namespace-aware case populations or directional attribution have been implemented. Database content, questions and existing Gold event logs are unchanged by this documentation migration.

**Entity storage clarification:** ETs classify identified business targets, not whole tables. A table may identify/reference multiple ETs and a single entity may have several physical identifiers. See the [definitions and partial-function model](ENTITY_IDENTITY_AND_STORAGE.md) and [live dataset cases](../../datasets/ENTITY_STORAGE_CASES.md). WarehouseFlow now includes optional worker attributes under an alternate identifier; existing event-log Gold is unchanged.

## Glossary

| Term | Meaning |
|---|---|
| **Entity Type (ET)** | A class of business entities sharing business meaning and instance granularity; one ET may span multiple physical representations and identity namespaces |
| **Entity Representation (ER)** | Schema-level representation of one physical relational table containing information about entities; every physical table has one ER node, which does not impose one ET per table |
| **Entity / Entity Instance** | An individually identifiable entity of an ET |
| **Identity Namespace** | Technical identity domain within an ET, enabling shared, mapped, independent or unknown cross-ER identity relationships |
| **Event Extraction Graph (EEG)** | Request-independent graph of candidate activities, ER/ET structure, physical event bindings, semantic evidence and candidate case-attribution contracts |
| **Case Notion** | Analyst-chosen ET and case interpretation for a request, with each validated ET instance becoming a case |
| **Case Attribution Path** | Verified route mapping source event occurrences to target ET instances, respecting permitted relational links |
| **Lifecycle Membership** | Separate semantic determination of whether an attributable event belongs to the target entity lifecycle |
| **Extraction Specification (ES)** | Executable contract for deterministic event-log extraction from a resolved process interpretation |

Legacy terminology: **Evidence Graph (EG) → EEG**, **Object Type (OT) → ET** *in the methodology*; **Object (Table) → ER**; **Object Linking → Entity Type Identification and Entity Linking**; **Case Linking Path → Case Attribution Path**. The words “object” and “object type” remain valid where citing external process-mining or OCEL terminology, or naming legacy dataset fields explicitly.

## Step 1: Request-independent EEG

**Temporal Screening → Event Interpretation → Selective LLM Review → Entity Type Identification → Entity Linking**

### Entity Type Identification

1. Keep every physical table as a source node. Enumerate PK, UNIQUE and FK candidates, preserving complete composite tuples. For each candidate determine the target it identifies or references; a table may have multiple such interpretations.
2. **Semantic type classification:** classify identifier interpretations by business meaning and instance granularity using definitions, the Data Dictionary, schema and business semantics. One table may describe a Registration and reference a Student and a Course. Interpretations can share an ET **without sharing actual instances**; do not group whole tables as the only operation.
3. **Instance identity resolution:** classify the relationship between instance identifiers *separately* from semantic ET membership. Validate primary/unique key meanings, structural relationships, domain evidence and actual data.
4. Record an **Identity Namespace** for every resolution domain:
   - **Shared** — normalized canonical key denotes the same instance across ERs.
   - **Mapped** — a verified explicit mapping normalizes distinct physical keys to the same instance.
   - **Independent** — separate identifiers denote separate instances even when ERs share an ET.
   - **Unknown** — evidence is insufficient; do not merge instances.
5. Apply deterministic validation to LLM-proposed ET merges/splits; perform ET naming after resolution. Do not generate arbitrary SQL, key transformations or mappings in the semantic reviewer.

Conceptual identity: `Entity ID = (Entity Type, Identity Namespace, Canonical Key)`.

**Key equality, key inequality, and FK existence alone do not prove an identity relationship.** Namespace is not a business concept. Group count (including 5–10 ETs) is not a hard constraint. Preserve ERs whose identity is unresolved, but do not automatically make them selectable case populations.

### Entity Linking

Attach an event candidate to its recorded **source ER**. For additional cross-ER case attribution, traverse only validated **FK → referenced PK/unique-key** links by default. Reverse FK traversal is disallowed in the baseline policy, including in multi-hop paths. Verified identity mappings *within the same ET* are distinct from inter-ET case attribution.

Keep three independent annotations:
- **Structural Reference:** physical/legal relational path.
- **Case Attribution:** verified mapping from event occurrence to target entity instance.
- **Lifecycle Membership:** business evidence that the event belongs to that entity's process.

A structural path alone does **not** establish lifecycle membership. Restricting to FK→PK may remove previously linked Gold events, so measure its effect on support coverage and recall before changing benchmark truth.

The EEG stores contracts and source-level bindings, **not one concrete EEG node per entity instance**.

## Step 2: Iterative Process Interpretation (What)

**Initial Mapping → Semantic Coverage Review → Targeted Candidate Expansion → Joint Reassessment**.

Select a **target ET** as the Case Notion; the cases are its validated Entity Instances. Explicit requests name activities to retrieve, including supported activities recorded in other ERs with verified attribution. Implicit requests ask for the ET's recorded lifecycle without enumerating activities:

- **own:** eligible events whose source-row identity interpretation resolves the selected ET as the event's own target; a table-wide type label alone is insufficient.
- **desc:** own plus supported events from related ERs where the directional Case Attribution Path and Lifecycle Membership are both validated.

Unresolved candidates and mere FK reachability are not automatically included. Process Information is frozen after Step 2.

## Step 3: Extraction Specification and deterministic SQL (How)

`ES_q = (I_q, b_κ, S, R, Δ)`

| Component | Contract |
|---|---|
| `I_q` | Target ET, requested activities, explicit/implicit mode and scope |
| `b_κ` | ET identity namespaces, instance mapping and verified case-population contract |
| `S` | Event source bindings and case-attribution routes |
| `R` | Activity interpretation, timestamp/carrier rules and supporting evidence |
| `Δ` | NULL behavior, multiplicity, occurrence deduplication and execution policy |

**Case Population(ET)** is the distinct union of validated canonical entity instance mappings across approved table/column/condition interpretations. Shared identities collapse to a single case; independent namespaces remain disjoint; unknown mappings are not silently unified. **Case union is not event-occurrence union**: preserve distinct recorded events and deduplicate only according to an explicit event-ID/occurrence policy.

SQL is compiled deterministically from the validated ES. The LLM does not freely author execution SQL.

## Step 4: Verification and repair

Check the consistency and executable behavior of ES and generated SQL **without changing Step 2's settled Process Information**. This includes schema/column existence, namespace/key mapping validity, directional case-attribution bindings, cardinalities, NULL handling and deduplication. Recoverable extraction errors may be repaired only inside the permitted ES/execution boundary. Semantic changes to selected ET, scope or activities require a new explicit interpretation cycle, not implicit post-hoc repair.

The exact Step 4 repair operators and acceptance tests require alignment with the current implementation. This document does not claim that the target behavior is already implemented.

## Evaluation and provenance boundary

- **Model-visible evidence:** SQLite database and Data Dictionary; supply the question separately.
- **Gold/reviewer-only:** author-assigned entity identity, event-source manifest, question-level SQL/CSV, DFGs and review graphics.
- Existing Gold SQLs are executed and checked against their Gold CSVs, but this proves **internal consistency, not semantic ET correctness, namespace coverage or FK→PK recall**.
- Re-annotate cross-ER same-ET identity namespaces, cases and process membership before evaluating the target method. Distinguish published *legacy Gold* from future *ET Gold* until that review is complete.
- The ET/ER diagrams in the present dataset reviews are an **author-labeled source-level projection**, not an EEG inferred by the model.

## References

- Esser & Fahland (2021), *Multi-Dimensional Event Data in Graph Databases*.
- Fahland (2022), *Process Mining over Multiple Behavioral Dimensions with Event Knowledge Graphs*.
