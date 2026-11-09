# UniversityFlow — Database and Gold Evidence Review

UniversityFlow is a synthetic university operations database representing students, courses, registration, assignments, examinations, theses, and simulation experiments. Its domain design draws on RSchema university requirements and uses authored synthetic records.

## Gold Evidence Graph

![Gold Object Types → Physical Tables → Activities](gold_evidence_graph.svg)

The diagram distinguishes core business object concepts from supporting entities and activity-record types. 
Each physical table belongs to exactly one Gold Object Type. An event can be associated with several business objects through foreign keys without its source table belonging to multiple OTs.

**This is an author-annotated Gold source projection, not an inferred Evidence Graph or a full provenance graph.**
Gold SQL and record-level evidence are available in the linked inspection materials.

## Relational Schema (SQL foreign keys)

![Relational database schema](schema.svg)

## Table inspector

| Physical table | Rows | Columns | Gold OT | First ten records |
|---|---:|---:|---|---|
| assignment | 20 | 8 | Assignment | [Preview](tables/assignment.md) |
| assignment_grading | 25 | 7 | Assignment grading record | [Preview](tables/assignment_grading.md) |
| course | 6 | 10 | Course | [Preview](tables/course.md) |
| degree_examination_result | 40 | 9 | Examination result record | [Preview](tables/degree_examination_result.md) |
| instructor | 3 | 3 | Instructor | [Preview](tables/instructor.md) |
| registration | 47 | 9 | Student-course registration | [Preview](tables/registration.md) |
| simulation_module | 3 | 9 | Simulation module | [Preview](tables/simulation_module.md) |
| student | 40 | 8 | Student | [Preview](tables/student.md) |
| student_simulation_experiment_result | 27 | 9 | Simulation experiment result record | [Preview](tables/student_simulation_experiment_result.md) |
| task | 3 | 10 | Course-design task | [Preview](tables/task.md) |
| thesis | 16 | 10 | Thesis | [Preview](tables/thesis.md) |

## Gold object types vs. core business objects

Gold identity types: **11**; principal business object concepts in this domain: **8**. 
The core set is a conceptual layer for interpreting process scope, not a rule that forces unrelated PK domains to merge.

**Core business concepts:** Assignment, Course, Course-design task, Instructor, Simulation module, Student, Student-course registration, Thesis.

Supporting Gold types: Assignment grading record, Examination result record, Simulation experiment result record.

## Evaluation evidence

- Gold SQL/CSV pairs executable and consistent: 66; compared event rows across questions: 8528.
- [Gold source inventory](../gold_dfg/event_graph.md)
- [Question-level Gold DFGs](../gold_dfg/README.md)
- [Editable Draw.io schema](../../docs/schema.drawio)

