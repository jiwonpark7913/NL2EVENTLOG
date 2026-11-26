-- Q07 evaluator-only reference. Do not supply to the model.
SELECT case_id, activity, timestamp FROM (
SELECT t.outbound_id AS case_id, 'Baggage Unloading Complete' AS activity, j.finished_at AS timestamp
FROM handling_jobs j
JOIN turnarounds t ON t.turn_id=j.turn_id
WHERE j.job_code='UL'
UNION ALL
SELECT t.outbound_id AS case_id, 'Cabin Cleaning Complete' AS activity, j.finished_at AS timestamp
FROM handling_jobs j
JOIN turnarounds t ON t.turn_id=j.turn_id
WHERE j.job_code='CL'
UNION ALL
SELECT t.outbound_id AS case_id, 'Refuelling Complete' AS activity, j.finished_at AS timestamp
FROM handling_jobs j
JOIN turnarounds t ON t.turn_id=j.turn_id
WHERE j.job_code='FU'
UNION ALL
SELECT t.outbound_id AS case_id, 'Catering Loading Complete' AS activity, j.finished_at AS timestamp
FROM handling_jobs j
JOIN turnarounds t ON t.turn_id=j.turn_id
WHERE j.job_code='CA'
UNION ALL
SELECT t.outbound_id AS case_id, 'Baggage Loading Close' AS activity, j.finished_at AS timestamp
FROM handling_jobs j
JOIN turnarounds t ON t.turn_id=j.turn_id
WHERE j.job_code='BL'
) ORDER BY case_id, timestamp, activity;
