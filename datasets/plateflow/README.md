# PlateFlow v2 — English schema-informed synthetic benchmark

This independent dataset revises PlateFlow v1 to reflect the table separation
in the supplied POSCO metadata CSV. It does not depend on ProcureFlow or v1.
All user-facing requirements, dictionary definitions and questions are English.
Original table/column identifiers remain only as provenance references.

## Reproduce

Python 3.10+, standard library only:

    python build.py

Run in a writable copy. Generated artifacts are overwritten.

## Structure retained from the source

| English table | Referenced original table | Role |
|---|---|---|
| slab_material | TB_M2EA08_C_MTL060 | Slab material and charge context |
| planned_rolling_instruction | TB_M2LB01_D_PLANINST010 | Planned rolling instruction |
| rolling_instruction | TB_M2LM01_D_INST010 | Released rolling instruction |
| furnace_charge_tracking | TB_M2EA05_E_RF_IN060 | Furnace charging tracking |
| as_rolled_material | TB_M2LM01_E_MTRL010 | Mother material lifecycle snapshot |
| cutting_finishing_instruction | TB_M2LM01_D_INST020 | Cutting/finishing instruction |
| plate_material | TB_M2LM01_E_MTRL020 | Individual Plate material |
| material_operation_history | TB_M2LM01_T_OPERHIST | Repeated operation history |
| operation_code | Newly authored | Synthetic operation value domain |

The supplied CSV has 20 table names and 6,616 metadata rows, with some repeated
table/column definitions. It supplies owner, table name/description and column
name/description. It does not supply SQL types, declared keys or value-domain
code meanings. V2 selects eight source table roles, rather than recreating the
entire enterprise schema. Each retained column has an explicit source reference;
new columns have a null source reference.

## Changes from v1

Plans and released work instructions are separate. Furnace tracking is separate
from the material snapshot. Mother as-rolled materials and individual Plate
materials are distinct; one completed mother yields one to three pieces.
Cutting/finishing instructions have their own table. Actual operation history
uses occurrence IDs, material identities, process codes, start and completion
times, with repeated inspection and heat-treatment rows.

Rolling completion comes from the RL operation-history occurrence. The
latest-operation-completed snapshot updates through subsequent operations,
so it is deliberately unsuitable as a generic rolling-completion timestamp.
This preserves the source description of PLT_AC_OP_END_OP_DT as the final
actual process work timestamp.

Factory/process code values RL/CO/LE/SC/HT/IF/IP are invented for this fixture.
One-to-many mother/piece lineage, explicit keys, link columns, durations and
route ordering are synthetic design assumptions, not established POSCO rules.
Lot charging start and material charging are stored separately; the default
material view excludes lot-level events rather than equating both timestamps.

## Model inputs and evaluation

Provide only input/ to the model. Keep build.py, design/, private/ and the
validation report outside model context because they contain oracle mappings.
The task catalog specifies the mother-material case concept and default scope;
this is a catalog-assisted evaluation setting.

V01/V02, V03/V04 and V05/V06 are paired explicit/paraphrase tests.
V07 tests the cutting-to-piece-inspection lifecycle. V08 is unsupported because
upstream casting timestamps are absent. Planned times and database timestamps
are excluded from actual execution logs.

For mother cases, include each mother occurrence once and each descendant-piece
occurrence once. Do not join all mother events directly to all pieces: that
would multiply the upstream log. History identity resolution uses two disjoint
identity sets to map each operation to its mother case. The history material ID
references either a mother or a piece, with an insert trigger and separate
orphan check rather than a false single-table FK declaration.

Gold logs are filtered from canonical semantic events. Gold ES is built from
separate persistence mappings, compiled with UNION ALL, and executed on SQLite.
Exact equality verifies occurrence preservation, including repeated activities.
They share authored process assumptions and are development fixtures.
Classic CSV event logs, not OCEL. Case population is separately declared in ES;
cases with no selected events have no event CSV row.

## Limits

No real production rows, identifiers or fitted empirical distributions are
included. This is not a full original-schema replica. Metadata is a practical
English custom profile, without an ISO/IEC 11179 conformity claim.
SchemaAgent design stages are inspiration only; no RSchema requirement sample
is used. The ES remains fixture-local and has not been adapted to the existing
NL2EventLog contract. Consistency checks do not measure extraction-model accuracy.

## Schema and documentation

![Schema](docs/schema.png)

- [Table inventory and relationships](docs/schema_overview.md)
- [English column dictionary](docs/data_dictionary.md)
- [CSV dictionary](docs/data_dictionary.csv)
- [Editable draw.io diagram](docs/schema.drawio)
- [SVG diagram](docs/schema.svg)
