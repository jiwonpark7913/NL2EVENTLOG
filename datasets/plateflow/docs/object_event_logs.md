# Object-based event logs

- Each answerable row below has its own English question, Gold specification, SQL and CSV event log.
- Business objects, event records and association records are labelled separately; a row-level case is useful for coverage but is not necessarily a rich business lifecycle.
- Case population includes records with no selected events; their event CSV has no row.
- One event may belong to several different cases, such as multiple goods types or workers. These are valid event-to-case links; the same event is not repeated within one case.
- Every view uses the exact scope stated below. Related upstream or downstream events are not automatically included through every reachable join.
- Existing explicit/paraphrase questions are retained. Paired questions may have identical Gold logs.
- Logs are case-based CSVs, not OCEL files.

| Case table | Case concept | Kind | Question | Cases | Event rows | Gold CSV |
|---|---|---|---|---:|---:|---|
| slab_material | Slab | business object | OPV01 | 36 | 324 | [CSV](../private/gold_logs/OPV01.csv) |
| planned_rolling_instruction | Rolling plan | business object | OPV02 | 36 | 36 | [CSV](../private/gold_logs/OPV02.csv) |
| rolling_instruction | Rolling instruction | business object | OPV03 | 36 | 36 | [CSV](../private/gold_logs/OPV03.csv) |
| as_rolled_material | Mother material | business object | OPV04 | 36 | 324 | [CSV](../private/gold_logs/OPV04.csv) |
| furnace_charge_tracking | Furnace tracking record | tracking record | OPV05 | 30 | 30 | [CSV](../private/gold_logs/OPV05.csv) |
| cutting_finishing_instruction | Cutting instruction | business object | OPV06 | 18 | 18 | [CSV](../private/gold_logs/OPV06.csv) |
| plate_material | Cut plate piece | business object | OPV07 | 39 | 114 | [CSV](../private/gold_logs/OPV07.csv) |
| material_operation_history | Material operation record | event record | OPV08 | 153 | 153 | [CSV](../private/gold_logs/OPV08.csv) |

## Scope of each view

- **OPV01 — Slab:** All recorded manufacturing events of the mother material and cut pieces derived from this slab; no upstream casting events are inferred.
- **OPV02 — Rolling plan:** The actual release of the rolling instruction linked to this plan; planned reheating times are not execution events.
- **OPV03 — Rolling instruction:** The actual release event for this rolling instruction.
- **OPV04 — Mother material:** All recorded mother-material events and its descendant-piece events, each occurrence once.
- **OPV05 — Furnace tracking record:** The recorded yard-instruction receipt for this tracking record; lot-level charging events remain outside the material-event set.
- **OPV06 — Cutting instruction:** The actual release event for this cutting/finishing instruction.
- **OPV07 — Cut plate piece:** Only operations recorded on this piece and its dimensional inspection. Upstream mother events are not copied to each piece.
- **OPV08 — Material operation record:** The operation-completion event represented by this transaction ID, preserving its process-code meaning.

## Tables without an actual event-log view

- **operation_code:** Operation codes define activity meanings. They are not business-object instances or cases.
