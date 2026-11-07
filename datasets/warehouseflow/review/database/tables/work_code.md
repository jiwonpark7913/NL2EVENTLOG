# work_code

**Rows:** 10 · **Columns:** 3

## Original records (first 10)

| code_family | code | meaning |
| --- | --- | --- |
| MOVEMENT | IN | Receipt into warehouse stock |
| MOVEMENT | OUT | Dispatch from warehouse stock |
| REQUEST | CHECK | Check receiving request |
| REQUEST | HOLD | Hold receiving request |
| REQUEST | RELEASE | Release receiving request |
| TASK | PUTAWAY | Putaway work |
| TASK | PICK | Picking work |
| TASK | PACK | Packing work |
| HANDLING | UNLOAD | Unloading work |
| HANDLING | LOAD | Loading work |

## Column definitions

| Column | SQL type | PK | Not null |
|---|---|---|---|
| code_family | TEXT | True | True |
| code | TEXT | True | True |
| meaning | TEXT | False | True |
