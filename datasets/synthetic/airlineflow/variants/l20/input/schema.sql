CREATE TABLE flights (flight_id TEXT PRIMARY KEY NOT NULL, flight_no TEXT NOT NULL, scheduled_offblock TEXT NOT NULL, scheduled_inblock TEXT NOT NULL);

CREATE TABLE turnarounds (turn_id TEXT PRIMARY KEY NOT NULL, inbound_id TEXT NOT NULL UNIQUE REFERENCES flights(flight_id), outbound_id TEXT NOT NULL UNIQUE REFERENCES flights(flight_id), handling_started_at TEXT NOT NULL, ready_at TEXT NOT NULL, CHECK(inbound_id <> outbound_id));

CREATE TABLE boarding_sessions (session_id TEXT PRIMARY KEY NOT NULL, flight_id TEXT NOT NULL UNIQUE REFERENCES flights(flight_id), started_at TEXT NOT NULL, closed_at TEXT NOT NULL);

CREATE TABLE handling_jobs (job_id TEXT PRIMARY KEY NOT NULL, turn_id TEXT NOT NULL REFERENCES turnarounds(turn_id), job_code TEXT NOT NULL, started_at TEXT NOT NULL, finished_at TEXT NOT NULL, posted_at TEXT NOT NULL, service_provider_code TEXT, priority_code TEXT, work_zone_code TEXT);

CREATE TABLE movement_reports (report_id TEXT PRIMARY KEY NOT NULL, flight_id TEXT NOT NULL REFERENCES flights(flight_id), kind TEXT NOT NULL, value_at TEXT NOT NULL, received_at TEXT NOT NULL, source_code TEXT, validation_code TEXT, message_format_code TEXT);

CREATE TABLE bookings (booking_id TEXT PRIMARY KEY NOT NULL, booked_at TEXT NOT NULL, record_locator TEXT NOT NULL, sales_channel TEXT NOT NULL, booking_status TEXT NOT NULL, currency_code TEXT NOT NULL, base_fare_amount INTEGER NOT NULL, tax_amount INTEGER NOT NULL, total_amount INTEGER NOT NULL, payment_status TEXT NOT NULL);

CREATE TABLE passengers (passenger_id TEXT PRIMARY KEY NOT NULL, display_name TEXT NOT NULL, date_of_birth DATE NOT NULL, nationality_code TEXT CHECK (nationality_code IS NULL OR length(nationality_code)=2), gender_code TEXT NOT NULL CHECK (gender_code IN ('MALE','FEMALE','UNKNOWN')), given_name TEXT NOT NULL, family_name TEXT NOT NULL, preferred_language TEXT NOT NULL, loyalty_tier TEXT);

CREATE TABLE tickets (ticket_id TEXT PRIMARY KEY NOT NULL, booking_id TEXT NOT NULL REFERENCES bookings(booking_id), passenger_id TEXT NOT NULL REFERENCES passengers(passenger_id), ticket_number TEXT NOT NULL, ticket_status TEXT NOT NULL, issuing_channel TEXT NOT NULL, currency_code TEXT NOT NULL, base_fare_amount INTEGER NOT NULL, tax_amount INTEGER NOT NULL, total_amount INTEGER NOT NULL, fare_product TEXT NOT NULL);

CREATE TABLE passenger_legs (leg_id TEXT PRIMARY KEY NOT NULL, ticket_id TEXT NOT NULL REFERENCES tickets(ticket_id), flight_id TEXT NOT NULL REFERENCES flights(flight_id), coupon_no INTEGER NOT NULL, booking_class TEXT NOT NULL, cabin_class TEXT NOT NULL, fare_basis TEXT NOT NULL, seat_no TEXT, checkin_sequence INTEGER, departure_status TEXT NOT NULL, checked_bag_allowance INTEGER NOT NULL, segment_base_fare INTEGER NOT NULL, segment_tax INTEGER NOT NULL, UNIQUE(ticket_id,flight_id));

CREATE TABLE passenger_actions (action_id TEXT PRIMARY KEY NOT NULL, leg_id TEXT NOT NULL REFERENCES passenger_legs(leg_id), action_code TEXT NOT NULL, action_at TEXT NOT NULL, station_code TEXT NOT NULL, processing_channel TEXT NOT NULL, terminal_code TEXT, device_id TEXT, result_code TEXT NOT NULL, rejection_reason TEXT);

