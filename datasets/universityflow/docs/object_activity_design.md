# Universityflow object activities and scenarios

- Original source requirements, columns and keys remain preserved.
- Every action below is an explicitly authored domain extension; these stages were not present in the source schemas.
- Each added history row records an actual activity, occurrence time, outcome and a declared FK to its object.
- Conditional revision branches and incomplete cases are intentional. Atomic grading/operation records remain auxiliary logs.
- Master-object views aggregate linked work; they do not assert one chronological causal process across unrelated jobs.

| Object | Added activities | Situation | Storage |
|---|---|---|---|
| registration | Registration Requested → Registration Approved → Course Started → Course Assessment Completed → Course Grade Finalized | Actual ordered actions; every seventh object stops before closure. Assignment/thesis revision branches occur in one third of objects. | registration_activity |
| degree_examination_result | Examination Scheduled → Examination Checked In → Examination Score Published → Examination Result Reviewed | Actual ordered actions; every seventh object stops before closure. Assignment/thesis revision branches occur in one third of objects. | degree_examination_result_activity |
| assignment | Assignment Assigned → Assignment Submitted → Assignment Revision Requested → Assignment Resubmitted → Assignment Grade Finalized → Assignment Regraded | Actual ordered actions; every seventh object stops before closure. Assignment/thesis revision branches occur in one third of objects. | assignment_activity |
| simulation_module | Simulation Module Published → Simulation Module Validated → Simulation Module Released → Simulation Module Retired | Actual ordered actions; every seventh object stops before closure. Assignment/thesis revision branches occur in one third of objects. | simulation_module_activity |
| student_simulation_experiment_result | Simulation Run Scheduled → Simulation Run Started → Simulation Output Reviewed → Simulation Result Accepted | Actual ordered actions; every seventh object stops before closure. Assignment/thesis revision branches occur in one third of objects. | student_simulation_experiment_result_activity |
| thesis | Thesis Draft Registered → Thesis Review Started → Thesis Revision Requested → Thesis Resubmitted → Thesis Accepted | Actual ordered actions; every seventh object stops before closure. Assignment/thesis revision branches occur in one third of objects. | thesis_activity |
| course | Course Offering Proposed → Course Offering Approved → Course Offering Published → Course Offering Closed | Actual ordered actions; every seventh object stops before closure. Assignment/thesis revision branches occur in one third of objects. | course_activity |
| task | Design Task Created → Design Task Approved → Design Task Published → Design Task Closed | Actual ordered actions; every seventh object stops before closure. Assignment/thesis revision branches occur in one third of objects. | task_activity |

- The full ES unions the original milestone sources and the new typed activity histories, then applies explicit event-to-case links.
- Related goods/workers, students/instructors and parent materials receive an event only through a documented business relationship.
- `lifecycle_case_link` is a generated extraction index with validated object identities; it is not an additional business object.
