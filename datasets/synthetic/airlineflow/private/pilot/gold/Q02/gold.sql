-- Q02 evaluator-only reference. Do not supply to the model.
SELECT case_id, activity, timestamp FROM (
SELECT j.job_id AS case_id, 'Job Start' AS activity, j.started_at AS timestamp
FROM handling_jobs j
UNION ALL
SELECT j.job_id AS case_id, 'Job Complete' AS activity, j.finished_at AS timestamp
FROM handling_jobs j
) ORDER BY case_id, timestamp, activity;
