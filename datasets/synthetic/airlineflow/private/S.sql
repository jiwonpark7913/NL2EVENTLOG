SELECT * FROM (
SELECT visit_id AS case_id, CASE point WHEN 'Q' THEN 'Queue entered' WHEN 'S' THEN 'Screening started' WHEN 'C' THEN 'Screening completed' END AS activity, observed_at AS timestamp FROM security_events WHERE point IN ('Q','S','C')
) ORDER BY case_id, timestamp, activity;