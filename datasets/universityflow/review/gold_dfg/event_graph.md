# universityflow · Event graph inventory

**EVALUATION ONLY.** [Back to question and DFG review](README.md).

This page shows the authored benchmark graph. Table bindings identify where events are recorded. Object links identify which activities are attributed to an object, including activities recorded in other tables.

Documented object views supply the names of their singleton OTs.
Every physical object without an explicit group gets a singleton OT. Table-named singletons have no authored object-view attribution. See Events produced for their source activities.

## Tables and event sources

| Table | Event classification | Carrier column | Selected event timestamps | Physical object (table · PK) | OT group | Events produced |
|---|---|---|---|---|---|---|
| `assignment` | Event · non-carrier | — | `assignment_assigned_at`, `assignment_grade_finalized_at`, `assignment_resubmitted_at`, `assignment_revision_requested_at`, `assignment_submitted_at` | `assignment` · `assignment_id` | Assignment | Assignment Assigned, Assignment Grade Finalized, Assignment Resubmitted, Assignment Revision Requested, Assignment Submitted |
| `assignment_grading` | Event · carrier | `grading_kind` | `grading_time` | `assignment_grading` · `assignment_id`, `instructor_id`, `grading_time` | Assignment grading record | Assignment Graded, Assignment Regraded |
| `course` | Event · non-carrier | — | `course_offering_approved_at`, `course_offering_closed_at`, `course_offering_proposed_at`, `course_offering_published_at` | `course` · `course_id` | Course | Course Offering Approved, Course Offering Closed, Course Offering Proposed, Course Offering Published |
| `degree_examination_result` | Event · non-carrier | — | `examination_checked_in_at`, `examination_date`, `examination_result_reviewed_at`, `examination_scheduled_at`, `examination_score_published_at` | `degree_examination_result` · `result_id` | Examination result record | Degree Examination Taken, Examination Checked In, Examination Result Reviewed, Examination Scheduled, Examination Score Published |
| `instructor` | Non-event | — | — | `instructor` · `instructor_id` | Instructor | — |
| `registration` | Event · non-carrier | — | `course_assessment_completed_at`, `course_grade_finalized_at`, `course_started_at`, `registration_approved_at`, `registration_requested_at`, `registration_time` | `registration` · `student_id`, `course_id` | Student-course registration | Course Assessment Completed, Course Grade Finalized, Course Registered, Course Started, Registration Approved, Registration Requested |
| `simulation_module` | Event · non-carrier | — | `simulation_module_published_at`, `simulation_module_released_at`, `simulation_module_retired_at`, `simulation_module_validated_at` | `simulation_module` · `module_id` | Simulation module | Simulation Module Published, Simulation Module Released, Simulation Module Retired, Simulation Module Validated |
| `student` | Non-event | — | — | `student` · `student_id` | Student | — |
| `student_simulation_experiment_result` | Event · non-carrier | — | `simulation_date`, `simulation_output_reviewed_at`, `simulation_result_accepted_at`, `simulation_run_scheduled_at`, `simulation_run_started_at` | `student_simulation_experiment_result` · `student_id`, `module_id`, `simulation_date` | Simulation experiment result record | Simulation Experiment Completed, Simulation Output Reviewed, Simulation Result Accepted, Simulation Run Scheduled, Simulation Run Started |
| `task` | Event · non-carrier | — | `design_task_approved_at`, `design_task_closed_at`, `design_task_created_at`, `design_task_published_at` | `task` · `task_id` | Course-design task | Design Task Approved, Design Task Closed, Design Task Created, Design Task Published |
| `thesis` | Event · non-carrier | — | `submission_date`, `thesis_accepted_at`, `thesis_draft_registered_at`, `thesis_resubmitted_at`, `thesis_review_started_at`, `thesis_revision_requested_at` | `thesis` · `thesis_id` | Thesis | Thesis Accepted, Thesis Draft Registered, Thesis Resubmitted, Thesis Review Started, Thesis Revision Requested, Thesis Submitted |

## Object types and attributed activities

