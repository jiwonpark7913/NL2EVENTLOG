-- Q02 evaluator-only reference. Do not supply to the model.
SELECT case_id, activity, timestamp FROM (
SELECT t.turn_id AS case_id, 'Handling Start' AS activity, t.handling_started_at AS timestamp
FROM turnarounds t
UNION ALL
SELECT j.turn_id AS case_id, 'Disembarkation Start' AS activity, j.started_at AS timestamp
FROM handling_jobs j
WHERE j.job_code='DP'
UNION ALL
SELECT j.turn_id AS case_id, 'Disembarkation Complete' AS activity, j.finished_at AS timestamp
FROM handling_jobs j
WHERE j.job_code='DP'
UNION ALL
SELECT j.turn_id AS case_id, 'Baggage Unloading Start' AS activity, j.started_at AS timestamp
FROM handling_jobs j
WHERE j.job_code='UL'
UNION ALL
SELECT j.turn_id AS case_id, 'Baggage Unloading Complete' AS activity, j.finished_at AS timestamp
FROM handling_jobs j
WHERE j.job_code='UL'
UNION ALL
SELECT j.turn_id AS case_id, 'Cabin Cleaning Start' AS activity, j.started_at AS timestamp
FROM handling_jobs j
WHERE j.job_code='CL'
UNION ALL
SELECT j.turn_id AS case_id, 'Cabin Cleaning Complete' AS activity, j.finished_at AS timestamp
FROM handling_jobs j
WHERE j.job_code='CL'
UNION ALL
SELECT j.turn_id AS case_id, 'Refuelling Start' AS activity, j.started_at AS timestamp
FROM handling_jobs j
WHERE j.job_code='FU'
UNION ALL
SELECT j.turn_id AS case_id, 'Refuelling Complete' AS activity, j.finished_at AS timestamp
FROM handling_jobs j
WHERE j.job_code='FU'
UNION ALL
SELECT j.turn_id AS case_id, 'Catering Loading Start' AS activity, j.started_at AS timestamp
FROM handling_jobs j
WHERE j.job_code='CA'
UNION ALL
SELECT j.turn_id AS case_id, 'Catering Loading Complete' AS activity, j.finished_at AS timestamp
FROM handling_jobs j
WHERE j.job_code='CA'
UNION ALL
SELECT j.turn_id AS case_id, 'Baggage Loading Start' AS activity, j.started_at AS timestamp
FROM handling_jobs j
WHERE j.job_code='BL'
UNION ALL
SELECT j.turn_id AS case_id, 'Baggage Loading Close' AS activity, j.finished_at AS timestamp
FROM handling_jobs j
WHERE j.job_code='BL'
UNION ALL
SELECT t.turn_id AS case_id, 'Aircraft Ready' AS activity, t.ready_at AS timestamp
FROM turnarounds t
) ORDER BY case_id, timestamp, activity;
