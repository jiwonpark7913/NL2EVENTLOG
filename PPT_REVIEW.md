# Review of the dataset-construction presentation

- Reviewed: NL2EventLog_dataset_construction.pptx, seven slides.
- The deck explicitly presents a construction plan.
- The central approach is sound; update the following points if describing the implemented datasets.
- The original PPT has not been modified.

- **Slide 1, 7 — Model inputs omit the task scope catalog used by the current builders.** Recommended correction: List DB, data dictionary, task scope catalog and question. Label the setting catalog-assisted.
- **Slide 2 — RSchema reuse is described as a possibility; conceptual artifacts appear to be available upstream.** Recommended correction: WarehouseFlow and UniversityFlow reuse preserved RSchema requirement/logical-schema pairs. Their conceptual models are derived locally. PlateFlow uses selected table definitions from a Korean manufacturing company and authors a synthetic schema.
- **Slide 3, 4, 7 — ISO/IEC 11179 wording may imply a defined standard template or implemented compliance.** Recommended correction: Use “a custom English enterprise data dictionary informed by metadata principles.” No formal field-level ISO alignment has been established.
- **Slide 4 — Excluding “this column is Approve” can also exclude legitimate business semantics.** Recommended correction: Allow ordinary event-time and code meanings in the dictionary. Withhold question-specific gold scope, selected extraction routes and executable Gold ES/SQL.
- **Slide 3 — File names/formats do not match current artifacts; Q taxonomy coverage is not complete.** Recommended correction: Current artifacts use conceptual/logical JSON, Markdown/JSON/CSV dictionaries, and private/gold.jsonl containing Process View and ES. Paraphrases are authored, not generated through an LLM API. Present YAML/XLSX and complete Q taxonomy as future choices.
- **Slide 5 — Distributed events confuses cross-table process storage with one occurrence split across tables.** Recommended correction: Distinguish “different events stored across tables” from “one event reconstructed from several tables.” Joins may be needed solely for case attribution.
- **Slide 5 — Five patterns appear as a coverage claim.** Recommended correction: Mark them as target patterns. Current datasets implement header events, timestamp milestones, operation history using process codes and parent-to-child material links across tables. Derived-event inference and full status-transition history coverage are not established.
- **Slide 6 — “Independently generated” overstates independence of expected answers.** Recommended correction: Gold log selection and ES/SQL extraction use separate transformations, while sharing authored semantics and persistence assumptions.
- **Slide 6 — Keeping only questions satisfying execution equality excludes intentional unsupported questions.** Recommended correction: Apply SQL/gold equality to answerable questions, including empty logs. Keep a separate unsupported set with documented reason.
- **Slide 6 — Answerability validation appears fully automated.** Recommended correction: SQL execution checks executability and log agreement; answerability also requires semantic/source review. Unsupported items are currently authored labels, not independently proved automatically.
- **Slide 7 — “All constraints verified” exceeds current check coverage.** Recommended correction: Name the implemented checks: exact log equality, FK/integrity checks, selected metadata and business invariants. Do not imply exhaustive semantic validation.

## Suggested current-status wording

- We construct three English-language synthetic development datasets using different source foundations.
- WarehouseFlow and UniversityFlow reuse actual RSchema requirements and logical schemas, while PlateFlow is informed by selected Korean manufacturer table and column definitions.
- We document all physical-design and process assumptions, simulate business histories, and persist them in relational tables.
- For answerable questions, gold logs selected from simulated business histories are compared with SQL results compiled from gold extraction specifications.
- The two paths share authored semantics and therefore establish internal consistency rather than independent correctness of expected answers.
- Current evaluation inputs include a task scope catalog, and model accuracy has not yet been measured.

## Gold equivalence

- Compare normalized occurrence tuples (case, activity, timestamp and occurrence identity) with multiplicity preserved.
- Ignore serialization order.
- Normalize time zones and precision explicitly.
- For an evaluated system that uses its own event IDs, compare source occurrence identity or a defined event matching rule, rather than requiring literal equality of arbitrary ID strings.