| OT group | Member physical objects | Activities linked to OT |
|---|---|---|
| Student | `student` | Assignment Assigned, Assignment Grade Finalized, Assignment Graded, Assignment Regraded, Assignment Resubmitted, Assignment Revision Requested, Assignment Submitted, Course Assessment Completed, Course Grade Finalized, Course Registered, Course Started, Degree Examination Taken, Examination Checked In, Examination Result Reviewed, Examination Scheduled, Examination Score Published, Registration Approved, Registration Requested, Simulation Experiment Completed, Simulation Output Reviewed, Simulation Result Accepted, Simulation Run Scheduled, Simulation Run Started, Thesis Accepted, Thesis Draft Registered, Thesis Resubmitted, Thesis Review Started, Thesis Revision Requested, Thesis Submitted |
| Course | `course` | Course Assessment Completed, Course Grade Finalized, Course Offering Approved, Course Offering Closed, Course Offering Proposed, Course Offering Published, Course Registered, Course Started, Registration Approved, Registration Requested |
| Student-course registration | `registration` | Course Assessment Completed, Course Grade Finalized, Course Registered, Course Started, Registration Approved, Registration Requested |
| Examination result record | `degree_examination_result` | Degree Examination Taken, Examination Checked In, Examination Result Reviewed, Examination Scheduled, Examination Score Published |
| Simulation module | `simulation_module` | Simulation Experiment Completed, Simulation Module Published, Simulation Module Released, Simulation Module Retired, Simulation Module Validated, Simulation Output Reviewed, Simulation Result Accepted, Simulation Run Scheduled, Simulation Run Started |
| Thesis | `thesis` | Thesis Accepted, Thesis Draft Registered, Thesis Resubmitted, Thesis Review Started, Thesis Revision Requested, Thesis Submitted |
| Simulation experiment result record | `student_simulation_experiment_result` | Simulation Experiment Completed, Simulation Output Reviewed, Simulation Result Accepted, Simulation Run Scheduled, Simulation Run Started |
| Assignment | `assignment` | Assignment Assigned, Assignment Grade Finalized, Assignment Graded, Assignment Regraded, Assignment Resubmitted, Assignment Revision Requested, Assignment Submitted |
| Instructor | `instructor` | Assignment Assigned, Assignment Grade Finalized, Assignment Graded, Assignment Regraded, Assignment Resubmitted, Assignment Revision Requested, Assignment Submitted |
| Assignment grading record | `assignment_grading` | Assignment Graded, Assignment Regraded |
| Course-design task | `task` | Design Task Approved, Design Task Closed, Design Task Created, Design Task Published |

## Physical objects and attributed activities

| Physical object | OT group | Activities linked to this object |
|---|---|---|
| `assignment` | Assignment | Assignment Assigned, Assignment Grade Finalized, Assignment Graded, Assignment Regraded, Assignment Resubmitted, Assignment Revision Requested, Assignment Submitted |
| `assignment_grading` | Assignment grading record | Assignment Graded, Assignment Regraded |
| `course` | Course | Course Assessment Completed, Course Grade Finalized, Course Offering Approved, Course Offering Closed, Course Offering Proposed, Course Offering Published, Course Registered, Course Started, Registration Approved, Registration Requested |
| `degree_examination_result` | Examination result record | Degree Examination Taken, Examination Checked In, Examination Result Reviewed, Examination Scheduled, Examination Score Published |
| `instructor` | Instructor | Assignment Assigned, Assignment Grade Finalized, Assignment Graded, Assignment Regraded, Assignment Resubmitted, Assignment Revision Requested, Assignment Submitted |
| `registration` | Student-course registration | Course Assessment Completed, Course Grade Finalized, Course Registered, Course Started, Registration Approved, Registration Requested |
| `simulation_module` | Simulation module | Simulation Experiment Completed, Simulation Module Published, Simulation Module Released, Simulation Module Retired, Simulation Module Validated, Simulation Output Reviewed, Simulation Result Accepted, Simulation Run Scheduled, Simulation Run Started |
| `student` | Student | Assignment Assigned, Assignment Grade Finalized, Assignment Graded, Assignment Regraded, Assignment Resubmitted, Assignment Revision Requested, Assignment Submitted, Course Assessment Completed, Course Grade Finalized, Course Registered, Course Started, Degree Examination Taken, Examination Checked In, Examination Result Reviewed, Examination Scheduled, Examination Score Published, Registration Approved, Registration Requested, Simulation Experiment Completed, Simulation Output Reviewed, Simulation Result Accepted, Simulation Run Scheduled, Simulation Run Started, Thesis Accepted, Thesis Draft Registered, Thesis Resubmitted, Thesis Review Started, Thesis Revision Requested, Thesis Submitted |
| `student_simulation_experiment_result` | Simulation experiment result record | Simulation Experiment Completed, Simulation Output Reviewed, Simulation Result Accepted, Simulation Run Scheduled, Simulation Run Started |
| `task` | Course-design task | Design Task Approved, Design Task Closed, Design Task Created, Design Task Published |
| `thesis` | Thesis | Thesis Accepted, Thesis Draft Registered, Thesis Resubmitted, Thesis Review Started, Thesis Revision Requested, Thesis Submitted |
