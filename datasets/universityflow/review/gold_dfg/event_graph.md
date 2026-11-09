# Universityflow — Gold source inventory

**Author annotations.** One identity OT per physical table; event-to-object attribution is a separate relation.

| Physical table | Gold Object Type | Gold activity source labels |
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

This is a source-binding projection. The model is not given this file.

[Gold diagram](../database/gold_evidence_graph.svg) · [Gold DFGs](README.md)
