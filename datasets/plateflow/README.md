# Plateflow

PlateFlow is a synthetic steel-plate production database with slab receiving, rolling preparation, furnace and rolling operations, finishing, inspection and quality review. It reflects industrial process concepts, not observed production records.

## Dataset overview

| Physical tables | Gold object types | Core business concepts | Gold SQL/CSV pairs verified |
|---:|---:|---:|---:|
| 12 | 12 | 6 | 50 |

## Explore the dataset

- [Gold Evidence Graph and real table records](review/database/README.md)
- [Editable Draw.io relational diagram](docs/schema.drawio)
- [Per-question Gold DFGs](review/gold_dfg/README.md)
- [Business Data Dictionary](input/data_dictionary.json)
- [Gold object membership and source bindings](review/gold_dfg/event_graph.md)

## Schema and process semantics

Object types identify business entities or independent occurrence records. The conceptual shortlist of core nouns is not a physical schema transformation.
Event timestamps and activity codes are interpreted using the Data Dictionary and their source-table context. The Gold event-log oracle is stored separately from normal model inputs.
