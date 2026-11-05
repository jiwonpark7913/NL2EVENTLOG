# Gold event log DFG review

**EVALUATION ONLY / PRIVATE GOLD — NEVER PASS THESE FILES TO ANY MODEL.**

This folder is separate from datasets/*/input and is absent from every model-input allowlist. No model-input bytes or manifests were changed. Keep it out of repository-wide retrieval/RAG/evaluation prompts.

Source commit: `a0ba4c9631d12730d60bf7720d783a3a827b88dc`. The current remote snapshot still includes Q2/Q4; each HTML page defaults to Q1/Q3 and optionally reveals those existing pairs. This renderer does not delete or regenerate questions.

| Dataset | Questions | Gold logs | Distinct DFGs | GitHub view | Event graph |
|---|---:|---:|---:|---|---|
| warehouseflow | 34 | 32 | 15 | [Questions + DFGs](warehouseflow/README.md) | [Inventory](warehouseflow/event_graph.md) |
| warehouseflow_new | 54 | 50 | 19 | [Questions + DFGs](warehouseflow_new/README.md) | [Inventory](warehouseflow_new/event_graph.md) |
| universityflow | 70 | 66 | 32 | [Questions + DFGs](universityflow/README.md) | [Inventory](universityflow/event_graph.md) |
| plateflow | 44 | 42 | 20 | [Questions + DFGs](plateflow/README.md) | [Inventory](plateflow/event_graph.md) |
| hospitalflow | 44 | 42 | 20 | [Questions + DFGs](hospitalflow/README.md) | [Inventory](hospitalflow/event_graph.md) |
| plateflow_new | 54 | 50 | 20 | [Questions + DFGs](plateflow_new/README.md) | [Inventory](plateflow_new/event_graph.md) |

## Local interactive review

Download and extract [review_bundle.zip](review_bundle.zip), then open index.html. To generate HTML pages from a local checkout, run the renderer first. Alternatively run `python -m http.server 8000` at the repository root and visit http://localhost:8000/review/gold_dfg/. Each dataset page has search, optional Q2/Q4 display, per-case timestamped traces, review status and notes, and JSON export. Review notes remain on that browser/device until exported. GitHub renders the dataset Markdown pages with SVG graphs; it does not execute HTML/JavaScript.

## Reading the graph

- The right panel shows original SQLite rows matched to Gold events. GitHub displays up to three matches per table, with keys, selected event times and carrier values. The HTML bundle shows all columns, remaining matches and FK-linked examples.
- Nodes: activity label, event occurrences, observed start/end case counts. Blue fill = starts; green outline = ends.
- Edges: adjacent selected events per case, with transition counts. All observed edges and activities are included; no frequency threshold hides rare behavior. Identical paired logs reuse the same DFG asset.
- Order: timestamp, then event_id (then original row index). Dashed amber edges touch tied timestamp groups and depend on tie-breaking. Start/end assignments at tied boundaries are also ambiguous. This is a display convention, not proof of order.
- Adjacency is measured in the question-specific projection. Removing intermediate activities can create a new edge. DFGs describe the selected traces, not a causal model or evidence that all cases follow one process.
- Unsupported requests have no DFG. Requested-but-unobserved labels, timestamp ties and duplicate case/event IDs are review flags, not automatic judgments of correctness.

Regenerate with `python tools/build_gold_dfg_review.py --commit HEAD` from a clean checkout of the intended source snapshot. The script verifies all input-file hashes before/after. Gold CSVs are read only.
