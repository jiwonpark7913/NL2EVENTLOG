# Review of the dataset-construction presentation

Reviewed: NL2EventLog_dataset_construction.pptx, seven slides.
The deck explicitly presents a construction plan. The central approach is
sound; update the following points if describing the implemented fixtures.
The original PPT has not been modified.

| Slide | Finding | Recommended correction |
|---|---|---|
| 1, 7 | Model inputs omit the task scope catalog used by both current builders. | List DB, data dictionary, task scope catalog and question. Label the setting catalog-assisted. |
| 2 | RSchema reuse is described as a possibility; conceptual artifacts appear to be available upstream. | WarehouseFlow actually reuses a frozen RSchema requirement/logical-schema pair. Its conceptual model is derived locally. PlateFlow uses selected original POSCO metadata and authors a synthetic schema. |
| 3, 4, 7 | ISO/IEC 11179 wording may imply a defined standard template or implemented compliance. | Use “a custom English enterprise data dictionary informed by metadata principles.” No formal field-level ISO alignment has been established. |
| 4 | Excluding “this column is Approve” can also exclude legitimate business semantics. | Allow ordinary event-time and code meanings in the dictionary. Withhold question-specific gold scope, selected extraction routes and executable Gold ES/SQL. |
| 3 | File names/formats do not match current artifacts; Q taxonomy coverage is not complete. | Current artifacts use conceptual/logical JSON, Markdown/JSON/CSV dictionaries, and private/gold.jsonl containing Process View and ES. Paraphrases are authored, not generated through an LLM API. Present YAML/XLSX and complete Q taxonomy as future choices. |
| 5 | Distributed events confuses cross-table process storage with one occurrence split across tables. | Distinguish “different events stored across tables” from “one event reconstructed from several tables.” Joins may be needed solely for case attribution. |
| 5 | Five patterns appear as a coverage claim. | Mark them as target patterns. Current fixtures implement header events, timestamp milestones, coded operation history and cross-table lineage. Derived-event inference and full status-transition history coverage are not established. |
| 6 | “Independently generated” overstates oracle independence. | Gold log selection and ES/SQL extraction use separate transformations, while sharing authored semantics and persistence assumptions. |
| 6 | Keeping only questions satisfying execution equality excludes intentional unsupported questions. | Apply SQL/gold equality to answerable questions, including empty logs. Keep a separate unsupported set with documented reason. |
| 6 | Answerability validation appears fully automated. | SQL execution checks executability and log agreement; answerability also requires semantic/source review. Unsupported items are currently authored labels, not independently proved automatically. |
| 7 | “All constraints verified” exceeds current check coverage. | Name the implemented checks: exact log equality, FK/integrity checks, selected metadata and business invariants. Do not imply exhaustive semantic validation. |

## Suggested current-status wording

We construct two English-language synthetic development fixtures using different
source foundations. WarehouseFlow reuses an actual RSchema requirement and
logical schema, while PlateFlow is informed by selected POSCO table and column
definitions. We document all physical-design and process assumptions, simulate
canonical business histories, and persist them in relational tables. For
answerable questions, gold logs selected from canonical histories are compared
with SQL results compiled from gold extraction specifications. The two paths
share authored semantics and therefore establish internal consistency rather
than independent oracle correctness. Current evaluation inputs include a task
scope catalog, and model accuracy has not yet been measured.

## Gold equivalence

Compare normalized occurrence tuples (case, activity, timestamp and occurrence
identity) with multiplicity preserved. Ignore serialization order. Normalize
time zones and precision explicitly. For an evaluated system that uses its own
event IDs, compare source occurrence identity or a defined event matching rule,
rather than requiring literal equality of arbitrary ID strings.
