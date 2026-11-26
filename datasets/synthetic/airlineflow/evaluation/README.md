# Evaluation resources

[Dataset home](../README.md) · [Dataset analysis](../docs/dataset_analysis.md)

## Model-facing requests

- [Pilot questions (12)](model_questions.jsonl)
- [Test questions (60)](model_questions_test.jsonl)

Pass only the request text (and database and dictionary) to a model.

## Evaluator-only files

- [Full registry](query_registry.csv) and [test registry](test_registry.csv): complexity, scope, expected counts, case policy.
- [Variant manifest](variant_manifest.json): applicable requests, DB/DD hashes.
- [Gold summary](gold_summary.csv): reference counts and multiset digests.
- [Case-key policy](case_key_policy.json) and [approved activity aliases](approved_activity_aliases.json): reference normalization policies. The standalone implementation is not the frozen production scorer.
- [Technical receipt](verification.json), [semantic audit](semantic_gold_review_20261127.md), [interval audit](interval_audit.csv), [timestamp audit](timestamp_query_audit.csv).
- [Legacy questions](legacy_model_questions.jsonl): compatibility only; excluded from the 108 conditions.

Use the 60 held-out requests at L15; run the 12 pilot requests at all four schema levels. Do not tune on held-out answers. Human approval and final production-runner integration are distinct from fixture verification.
