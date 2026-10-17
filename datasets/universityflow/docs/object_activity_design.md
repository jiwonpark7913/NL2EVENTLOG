# Object activity storage

- Actual one-time milestone columns and retained row histories are used together. Events are extracted once, not mirrored in two places.
- Original event IDs and occurrence times are preserved. All added fields are authored synthetic extensions.

| Object | Activities | Storage |
|---|---|---|
| registration | Registration Requested; Registration Approved; Course Started; Course Assessment Completed; Course Grade Finalized | Actual milestone columns on registration |
| degree_examination_result | Examination Scheduled; Examination Checked In; Examination Score Published; Examination Result Reviewed | Actual milestone columns on degree_examination_result |
| assignment | Assignment Assigned; Assignment Submitted; Assignment Revision Requested; Assignment Resubmitted; Assignment Grade Finalized; Assignment Regraded | Actual milestone columns on assignment; remaining repeatable actions stay in assignment_activity |
| simulation_module | Simulation Module Published; Simulation Module Validated; Simulation Module Released; Simulation Module Retired | simulation_module_activity |
| student_simulation_experiment_result | Simulation Run Scheduled; Simulation Run Started; Simulation Output Reviewed; Simulation Result Accepted | student_simulation_experiment_result_activity |
| thesis | Thesis Draft Registered; Thesis Review Started; Thesis Revision Requested; Thesis Resubmitted; Thesis Accepted | Actual milestone columns on thesis; remaining repeatable actions stay in thesis_activity |
| course | Course Offering Proposed; Course Offering Approved; Course Offering Published; Course Offering Closed | course_activity |
| task | Design Task Created; Design Task Approved; Design Task Published; Design Task Closed | task_activity |
