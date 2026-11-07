# simulation_module

**Rows:** 3 · **Columns:** 9

## Original records (first 10)

| module_id | module_name | module_type | module_description | module_code | simulation_module_published_at | simulation_module_validated_at | simulation_module_released_at | simulation_module_retired_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M01 | PCM | PCM | Synthetic teaching module | example_module_1() | 2026-02-11T15:00:00Z | 2026-02-12T15:00:00Z | 2026-02-13T15:00:00Z | NULL |
| M02 | DPCM | DPCM | Synthetic teaching module | example_module_2() | 2026-02-15T15:00:00Z | 2026-02-16T15:00:00Z | 2026-02-17T15:00:00Z | 2026-04-16T15:00:00Z |
| M03 | Delta Modulation | DELTA | Synthetic teaching module | example_module_3() | 2026-02-10T15:00:00Z | 2026-02-11T15:00:00Z | 2026-02-12T15:00:00Z | 2026-04-20T15:00:00Z |

## Column definitions

| Column | SQL type | PK | Not null |
|---|---|---|---|
| module_id | TEXT | True | True |
| module_name | TEXT | False | True |
| module_type | TEXT | False | True |
| module_description | TEXT | False | True |
| module_code | TEXT | False | True |
| simulation_module_published_at | TEXT | False | False |
| simulation_module_validated_at | TEXT | False | False |
| simulation_module_released_at | TEXT | False | False |
| simulation_module_retired_at | TEXT | False | False |