CREATE TABLE bag_legs (bag_leg_id TEXT PRIMARY KEY NOT NULL, leg_id TEXT NOT NULL REFERENCES passenger_legs(leg_id), bag_tag TEXT NOT NULL, tag_license_plate TEXT NOT NULL, weight_kg REAL NOT NULL, bag_type TEXT NOT NULL, origin_station TEXT NOT NULL, destination_station TEXT NOT NULL, handling_status TEXT NOT NULL);

CREATE TABLE bag_scans (scan_id TEXT PRIMARY KEY NOT NULL, bag_leg_id TEXT NOT NULL REFERENCES bag_legs(bag_leg_id), scan_code TEXT NOT NULL, scanned_at TEXT NOT NULL, station_code TEXT NOT NULL, location_code TEXT NOT NULL, device_id TEXT NOT NULL, capture_method TEXT NOT NULL, container_id TEXT, source_system TEXT NOT NULL);

CREATE TABLE checkpoints (checkpoint_id TEXT PRIMARY KEY NOT NULL, zone TEXT NOT NULL, terminal_code TEXT NOT NULL, checkpoint_name TEXT NOT NULL, checkpoint_type TEXT NOT NULL, lane_count INTEGER NOT NULL, operational_status TEXT NOT NULL);

CREATE TABLE security_visits (visit_id TEXT PRIMARY KEY NOT NULL, leg_id TEXT NOT NULL REFERENCES passenger_legs(leg_id), checkpoint_id TEXT NOT NULL REFERENCES checkpoints(checkpoint_id), queue_type TEXT NOT NULL, lane_no INTEGER, visit_status TEXT NOT NULL);

CREATE TABLE security_events (event_id TEXT PRIMARY KEY NOT NULL, visit_id TEXT NOT NULL REFERENCES security_visits(visit_id), point TEXT NOT NULL, observed_at TEXT NOT NULL, received_at TEXT NOT NULL, station_code TEXT NOT NULL, source_system TEXT NOT NULL, device_id TEXT NOT NULL, capture_method TEXT NOT NULL, quality_code TEXT NOT NULL);

CREATE TABLE airlines (airline_id TEXT PRIMARY KEY NOT NULL, name TEXT NOT NULL, carrier_code TEXT NOT NULL, country_code TEXT NOT NULL, home_base TEXT NOT NULL, carrier_type TEXT NOT NULL);

CREATE TABLE airports (airport_id TEXT PRIMARY KEY NOT NULL, city TEXT NOT NULL, airport_name TEXT NOT NULL, icao_code TEXT NOT NULL, country_code TEXT NOT NULL, timezone TEXT NOT NULL, airport_type TEXT NOT NULL);

CREATE TABLE aircraft (tail_id TEXT PRIMARY KEY NOT NULL, airline_id TEXT NOT NULL REFERENCES airlines(airline_id), model TEXT NOT NULL, registration_ref TEXT NOT NULL, manufacturer TEXT NOT NULL, aircraft_type_code TEXT NOT NULL, manufacture_year INTEGER NOT NULL, seat_capacity INTEGER NOT NULL, fleet_status TEXT NOT NULL);

CREATE TABLE employees (employee_id TEXT PRIMARY KEY NOT NULL, airline_id TEXT NOT NULL REFERENCES airlines(airline_id), role TEXT NOT NULL, employee_name TEXT NOT NULL, department TEXT NOT NULL, base_station TEXT NOT NULL, qualification_status TEXT NOT NULL, employment_status TEXT NOT NULL);

CREATE TABLE flight_dispatch (dispatch_id TEXT PRIMARY KEY NOT NULL, flight_id TEXT NOT NULL UNIQUE REFERENCES flights(flight_id), tail_id TEXT NOT NULL REFERENCES aircraft(tail_id), origin TEXT NOT NULL REFERENCES airports(airport_id), destination TEXT NOT NULL REFERENCES airports(airport_id), dispatcher_id TEXT NOT NULL REFERENCES employees(employee_id), assigned_at TEXT NOT NULL, operation_type TEXT NOT NULL, alternate_station TEXT NOT NULL, planned_fuel_kg INTEGER NOT NULL, minimum_fuel_kg INTEGER NOT NULL, release_status TEXT NOT NULL, dispatch_system TEXT NOT NULL);
