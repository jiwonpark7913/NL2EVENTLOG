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
