# work_code

**Rows:** 10 · **Columns:** 3

## Original records (first 10)

| code_family | code | meaning |
| --- | --- | --- |
| MOVEMENT | I | Receipt into warehouse stock |
| MOVEMENT | O | Dispatch from warehouse stock |
| REQUEST | A | Check receiving request |
| REQUEST | H | Hold receiving request |
| REQUEST | R | Release receiving request |
| TASK | A | Putaway work |
| TASK | K | Picking work |
| TASK | B | Packing work |
| HANDLING | U | Unloading work |
| HANDLING | L | Loading work |

## Column definitions

| Column | SQL type | PK | Not null |
|---|---|---|---|
| code_family | TEXT | True | True |
| code | TEXT | True | True |
| meaning | TEXT | False | True |
