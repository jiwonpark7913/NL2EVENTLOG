# Step 4 — Evidence-grounded Verification and Repair

## Status and boundary

This is a revised method design grounded in the 2026-11-20 author audit. The reference-audit tools are implemented. A general automatic runtime repair engine covering every operation below is not claimed to be implemented or validated. Earlier negative process-guided repair results are not superseded by this authoring exercise.

Step 4 checks ESpec and its executed log against fixed Process Information, EEG evidence and source rows. It preserves the user's case notion, process focus and activity scope. Revising an interpretation belongs to Step 2; replacing a weak benchmark request belongs to authoring. A singleton-only reference request can be correctly extracted yet unsuitable for testing multi-event process interpretation.

## Verification and repair protocol

1. **Validate structure and execution:** EEG IDs, columns/types, actual versus planned/maintenance timestamp roles, occurrence identity, admissible attribution paths, SQL compilation/execution, output fields and case membership. Preserve failed drafts and failure witnesses.
2. **Diagnose the extracted log:** events per case, singleton/empty-case rates, activity coverage, repeated occurrences, duplicate identities, cases per occurrence, temporal ties and DFG relations. Distinguish singleton traces from isolated activity nodes. A DFG is an ordered projection, not a causal model.
3. **Form a testable error hypothesis:** e.g. row ID used instead of business entity ID, omitted path, excluded recorded completion, unrelated source branch, or fan-out from a join. A diagnostic signal is not a correctness judgment.
4. **Verify with evidence:** trace events to source keys, row predicates, timestamp fields and case paths; inspect EEG-supported residual candidates within the fixed process scope. Distinguish a recorded, relevant occurrence lost by extraction from an unrecorded occurrence, unrelated occurrence or ambiguous interpretation.
5. **Apply a bounded, typed ESpec patch:** change only an evidence-supported timestamp choice, predicate, identity expression or attribution path, preserving semantic activity labels and Process Information. If evidence discovery is required, validate new evidence before using it. Do not invent unrestricted SQL alternatives to force a better-looking process.
6. **Recompile, re-execute, revalidate:** verify affected source witnesses and counts; reject unsupported additions, loss of supported occurrences, collapse of legitimate repeats and interpretation changes. Terminate with accepted, unresolved or budget exhausted. Keep before/after decisions and evidence.

## Decision rules

| Observation | Evidence to inspect | Decision |
|---|---|---|
| All cases have one event | Atomic case requested, or wrong case identity selected? | Retain valid atomic cases. Repair a wrong ESpec identity only with validated alternatives. Authoring may replace a weak benchmark request. |
| Start without completion | Is the same occurrence's actual completion field NULL? | Retain legitimate partial traces; add only an actually recorded, relevant completion omitted by extraction. |
| Activity absent from log | Are there relevant source occurrences attributable to this case? | Zero recorded occurrences is not under-extraction. Otherwise localize the predicate, timestamp or path that lost them. |
| Dense/reversing DFG | Shared resource case, independent work, repeats or timestamp ties? | Do not delete events merely to simplify the graph. |
| Repeated event | Same occurrence duplicated by join, or distinct repeated occurrences? | Fix join-induced duplication; preserve actual repeated occurrences. Multiple-case attribution is evaluated under the selected entity policy. |
| Empty cases absent from CSV | Compare the case population and represented cases. | Retain population separately. Never fabricate events to populate empty cases. |

Store `diagnostic`, `hypothesis`, `source_witness`, `EEG_candidate`, `ESpec_field`, `before`, `after`, `validation_results` and `decision`. Thresholds prioritize inspection; they are not universal error criteria.

## Runtime versus author audit

Runtime evidence consists of the request, frozen interpretation, EEG, ESpec, SQL, output log and read-only source DB. Gold SQL/logs, reference case-path catalogs and benchmark labels are excluded from runtime inputs. The current author audit uses stronger reference annotations; its success does not prove that the inferred EEG is complete or that runtime repair improves accuracy.

For repair evaluation, keep the same initial interpretation/ESpec and report correct, unnecessary, harmful and unresolved repairs, net event precision/recall and exact-match changes. Negative controls must include legitimate atomic cases, unfinished work, activities with no observed occurrences, rework and shared-resource views.

## Audit experience informing the design

Seven original/paraphrase pairs were replaced: HF03, HF08, N12, W06, WF08, WF09 and OU10. The first six belong to the three primary DBs; OU10 is an additional targeted UniversityFlow correction. These are benchmark edits, not Step 4 operations. In contrast, the checks that distinguished missing timestamps from extraction losses, verified case paths and preserved repeated occurrences are directly relevant to Step 4.

The independent reference replay checked all 120 requests in HospitalFlow, PlateFlow and WarehouseFlow. It used documented event definitions and attribution paths rather than stored Gold SQL to construct expected tuples. It supports correctness relative to those documented semantics; it is not an independent blinded expert annotation study.
