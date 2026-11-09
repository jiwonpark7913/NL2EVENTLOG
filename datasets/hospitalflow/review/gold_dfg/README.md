# HospitalFlow — Question-level Gold DFG inspection

**Evaluation only: never provide Gold data or DFGs to NL2EventLog model inputs.**

DFGs are calculated from each question's Gold event log, using timestamp and event ID for deterministic ordering.

Timestamp ties are ordered using event_id only for deterministic display; this does not establish causal ordering.

| Question | Events | Cases | Activity types | Gold DFG | Gold SQL |
|---|---:|---:|---:|---|---|
| H01 | 194 | 15 | 3 | [Graph](graphs/H01.svg) | [SQL](../../private/gold_sql/H01.sql) |
| H01P | 194 | 15 | 3 | [Graph](graphs/H01P.svg) | [SQL](../../private/gold_sql/H01P.sql) |
| H02 | 124 | 14 | 3 | [Graph](graphs/H02.svg) | [SQL](../../private/gold_sql/H02.sql) |
| H02P | 124 | 14 | 3 | [Graph](graphs/H02P.svg) | [SQL](../../private/gold_sql/H02P.sql) |
| H03 | 154 | 30 | 3 | [Graph](graphs/H03.svg) | [SQL](../../private/gold_sql/H03.sql) |
| H03P | 154 | 30 | 3 | [Graph](graphs/H03P.svg) | [SQL](../../private/gold_sql/H03P.sql) |
| H04 | 126 | 28 | 4 | [Graph](graphs/H04.svg) | [SQL](../../private/gold_sql/H04.sql) |
| H04P | 126 | 28 | 4 | [Graph](graphs/H04P.svg) | [SQL](../../private/gold_sql/H04P.sql) |
| H05 | 55 | 13 | 3 | [Graph](graphs/H05.svg) | [SQL](../../private/gold_sql/H05.sql) |
| H05P | 55 | 13 | 3 | [Graph](graphs/H05P.svg) | [SQL](../../private/gold_sql/H05P.sql) |
| H06 | 44 | 15 | 4 | [Graph](graphs/H06.svg) | [SQL](../../private/gold_sql/H06.sql) |
| H06P | 44 | 15 | 4 | [Graph](graphs/H06P.svg) | [SQL](../../private/gold_sql/H06P.sql) |
| H07 | 158 | 11 | 5 | [Graph](graphs/H07.svg) | [SQL](../../private/gold_sql/H07.sql) |
| H07P | 158 | 11 | 5 | [Graph](graphs/H07P.svg) | [SQL](../../private/gold_sql/H07P.sql) |
| HF01 | 627 | 11 | 20 | [Graph](graphs/HF01.svg) | [SQL](../../private/gold_sql/HF01.sql) |
| HF01P | 627 | 11 | 20 | [Graph](graphs/HF01P.svg) | [SQL](../../private/gold_sql/HF01P.sql) |
| HF02 | 600 | 15 | 20 | [Graph](graphs/HF02.svg) | [SQL](../../private/gold_sql/HF02.sql) |
| HF02P | 600 | 15 | 20 | [Graph](graphs/HF02P.svg) | [SQL](../../private/gold_sql/HF02P.sql) |
| HF03 | 203 | 203 | 3 | [Graph](graphs/HF03.svg) | [SQL](../../private/gold_sql/HF03.sql) |
| HF03P | 203 | 203 | 3 | [Graph](graphs/HF03P.svg) | [SQL](../../private/gold_sql/HF03P.sql) |
| HF04 | 267 | 34 | 6 | [Graph](graphs/HF04.svg) | [SQL](../../private/gold_sql/HF04.sql) |
| HF04P | 267 | 34 | 6 | [Graph](graphs/HF04P.svg) | [SQL](../../private/gold_sql/HF04P.sql) |
| HF05 | 198 | 29 | 6 | [Graph](graphs/HF05.svg) | [SQL](../../private/gold_sql/HF05.sql) |
| HF05P | 198 | 29 | 6 | [Graph](graphs/HF05P.svg) | [SQL](../../private/gold_sql/HF05P.sql) |
| HF06 | 103 | 17 | 6 | [Graph](graphs/HF06.svg) | [SQL](../../private/gold_sql/HF06.sql) |
| HF06P | 103 | 17 | 6 | [Graph](graphs/HF06P.svg) | [SQL](../../private/gold_sql/HF06P.sql) |
| H09 | 10 | 8 | 1 | [Graph](graphs/H09.svg) | [SQL](../../private/gold_sql/H09.sql) |
| H09P | 10 | 8 | 1 | [Graph](graphs/H09P.svg) | [SQL](../../private/gold_sql/H09P.sql) |
| H10 | 5 | 5 | 1 | [Graph](graphs/H10.svg) | [SQL](../../private/gold_sql/H10.sql) |
| H10P | 5 | 5 | 1 | [Graph](graphs/H10P.svg) | [SQL](../../private/gold_sql/H10P.sql) |
| H11 | 25 | 11 | 2 | [Graph](graphs/H11.svg) | [SQL](../../private/gold_sql/H11.sql) |
| H11P | 25 | 11 | 2 | [Graph](graphs/H11P.svg) | [SQL](../../private/gold_sql/H11P.sql) |
| HF07 | 124 | 62 | 2 | [Graph](graphs/HF07.svg) | [SQL](../../private/gold_sql/HF07.sql) |
| HF07P | 124 | 62 | 2 | [Graph](graphs/HF07P.svg) | [SQL](../../private/gold_sql/HF07P.sql) |
| HF08 | 67 | 67 | 2 | [Graph](graphs/HF08.svg) | [SQL](../../private/gold_sql/HF08.sql) |
| HF08P | 67 | 67 | 2 | [Graph](graphs/HF08P.svg) | [SQL](../../private/gold_sql/HF08P.sql) |
| HF09 | 42 | 23 | 2 | [Graph](graphs/HF09.svg) | [SQL](../../private/gold_sql/HF09.sql) |
| HF09P | 42 | 23 | 2 | [Graph](graphs/HF09P.svg) | [SQL](../../private/gold_sql/HF09P.sql) |
| HF10 | 101 | 34 | 3 | [Graph](graphs/HF10.svg) | [SQL](../../private/gold_sql/HF10.sql) |
| HF10P | 101 | 34 | 3 | [Graph](graphs/HF10P.svg) | [SQL](../../private/gold_sql/HF10P.sql) |
| H12 | 101 | 34 | 3 | [Graph](graphs/H12.svg) | [SQL](../../private/gold_sql/H12.sql) |
| H12P | 101 | 34 | 3 | [Graph](graphs/H12P.svg) | [SQL](../../private/gold_sql/H12P.sql) |

[Current source evidence inventory](event_graph.md) · [Current database inspection](../database/README.md)
