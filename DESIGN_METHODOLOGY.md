# Database design and benchmark construction

## Design stages

The supplied SchemaAgent related-work passage distinguishes conceptual modeling
from logical relational mapping. We use this staged separation as documentation
and validation structure. We do not claim to implement LIDA, APSARA, CABSYDD,
OMDDE, HBT, Textodata, or any of the cited algorithms.

| Stage | Decision | Artifact |
|---|---|---|
| Requirements analysis | Business entities, recorded operations and scope | requirements.md, preserved source requirement |
| Conceptual modeling | Entity roles, relationships, event granularity and lineage | conceptual_model.json |
| Logical modeling | Tables, attributes, PK/FK and cardinality | logical_schema.json |
| Physical design | SQLite types, nullability, checks and execution constraints | schema.sql |
| Metadata documentation | English definitions, code domains and business rules | data_dictionary.json/md and docs/ |
| Process simulation | Branches, business consistency and stable occurrence identities | canonical_history.jsonl |
| Persistence | Store history using the designed relational structures | database.sqlite |
| Benchmark derivation | Query scope, Gold Process View/ES and canonical log selection | questions and private gold artifacts |
| Validation | Compile ES, execute SQL, compare with independently selected canonical logs | validation_report.json |

The actual source availability determines the authoring order. WarehouseFlow
starts from an existing requirement/logical-schema pair and derives its
conceptual model for documentation; it does not claim the original conceptual
diagram was supplied. PlateFlow starts from physical metadata descriptions,
infers a scoped conceptual design and authors explicit logical/physical
constraints. Neither fixture invents source artifacts that were not available.

## WarehouseFlow

Retain all six source tables, all 17 attributes and all PK/FK relationships.
Normalize casing inconsistencies and identifiers. Add no tables or columns.
Warehouse and transaction identities have different roles: warehouse is the
chosen case concept; a transaction is one inbound/outbound occurrence.
Goods and worker bridges enrich each transaction and are not separate events.
In this instance their naive cross-join expansion yields 289 rows for 80
business events; the gold extraction preserves the 80 header occurrences.

## PlateFlow

Retain separation of planned instructions, released instructions, furnace
tracking, mother materials, cutting/finishing instructions, individual Plate
materials and immutable operation history. Add a synthetic code-domain table.
Use distinct mother/piece identity sets and a one-to-many lineage.
The mother-case scope includes descendant-piece events once, without multiplying
mother events by its number of pieces. Latest-operation snapshot timestamps
do not substitute for rolling-completion occurrences in history.

## Explicit adaptations

Source metadata is not sufficient to determine every physical and process
constraint. English definitions describe synthetic assumptions openly:
code meanings, timestamp conventions, data types, checks, cardinalities and
simulation routes are additions. No ISO conformity is claimed.
Source mappings and adaptation reports permit inspection of each boundary.

## Evaluation interpretation

These datasets provide task catalogs with business labels and a fixed default
scope. Report results as catalog-assisted extraction. Canonical history and
Gold ES use different transformation paths but share authored semantics.
Gold SQL consistency is not model accuracy, gold annotation independence,
or held-out generalization. Question paraphrases are paired tests.
Unsupported questions are distinguished from empty observations.
The ES contracts are fixture-local and still require adaptation to the
existing NL2EventLog implementation.
