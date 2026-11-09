# HospitalFlow

HospitalFlow models synthetic patient encounters, clinical orders, medication administration, laboratory testing, procedures, and care-unit transfers. Its patient and admission structures and time-column vocabulary are inspired by the public MIMIC-IV hospital schema; all records are synthetic, not MIMIC-IV patient records.

## Dataset overview

| Physical ERs | Entity Type candidates | Core business concepts | Gold SQL/CSV pairs verified |
|---:|---:|---:|---:|
| 12 | 11 | 5 | 42 |

## Explore the dataset

- [Gold Event Extraction Graph (EEG) Source Projection and real table records](review/database/README.md)
- [Editable Draw.io relational diagram](docs/schema.drawio)
- [Per-question Gold DFGs](review/gold_dfg/README.md)
- [Business Data Dictionary](input/data_dictionary.json)
- [Gold object membership and source bindings](review/gold_dfg/event_graph.md)

## Schema and process semantics

Entity Types classify business entities; ERs preserve the underlying physical tables. Semantic ET grouping and instance identity resolution are separate tasks.
Event timestamps and activity codes are interpreted using the Data Dictionary and their source-table context. The Gold event-log oracle is stored separately from normal model inputs.

## Entity-model interpretation

A physical table is one **Entity Representation (ER)**. Its displayed **Entity Type (ET) candidate** comes from legacy Gold annotations. ET semantic grouping and cross-ER instance identity resolution must be validated independently. FK reachability alone does not establish Case Attribution or Lifecycle Membership. See the [EEG / ET / ER methodology](../../docs/system/EEG_ENTITY_MODEL.md) for the target semantics.
