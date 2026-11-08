# process_code

**Rows:** 8 · **Columns:** 3

## Original records (first 10)

| process_group | code | meaning |
| --- | --- | --- |
| FURNACE | C | Furnace charging |
| FURNACE | A | Furnace heating |
| FURNACE | D | Furnace discharge |
| ROLLING | R | Rough rolling |
| ROLLING | F | Finish rolling |
| FINISHING | L | Leveling |
| FINISHING | A | Heat treatment |
| FINISHING | S | Surface finishing |

## Column definitions

| Column | SQL type | PK | Not null |
|---|---|---|---|
| process_group | TEXT | True | True |
| code | TEXT | True | True |
| meaning | TEXT | False | True |
