-- Q04 evaluator-only reference. Do not supply to the model.
SELECT case_id, activity, timestamp FROM (
SELECT t.turn_id AS case_id, 'Landing' AS activity, m.value_at AS timestamp
FROM movement_reports m
JOIN turnarounds t ON t.inbound_id=m.flight_id
WHERE m.kind='LAND'
UNION ALL
SELECT t.turn_id AS case_id, 'In-block' AS activity, m.value_at AS timestamp
FROM movement_reports m
JOIN turnarounds t ON t.inbound_id=m.flight_id
WHERE m.kind='IN'
UNION ALL
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
SELECT t.turn_id AS case_id, 'Boarding Start' AS activity, b.started_at AS timestamp
FROM boarding_sessions b
JOIN turnarounds t ON t.outbound_id=b.flight_id
UNION ALL
SELECT t.turn_id AS case_id, 'Boarding Close' AS activity, b.closed_at AS timestamp
FROM boarding_sessions b
JOIN turnarounds t ON t.outbound_id=b.flight_id
UNION ALL
SELECT t.turn_id AS case_id, 'Aircraft Ready' AS activity, t.ready_at AS timestamp
FROM turnarounds t
UNION ALL
SELECT t.turn_id AS case_id, 'Off-block' AS activity, m.value_at AS timestamp
FROM movement_reports m
JOIN turnarounds t ON t.outbound_id=m.flight_id
WHERE m.kind='OUT'
UNION ALL
SELECT t.turn_id AS case_id, 'Take-off' AS activity, m.value_at AS timestamp
FROM movement_reports m
JOIN turnarounds t ON t.outbound_id=m.flight_id
WHERE m.kind='AIR'
) ORDER BY case_id, timestamp, activity;
