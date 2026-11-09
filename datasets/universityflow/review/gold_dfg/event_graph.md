# UniversityFlow — Gold source inventory

**Author annotations (legacy ET candidates).** One ER per physical table. Event-to-entity attribution is a separate relation and same-ET does not imply same entity instance.

| Physical table | Entity Type candidate | Gold activity source labels |
|---|---|---|
| assignment | Assignment | Assignment Assigned, Assignment Grade Finalized, Assignment Resubmitted, Assignment Revision Requested, Assignment Submitted |
| assignment_grading | Assignment grading record | Assignment Graded, Assignment Regraded |
| course | Course | Course Offering Approved, Course Offering Closed, Course Offering Proposed, Course Offering Published |
| degree_examination_result | Examination result record | Degree Examination Taken, Examination Checked In, Examination Result Reviewed, Examination Scheduled, Examination Score Published |
| instructor | Instructor | — |
| registration | Student-course registration | Course Assessment Completed, Course Grade Finalized, Course Registered, Course Started, Registration Approved, Registration Requested |
| simulation_module | Simulation module | Simulation Module Published, Simulation Module Released, Simulation Module Retired, Simulation Module Validated |
| student | Student | — |
| student_simulation_experiment_result | Simulation experiment result record | Simulation Experiment Completed, Simulation Output Reviewed, Simulation Result Accepted, Simulation Run Scheduled, Simulation Run Started |
| task | Course-design task | Design Task Approved, Design Task Closed, Design Task Created, Design Task Published |
| thesis | Thesis | Thesis Accepted, Thesis Draft Registered, Thesis Resubmitted, Thesis Review Started, Thesis Revision Requested, Thesis Submitted |

This is a source-binding projection. This is a reviewer-only candidate grouping and is not provided to the model.

[Gold diagram](../database/gold_evidence_graph.svg) · [Gold DFGs](README.md)

[Entity Representation and namespace candidates](entity_model_candidates.json) — review-only; **not validated semantic ET Gold**.
