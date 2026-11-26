-- evaluator-only Q15
SELECT case_id,activity,timestamp FROM (
SELECT s2.flight_id AS case_id, 'Bag Accepted' AS activity, s0.scanned_at AS timestamp FROM bag_scans s0 JOIN bag_legs s1 ON s0.bag_leg_id=s1.bag_leg_id JOIN passenger_legs s2 ON s1.leg_id=s2.leg_id WHERE s0.scan_code='B101'
UNION ALL
SELECT s2.flight_id AS case_id, 'Bag Loaded' AS activity, s0.scanned_at AS timestamp FROM bag_scans s0 JOIN bag_legs s1 ON s0.bag_leg_id=s1.bag_leg_id JOIN passenger_legs s2 ON s1.leg_id=s2.leg_id WHERE s0.scan_code='B204'
) ORDER BY case_id,timestamp,activity;
