SELECT * FROM (
SELECT leg_id AS case_id, CASE action_code WHEN 'CK' THEN 'Check-in completed' WHEN 'BD' THEN 'Boarding confirmed' END AS activity, action_at AS timestamp FROM passenger_actions WHERE action_code IN ('CK','BD')
) ORDER BY case_id, timestamp, activity;