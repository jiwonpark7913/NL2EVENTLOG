-- Q11 evaluator-only reference. Do not supply to the model.
SELECT case_id, activity, timestamp FROM (
SELECT b.session_id AS case_id, 'Boarding Start' AS activity, b.started_at AS timestamp
FROM boarding_sessions b
UNION ALL
SELECT b.session_id AS case_id, 'Boarding Close' AS activity, b.closed_at AS timestamp
FROM boarding_sessions b
) ORDER BY case_id, timestamp, activity;
