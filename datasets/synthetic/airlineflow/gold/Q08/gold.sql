-- Q08 evaluator-only reference. Do not supply to the model.
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
