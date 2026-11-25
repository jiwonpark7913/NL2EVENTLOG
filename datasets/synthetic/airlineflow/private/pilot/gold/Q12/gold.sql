-- Q12 evaluator-only reference. Do not supply to model.
SELECT case_id, activity, timestamp FROM (
SELECT b.flight_id AS case_id, 'Boarding Start' AS activity, b.started_at AS timestamp
FROM boarding_sessions b
JOIN turnarounds t ON t.outbound_id=b.flight_id
UNION ALL
SELECT b.flight_id AS case_id, 'Boarding Close' AS activity, b.closed_at AS timestamp
FROM boarding_sessions b
JOIN turnarounds t ON t.outbound_id=b.flight_id
UNION ALL
SELECT m.flight_id AS case_id, 'Off-block' AS activity, m.value_at AS timestamp
FROM movement_reports m
JOIN turnarounds t ON t.outbound_id=m.flight_id
WHERE m.kind='OUT'
UNION ALL
SELECT m.flight_id AS case_id, 'Take-off' AS activity, m.value_at AS timestamp
FROM movement_reports m
JOIN turnarounds t ON t.outbound_id=m.flight_id
WHERE m.kind='AIR'
) ORDER BY case_id, timestamp, activity;
