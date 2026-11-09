# Hospitalflow

HospitalFlow models synthetic patient encounters, clinical orders, medication administration, laboratory testing, procedures, and care-unit transfers. Its patient and admission structures and time-column vocabulary are inspired by the public MIMIC-IV hospital schema; all records are synthetic, not MIMIC-IV patient records.

## Dataset overview

| Physical tables | Gold object types | Core business concepts | Gold SQL/CSV pairs verified |
|---:|---:|---:|---:|
| 12 | 11 | 5 | 42 |

## Explore the dataset

- [Gold Evidence Graph and real table records](review/database/README.md)
- [Editable Draw.io relational diagram](docs/schema.drawio)
- [Per-question Gold DFGs](review/gold_dfg/README.md)
- [Business Data Dictionary](input/data_dictionary.json)
- [Gold object membership and source bindings](review/gold_dfg/event_graph.md)

## Schema and process semantics

Object types identify business entities or independent occurrence records. The conceptual shortlist of core nouns is not a physical schema transformation.
Event timestamps and activity codes are interpreted using the Data Dictionary and their source-table context. The Gold event-log oracle is stored separately from normal model inputs.
