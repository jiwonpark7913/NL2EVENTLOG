# Procurement to payment

This synthetic NL2EventLog benchmark contains 40 English requests derived from 20 paired specifications. The same requests and underlying events apply to all 6 physical layouts.

The [question file](evaluation/model_questions.jsonl) contains one request per line with fields `question_id` and `text`. A trailing `P` identifies the second wording of a pair. The first ten pairs select named activities. The remaining ten pairs request a complete case history or a complete business phase.

For each request, provide its text and the selected layout’s SQLite database and data dictionary to the extraction method. The [variant manifest](evaluation/variant_manifest.json) lists paths and SHA-256 checksums.

| Layout | Tables | Maximum forward FK hops | Names and dictionary | Additional time fields per event table |
|---|---:|---:|---|---:|
| [base](input/) | 15 | 1 | N0 | 0 |
| [x1_max](variants/x1_max/input/) | 120 | 1 | N0 | 0 |
| [x2_max](variants/x2_max/input/) | 15 | 3 | N0 | 0 |
| [x3_max](variants/x3_max/input/) | 15 | 1 | N3 | 0 |
| [x4_max](variants/x4_max/input/) | 15 | 1 | N0 | 4 |
| [stress](variants/stress/input/) | 120 | 3 | N3 | 4 |

N0 uses descriptive identifiers, N1 abbreviates them, N2 uses codes with the full dictionary, and N3 uses codes with a shorter dictionary. The stress layout combines the highest level of all four factors.
