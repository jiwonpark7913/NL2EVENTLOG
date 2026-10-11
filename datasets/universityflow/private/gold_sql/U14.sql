SELECT * FROM (SELECT 'THESIS:' || thesis_id event_id, student_id case_id, 'Thesis Submitted' activity, submission_date timestamp FROM thesis) ORDER BY case_id,timestamp,event_id;
