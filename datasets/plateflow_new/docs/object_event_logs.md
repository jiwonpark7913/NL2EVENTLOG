# Object-specific full lifecycle Gold logs

| Case type | Q3 | Q4 | Cases | Event rows |
| --- | --- | --- | --- | --- |
| Slab | NF01 | NF01P | 30 | 620 |
| Rolling Plan | NF02 | NF02P | 28 | 106 |
| Rolling Instruction | NF03 | NF03P | 26 | 454 |
| Mother Material | NF04 | NF04P | 26 | 428 |
| Plate Piece | NF05 | NF05P | 38 | 318 |
| Dimension Inspection | NF06 | NF06P | 46 | 46 |
| Quality Review | NF07 | NF07P | 46 | 43 |
| Equipment | NF08 | NF08P | 7 | 240 |
| Furnace Operation Record | NF09 | NF09P | 70 | 68 |
| Rolling Operation Record | NF10 | NF10P | 44 | 42 |
| Finishing Operation Record | NF11 | NF11P | 130 | 130 |

- Empty and unfinished cases remain in private/case_population.json and ES.case_population even when they have no CSV rows.
- These are case-based CSV logs, not OCEL. A shared event may appear in different case views, never twice within the same case.
