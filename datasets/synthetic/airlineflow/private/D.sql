SELECT * FROM (
SELECT b.flight_id AS case_id, 'Boarding started' AS activity,b.started_at AS timestamp FROM boarding_sessions b JOIN turnarounds t ON t.outbound_id=b.flight_id
UNION ALL SELECT b.flight_id,'Boarding closed',b.closed_at FROM boarding_sessions b JOIN turnarounds t ON t.outbound_id=b.flight_id
UNION ALL SELECT t.outbound_id,'Baggage loading closed',j.finished_at FROM handling_jobs j JOIN turnarounds t ON t.turn_id=j.turn_id WHERE j.job_code='BL'
UNION ALL SELECT outbound_id,'Aircraft ready',ready_at FROM turnarounds
UNION ALL SELECT m.flight_id,'Off-block',m.value_at FROM movement_reports m JOIN turnarounds t ON t.outbound_id=m.flight_id WHERE m.kind='OUT'
) ORDER BY case_id,timestamp,activity;
