SELECT * FROM (
SELECT leg_id AS case_id, CASE action_code WHEN 'CK' THEN 'Check-in completed' WHEN 'BD' THEN 'Boarding confirmed' END AS activity, action_at AS timestamp FROM passenger_actions WHERE action_code IN ('CK','BD')
UNION ALL SELECT l.leg_id AS case_id, CASE s.scan_code WHEN 'ACC' THEN 'Bag accepted' WHEN 'LD' THEN 'Bag loaded' END AS activity, s.scanned_at AS timestamp FROM bag_scans s JOIN bag_legs l ON s.bag_leg_id=l.bag_leg_id WHERE s.scan_code IN ('ACC','LD')
) ORDER BY case_id, timestamp, activity;