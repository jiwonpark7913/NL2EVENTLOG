-- Q03 evaluator-only reference. Do not supply to the model.
SELECT case_id, activity, timestamp FROM (
SELECT b.flight_id AS case_id, 'Boarding Start' AS activity, b.started_at AS timestamp
FROM boarding_sessions b
JOIN turnarounds t ON t.outbound_id=b.flight_id
UNION ALL
SELECT b.flight_id AS case_id, 'Boarding Close' AS activity, b.closed_at AS timestamp
FROM boarding_sessions b
JOIN turnarounds t ON t.outbound_id=b.flight_id
UNION ALL
SELECT t.outbound_id AS case_id, 'Baggage Loading Close' AS activity, j.finished_at AS timestamp
FROM handling_jobs j
JOIN turnarounds t ON t.turn_id=j.turn_id
WHERE j.job_code='BL'
UNION ALL
SELECT t.outbound_id AS case_id, 'Aircraft Ready' AS activity, t.ready_at AS timestamp
FROM turnarounds t
UNION ALL
SELECT m.flight_id AS case_id, 'Off-block' AS activity, m.value_at AS timestamp
FROM movement_reports m
JOIN turnarounds t ON t.outbound_id=m.flight_id
WHERE m.kind='OUT'
) ORDER BY case_id, timestamp, activity;
