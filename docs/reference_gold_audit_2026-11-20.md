# Reference Gold audit — 2026-11-20

## Decision and scope

HospitalFlow, PlateFlow and WarehouseFlow are accepted as consistent reference datasets under the documented recorded-occurrence, case-attribution and process-focus contract. Each retains 40 requests (Q1/Q2/Q3/Q4 = 10 each). All 120 requests pass independently reconstructed source-definition/path replay, SQL/CSV/ESpec consistency, provenance, identity, case-population and pair-equality checks. Missing reference events = 0, extra events = 0, unmatched source events = 0.

This is correctness relative to declared source semantics, not a guarantee that every natural-language lifecycle request has one possible interpretation. It does not establish automatic Step 4 repair effectiveness. UniversityFlow received the targeted correction below but is not included in the three-DB acceptance decision.

## Replacements

Both the original and `P` paraphrase were revised. IDs remain stable but semantics changed: invalidate cached model predictions and old evaluation results for these IDs.

| Dataset | Original ID (and P pair) | New case / focus | Events | Cases with events | Singleton cases |
|---|---|---|---:|---:|---:|
| HospitalFlow | HF03 | Hospital admission / laboratory testing | 240 | 12 | 0 |
| HospitalFlow | HF08 | Patient / medication treatment | 198 | 10 | 0 |
| PlateFlow | N12 | Mother material / explicit furnace completions | 68 | 24 | 2 |
| WarehouseFlow | W06 | Receiving request / explicit request actions | 56 | 24 | 0 |
| WarehouseFlow | WF08 | Goods type / inbound receiving | 219 | 6 | 0 |
| WarehouseFlow | WF09 | Worker / outbound-fulfillment work | 112 | 6 | 0 |
| UniversityFlow, targeted fix | OU10 | Instructor / grading and regrading | 25 | 3 | 0 |

## Evidence

`tools/audit_reference_logs.py` reconstructs expected occurrences from source event definitions and forward case paths, without executing the stored Gold SQL to obtain the expected set. Explicit activity enumerations are parsed from Q1 request text. Focused lifecycle requests are restricted by the documented focus; hospital laboratory/medication focuses constrain order identity as well as activity names. Expected and actual `(event_id, case_id, activity, timestamp)` multisets match for all 120 requests.

Additional checks cover SQLite integrity, declared foreign keys, SQL execution, ESpec compiled SQL, model-question text, source-row provenance, unique case/event identities, non-null output fields, case-population membership and exact paraphrase log equality. Detailed counts, singleton cases, empty cases and supported-but-unobserved activities appear in [reference_gold_audit_2026-11-20.json](reference_gold_audit_2026-11-20.json).

## Legitimate partial traces retained

- HF09: four procedure episodes have NULL `endtime`.
- NF07: three pending quality reviews have NULL `finished_at`.
- NF09/NF10: two furnace and two rolling records lack actual completion timestamps.
- WF10/WF11: three task and two handling records have NULL `completed_at`.
- N12 retains two singleton traces because only one selected completion is recorded for those mother materials.

No events were fabricated. Single-activity explicit requests and dense shared-resource DFGs are not automatically errors. Supported activities with no actual occurrences are distinguished from extraction losses. Case populations preserve cases that cannot appear as rows in an event CSV because no events are recorded.

## Reproduction and limitations

Run `python tools/experiments/replace_atomic_review_requests.py`, `python tools/audit_reference_logs.py`, and `python tools/build_gold_review_pages.py`. Gold sources and case paths are author annotations, not runtime model inputs. This is not independent blinded expert annotation, nor proof of real-data generalization. Browser interaction verification was unavailable in the environment; data and script-syntax checks are separate from visual QA.

Step 4 design: [step4_verification_repair.md](step4_verification_repair.md). Proposed paper text: [step4_paper_draft.tex](step4_paper_draft.tex). The latter must match implemented operators and actual evaluation before publication.
