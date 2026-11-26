SELECT bag_leg_id AS case_id, 'B204' AS activity, scanned_at AS timestamp FROM bag_scans WHERE scan_code='B204' ORDER BY case_id,timestamp,activity;
