# Release maintenance

The active entry points are `generate.py --check` (read-only fixed-seed reconstruction), `generate.py EMPTY_OUTPUT_DIRECTORY` (reproduce the released databases), `verify.py` (read-only release audit), and `publish_review.py` (validate and refresh derived review assets). The publication checks every original Gold file and DB/dictionary fingerprint before and after running the graph, HTML, enrichment and documentation stages.

The duplicate `verify_v2.py` was removed. The previous `regenerate_v2.py`, `migrate_operational_schema.py` and `randomize_timestamps.py` are historical migration and audit implementations, not current entry points. They are retained for research provenance; do not execute them to refresh the review. `normalize_case_keys.py` is an evaluator reference, not a confirmed production scorer. Older archived releases remain for reproducibility.

The published interface uses English labels and request text. Existing bilingual registry fields and reference PI/ESpec metadata are preserved for traceability and compatibility; they are not newly authored translations. User-entered review notes may be in any language. Export review JSON before switching local HTML files because browser storage behavior varies by file origin. The fixture version and review keys are unchanged by this interface revision.
