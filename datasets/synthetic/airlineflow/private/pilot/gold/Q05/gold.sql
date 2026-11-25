-- Q05 evaluator-only reference. Do not supply to the model.
SELECT case_id, activity, timestamp FROM (
SELECT t.turn_id AS case_id, 'Handling Start' AS activity, t.handling_started_at AS timestamp
FROM turnarounds t
UNION ALL
SELECT j.turn_id AS case_id, 'Cabin Cleaning Complete' AS activity, j.finished_at AS timestamp
FROM handling_jobs j
WHERE j.job_code='CL'
UNION ALL
SELECT j.turn_id AS case_id, 'Refuelling Complete' AS activity, j.finished_at AS timestamp
FROM handling_jobs j
WHERE j.job_code='FU'
UNION ALL
SELECT t.turn_id AS case_id, 'Aircraft Ready' AS activity, t.ready_at AS timestamp
FROM turnarounds t
) ORDER BY case_id, timestamp, activity;
