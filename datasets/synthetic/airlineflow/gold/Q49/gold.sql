-- evaluator-only Q49
SELECT case_id,activity,timestamp FROM (
SELECT s0.bag_leg_id AS case_id, 'Bag Accepted' AS activity, s0.scanned_at AS timestamp FROM bag_scans s0 WHERE s0.scan_code='B101'
UNION ALL
SELECT s0.bag_leg_id AS case_id, 'Bag Loaded' AS activity, s0.scanned_at AS timestamp FROM bag_scans s0 WHERE s0.scan_code='B204'
) ORDER BY case_id,timestamp,activity;
