-- evaluator-only Q37
SELECT case_id,activity,timestamp FROM (
SELECT s0.turn_id AS case_id, 'Cabin Cleaning Start' AS activity, s0.started_at AS timestamp FROM handling_jobs s0 WHERE s0.job_code='CL'
UNION ALL
SELECT s0.turn_id AS case_id, 'Cabin Cleaning Complete' AS activity, s0.finished_at AS timestamp FROM handling_jobs s0 WHERE s0.job_code='CL'
) ORDER BY case_id,timestamp,activity;
