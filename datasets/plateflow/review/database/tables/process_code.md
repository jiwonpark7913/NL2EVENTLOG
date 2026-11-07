# process_code

**Rows:** 8 · **Columns:** 3

## Original records (first 10)

| process_group | code | meaning |
| --- | --- | --- |
| FURNACE | CH | Furnace charging |
| FURNACE | HT | Furnace heating |
| FURNACE | DS | Furnace discharge |
| ROLLING | RR | Rough rolling |
| ROLLING | FR | Finish rolling |
| FINISHING | LEV | Leveling |
| FINISHING | HT | Heat treatment |
| FINISHING | SF | Surface finishing |

## Column definitions

| Column | SQL type | PK | Not null |
|---|---|---|---|
| process_group | TEXT | True | True |
| code | TEXT | True | True |
| meaning | TEXT | False | True |
