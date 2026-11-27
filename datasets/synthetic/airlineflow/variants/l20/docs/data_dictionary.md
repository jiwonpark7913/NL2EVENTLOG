# L20 — data dictionary

[Back to variant](../README.md) · [Original JSON](../input/data_dictionary.json)

20 tables · 168 columns · 80,289 rows

## `aircraft`

Register of individual aircraft. (5 rows)

| Column | Declaration | Description |
|---|---|---|
| `tail_id` | `TEXT PRIMARY KEY NOT NULL` | Individual aircraft registration identifier. |
| `airline_id` | `TEXT NOT NULL REFERENCES airlines(airline_id)` | Operating airline. |
| `model` | `TEXT NOT NULL` | Aircraft model. |
| `registration_ref` | `TEXT NOT NULL` | Fictional internal registration reference; not a real civil-aircraft registration. |
| `manufacturer` | `TEXT NOT NULL` | Manufacturer associated with the existing aircraft model. |
| `aircraft_type_code` | `TEXT NOT NULL` | Aircraft family type designation used in this model. |
| `manufacture_year` | `INTEGER NOT NULL` | Synthetic manufacture year. |
| `seat_capacity` | `INTEGER NOT NULL` | Modeled total installed seat capacity; passenger records cover a sample, not the full manifest. |
| `fleet_status` | `TEXT NOT NULL` | Aircraft master-data operating status. |

## `airlines`

Register of operating airlines. (2 rows)

| Column | Declaration | Description |
|---|---|---|
| `airline_id` | `TEXT PRIMARY KEY NOT NULL` | Airline identifier. |
| `name` | `TEXT NOT NULL` | Synthetic airline name. |
| `carrier_code` | `TEXT NOT NULL` | Synthetic two-character carrier prefix used by the fixture flight numbers; not an assertion of real IATA assignment. |
| `country_code` | `TEXT NOT NULL` | Synthetic carrier registration country, ISO 3166-1 alpha-2. |
| `home_base` | `TEXT NOT NULL` | Three-letter modeled home airport code. |
| `carrier_type` | `TEXT NOT NULL` | Commercial service category used in the synthetic register. |

## `airports`

Airport register. (3 rows)

| Column | Declaration | Description |
|---|---|---|
| `airport_id` | `TEXT PRIMARY KEY NOT NULL` | Airport code. |
| `city` | `TEXT NOT NULL` | City name. |
| `airport_name` | `TEXT NOT NULL` | Published airport name. |
| `icao_code` | `TEXT NOT NULL` | Four-letter ICAO location indicator. |
| `country_code` | `TEXT NOT NULL` | ISO 3166-1 alpha-2 country code. |
| `timezone` | `TEXT NOT NULL` | IANA timezone of the airport. |
| `airport_type` | `TEXT NOT NULL` | Airport category: international commercial airport. |

## `bag_legs`

Transport records for a sample of checked bags associated with passenger flight legs. (5,887 rows)

| Column | Declaration | Description |
|---|---|---|
| `bag_leg_id` | `TEXT PRIMARY KEY NOT NULL` | Baggage transport record identifier. |
| `leg_id` | `TEXT NOT NULL REFERENCES passenger_legs(leg_id)` | Passenger flight leg associated with the checked bag. |
| `bag_tag` | `TEXT NOT NULL` | Baggage tag identifier. |
| `tag_license_plate` | `TEXT NOT NULL` | Ten-digit synthetic bag-tag license plate using dummy carrier prefix 0999; not an issued tag. |
| `weight_kg` | `REAL NOT NULL` | Measured checked-bag mass in kilograms, synthetic. |
| `bag_type` | `TEXT NOT NULL` | Physical baggage category: STANDARD, OVERSIZE or SPECIAL. |
| `origin_station` | `TEXT NOT NULL` | Three-letter airport code of the associated operating leg's origin. |
| `destination_station` | `TEXT NOT NULL` | Three-letter airport code of the associated operating leg's destination. |
| `handling_status` | `TEXT NOT NULL` | Last observed tracking state: ACCEPTED or LOADED. No arrival or delivery is inferred. |

## `bag_scans`

Individual baggage tracking records for the checked bags represented in the dataset. (11,595 rows)

| Column | Declaration | Description |
|---|---|---|
| `scan_id` | `TEXT PRIMARY KEY NOT NULL` | Baggage scan record identifier. |
| `bag_leg_id` | `TEXT NOT NULL REFERENCES bag_legs(bag_leg_id)` | Baggage transport record associated with the scan. |
| `scan_code` | `TEXT NOT NULL` | Baggage tracking event code. B101 indicates that a bag has been accepted. B204 indicates that a bag has been loaded into the aircraft hold. |
| `scanned_at` | `TEXT NOT NULL` | Date and time of the baggage scan. |
| `station_code` | `TEXT NOT NULL` | Airport where tracking observation was recorded. |
| `location_code` | `TEXT NOT NULL` | Local tracking location: BAG_DROP or AIRCRAFT_LOADING. |
| `device_id` | `TEXT NOT NULL` | Synthetic scanner identifier local to the station and location. |
| `capture_method` | `TEXT NOT NULL` | Tracking capture method: BARCODE or RFID. |
| `container_id` | `TEXT` | Synthetic cart/container reference for a loading observation; NULL if not recorded. |
| `source_system` | `TEXT NOT NULL` | Local baggage reconciliation or handling system identifier. |

## `boarding_sessions`

Flight-level boarding sessions at the origin of every dated operating leg. One session per flight in this example; inbound legs also have origin boarding records. (200 rows)

| Column | Declaration | Description |
|---|---|---|
| `session_id` | `TEXT PRIMARY KEY NOT NULL` | Boarding session identifier. |
| `flight_id` | `TEXT NOT NULL UNIQUE REFERENCES flights(flight_id)` | Operating leg. |
| `started_at` | `TEXT NOT NULL` | Actual start of passenger boarding. |
| `closed_at` | `TEXT NOT NULL` | Actual close of passenger boarding. |

## `bookings`

Reservations for groups of travellers. (2,537 rows)

| Column | Declaration | Description |
|---|---|---|
| `booking_id` | `TEXT PRIMARY KEY NOT NULL` | Booking identifier. |
| `booked_at` | `TEXT NOT NULL` | Time the booking was created. |
| `record_locator` | `TEXT NOT NULL` | Six-character synthetic reservation reference (PNR locator), independent of the internal booking key. |
| `sales_channel` | `TEXT NOT NULL` | Channel used to place the reservation: WEB, MOBILE, AGENCY or CONTACT_CENTER. |
| `booking_status` | `TEXT NOT NULL` | Reservation status in the final snapshot; CONFIRMED means the itinerary was reserved. |
| `currency_code` | `TEXT NOT NULL` | ISO 4217 currency of the booking amounts. |
| `base_fare_amount` | `INTEGER NOT NULL` | Total base fare in whole KRW, summed over tickets in this booking. |
| `tax_amount` | `INTEGER NOT NULL` | Total taxes and fees in whole KRW, summed over tickets. |
| `total_amount` | `INTEGER NOT NULL` | Total fare plus taxes in whole KRW. |
| `payment_status` | `TEXT NOT NULL` | Payment state at the reservation snapshot. PAID indicates settled payment. |

## `checkpoints`

Airport security screening checkpoints. (3 rows)

| Column | Declaration | Description |
|---|---|---|
| `checkpoint_id` | `TEXT PRIMARY KEY NOT NULL` | Security checkpoint identifier. |
| `zone` | `TEXT NOT NULL` | Screening zone name. |
| `terminal_code` | `TEXT NOT NULL` | Synthetic terminal designation at the airport represented by zone. |
| `checkpoint_name` | `TEXT NOT NULL` | Human-readable synthetic checkpoint name. |
| `checkpoint_type` | `TEXT NOT NULL` | Passenger checkpoint category used in this benchmark. |
| `lane_count` | `INTEGER NOT NULL` | Number of modeled screening lanes at this checkpoint. |
| `operational_status` | `TEXT NOT NULL` | Checkpoint availability in the master-data snapshot. |

## `employees`

Register of airline employees. (2 rows)

| Column | Declaration | Description |
|---|---|---|
| `employee_id` | `TEXT PRIMARY KEY NOT NULL` | Employee identifier. |
| `airline_id` | `TEXT NOT NULL REFERENCES airlines(airline_id)` | Employing airline. |
| `role` | `TEXT NOT NULL` | Job role. |
| `employee_name` | `TEXT NOT NULL` | Fictional employee display name. |
| `department` | `TEXT NOT NULL` | Organizational unit responsible for the employee's role. |
| `base_station` | `TEXT NOT NULL` | Modeled duty base airport code. |
| `qualification_status` | `TEXT NOT NULL` | Synthetic qualification snapshot, not an actual license or regulatory certification. |
| `employment_status` | `TEXT NOT NULL` | Employment master-data status. |

## `flight_dispatch`

Assignments of operating resources to individual dated legs. (200 rows)

| Column | Declaration | Description |
|---|---|---|
| `dispatch_id` | `TEXT PRIMARY KEY NOT NULL` | Dispatch assignment identifier. |
| `flight_id` | `TEXT NOT NULL UNIQUE REFERENCES flights(flight_id)` | Operating leg. |
| `tail_id` | `TEXT NOT NULL REFERENCES aircraft(tail_id)` | Assigned aircraft. |
| `origin` | `TEXT NOT NULL REFERENCES airports(airport_id)` | Departure airport. |
| `destination` | `TEXT NOT NULL REFERENCES airports(airport_id)` | Arrival airport. |
| `dispatcher_id` | `TEXT NOT NULL REFERENCES employees(employee_id)` | Assigned flight dispatcher. |
| `assigned_at` | `TEXT NOT NULL` | Time the assignment record was created. |
| `operation_type` | `TEXT NOT NULL` | Modeled flight rules category, IFR. |
| `alternate_station` | `TEXT NOT NULL` | Synthetic planned alternate airport code, not a dispatch recommendation. |
| `planned_fuel_kg` | `INTEGER NOT NULL` | Illustrative planned block fuel mass in kilograms; not an operational fuel calculation. |
| `minimum_fuel_kg` | `INTEGER NOT NULL` | Illustrative minimum fuel mass, not a certified dispatch value. |
| `release_status` | `TEXT NOT NULL` | Assignment snapshot status; ASSIGNED does not assert a signed dispatch release. |
| `dispatch_system` | `TEXT NOT NULL` | Local operations-control system identifier. |

## `flights`

Dated operating legs, including both inbound and outbound flights. Flight numbers repeat across dates. (200 rows)

| Column | Declaration | Description |
|---|---|---|
| `flight_id` | `TEXT PRIMARY KEY NOT NULL` | Operating leg identifier. |
| `flight_no` | `TEXT NOT NULL` | Published flight number. |
| `scheduled_offblock` | `TEXT NOT NULL` | Scheduled off-block time. |
| `scheduled_inblock` | `TEXT NOT NULL` | Scheduled in-block time. |

## `handling_jobs`

Ground handling work orders associated with aircraft turnarounds. (600 rows)

| Column | Declaration | Description |
|---|---|---|
| `job_id` | `TEXT PRIMARY KEY NOT NULL` | Handling job identifier. |
| `turn_id` | `TEXT NOT NULL REFERENCES turnarounds(turn_id)` | Aircraft turnaround associated with the job. |
| `job_code` | `TEXT NOT NULL` | Ground crews use CL for cabin cleaning and FU for refuelling. Catering loading is recorded under CA, and baggage loading under BL. DP identifies passenger disembarkation, while UL identifies baggage unloading. |
| `started_at` | `TEXT NOT NULL` | Actual start time of the assigned job. |
| `finished_at` | `TEXT NOT NULL` | Time at which completion of the assigned operation was confirmed. |
| `posted_at` | `TEXT NOT NULL` | Time at which the job record was posted to the system. |
| `service_provider_code` | `TEXT` | Provider assigned to the job. Codes are synthetic and cover airline ground operations and contracted providers. |
| `priority_code` | `TEXT` | Dispatch priority assigned to the job. STANDARD, HIGH and CRITICAL are synthetic operational categories. |
| `work_zone_code` | `TEXT` | Zone where the work was carried out, such as aircraft cabin, cargo hold, ramp or passenger bridge. |

## `movement_reports`

Estimated and actual movement messages for operating legs. Actual OUT and AIR refer to the origin; LAND and IN refer to the destination. Both inbound and outbound legs have all four actual movements; EST estimates origin off-block. (1,000 rows)

| Column | Declaration | Description |
|---|---|---|
| `report_id` | `TEXT PRIMARY KEY NOT NULL` | Movement report identifier. |
| `flight_id` | `TEXT NOT NULL REFERENCES flights(flight_id)` | Operating leg. |
| `kind` | `TEXT NOT NULL` | EST = estimated off-block; OUT = actual off-block; AIR = actual take-off; LAND = actual landing; IN = actual in-block. |
| `value_at` | `TEXT NOT NULL` | Timestamp represented by the message. |
| `received_at` | `TEXT NOT NULL` | Time the message was received. |
| `source_code` | `TEXT` | Origin of the report, such as an airport operations database (AODB), a ground handling system (GHS), or an aircraft communications feed (ACARS). |
| `validation_code` | `TEXT` | How a report was checked. AUTO_CHECKED means automated checks. OPS_REVIEWED means operations staff reviewed it. |
| `message_format_code` | `TEXT` | Format of the ingested record, such as AIDX, MVT or a local system record. |

## `passenger_actions`

Departure processing records for passenger flight legs. (14,031 rows)

| Column | Declaration | Description |
|---|---|---|
| `action_id` | `TEXT PRIMARY KEY NOT NULL` | Passenger action identifier. |
| `leg_id` | `TEXT NOT NULL REFERENCES passenger_legs(leg_id)` | Passenger flight leg. |
| `action_code` | `TEXT NOT NULL` | Once check-in is completed, the system records CK. When boarding is confirmed, the system records BD. If a scan is rejected, the system records RJ. |
| `action_at` | `TEXT NOT NULL` | Time the action occurred. |
| `station_code` | `TEXT NOT NULL` | Three-letter airport code where the processing action occurred. |
| `processing_channel` | `TEXT NOT NULL` | WEB, MOBILE, KIOSK, COUNTER or GATE; reflects the system channel. |
| `terminal_code` | `TEXT` | Synthetic terminal designation; NULL for remote web/mobile check-in. |
| `device_id` | `TEXT` | Local synthetic processing device or application identifier. |
| `result_code` | `TEXT NOT NULL` | Processing result in the source system: OK or REJECTED. |
| `rejection_reason` | `TEXT` | Local synthetic reason code for a rejected boarding scan; NULL for successful actions. |

## `passenger_legs`

Ticketed segments linking a passenger ticket to a particular operating leg. (6,885 rows)

| Column | Declaration | Description |
|---|---|---|
| `leg_id` | `TEXT PRIMARY KEY NOT NULL` | Passenger flight leg identifier. |
| `ticket_id` | `TEXT NOT NULL REFERENCES tickets(ticket_id)` | Associated ticket. |
| `flight_id` | `TEXT NOT NULL REFERENCES flights(flight_id)` | Operating leg. |
| `coupon_no` | `INTEGER NOT NULL` | One-based coupon position in chronological order within the ticket itinerary. |
| `booking_class` | `TEXT NOT NULL` | Reservation booking class code for the segment, using local synthetic Y, M or J values. |
| `cabin_class` | `TEXT NOT NULL` | Cabin associated with the fare product: ECONOMY or BUSINESS. |
| `fare_basis` | `TEXT NOT NULL` | Local synthetic fare basis code for the segment. |
| `seat_no` | `TEXT` | Assigned seat designator. NULL means no seat assignment in the observed departure records. |
| `checkin_sequence` | `INTEGER` | Sequence of successful check-in within the dated flight; NULL if no completed check-in exists. |
| `departure_status` | `TEXT NOT NULL` | Departure-system snapshot derived from observed processing: BOOKED, CHECKED_IN or BOARDED. |
| `checked_bag_allowance` | `INTEGER NOT NULL` | Number of included checked bags; additional paid bags can exceed the allowance. |
| `segment_base_fare` | `INTEGER NOT NULL` | Allocated segment base fare in whole KRW. |
| `segment_tax` | `INTEGER NOT NULL` | Allocated segment taxes and fees in whole KRW. |

## `passengers`

Synthetic passenger register. The dataset records a single nationality, distinct from country of birth, residence or passport issuance. Date of birth is a passenger attribute. (4,505 rows)

| Column | Declaration | Description |
|---|---|---|
| `passenger_id` | `TEXT PRIMARY KEY NOT NULL` | Internal synthetic passenger identifier, distinct from a passport number. |
| `display_name` | `TEXT NOT NULL` | Synthetic passenger display name. |
| `date_of_birth` | `DATE NOT NULL` | Date of birth in YYYY-MM-DD format. A passenger attribute rather than an event timestamp. |
| `nationality_code` | `TEXT CHECK (nationality_code IS NULL OR length(nationality_code)=2)` | Recorded two-letter nationality code (KR, JP, US, DE or SG). NULL means unknown. |
| `gender_code` | `TEXT NOT NULL CHECK (gender_code IN ('MALE','FEMALE','UNKNOWN'))` | Source gender code using the local values MALE, FEMALE and UNKNOWN. |
| `given_name` | `TEXT NOT NULL` | Fictional given name; part of the display name. |
| `family_name` | `TEXT NOT NULL` | Fictional family name; part of the display name. |
| `preferred_language` | `TEXT NOT NULL` | Two-letter service language code, not necessarily the passenger nationality. |
| `loyalty_tier` | `TEXT` | Synthetic frequent-flyer tier; NULL means no tier recorded. |

## `security_events`

Observations recorded during security checkpoint visits. (20,999 rows)

| Column | Declaration | Description |
|---|---|---|
| `event_id` | `TEXT PRIMARY KEY NOT NULL` | Observation identifier. |
| `visit_id` | `TEXT NOT NULL REFERENCES security_visits(visit_id)` | Associated security visit. |
| `point` | `TEXT NOT NULL` | Q = queue entry; S = screening start; C = screening completion. |
| `observed_at` | `TEXT NOT NULL` | Time the observation was made on site. |
| `received_at` | `TEXT NOT NULL` | Time the receiving system received the record. |
| `station_code` | `TEXT NOT NULL` | Airport code of the visit checkpoint. |
| `source_system` | `TEXT NOT NULL` | Observation feed: QUEUE_MONITOR or SCREENING_SYSTEM. |
| `device_id` | `TEXT NOT NULL` | Synthetic observation device reference, not a real airport installation. |
| `capture_method` | `TEXT NOT NULL` | Local observation capture method: SENSOR or SYSTEM_RECORD. |
| `quality_code` | `TEXT NOT NULL` | Local record quality indicator: VALIDATED or UNREVIEWED. |

## `security_visits`

Airport-provided records of individual passenger visits to security checkpoints. (7,030 rows)

| Column | Declaration | Description |
|---|---|---|
| `visit_id` | `TEXT PRIMARY KEY NOT NULL` | Security visit identifier. |
| `leg_id` | `TEXT NOT NULL REFERENCES passenger_legs(leg_id)` | Associated passenger flight leg. |
| `checkpoint_id` | `TEXT NOT NULL REFERENCES checkpoints(checkpoint_id)` | Security checkpoint visited. |
| `queue_type` | `TEXT NOT NULL` | Local service queue category: STANDARD or PRIORITY. |
| `lane_no` | `INTEGER` | Synthetic lane number; NULL when screening has not started. |
| `visit_status` | `TEXT NOT NULL` | Last observed visit state: QUEUED, IN_SCREENING or COMPLETED; does not assert a security clearance decision. |

## `tickets`

Tickets issued to passengers. (4,505 rows)

| Column | Declaration | Description |
|---|---|---|
| `ticket_id` | `TEXT PRIMARY KEY NOT NULL` | Ticket identifier. |
| `booking_id` | `TEXT NOT NULL REFERENCES bookings(booking_id)` | Associated booking. |
| `passenger_id` | `TEXT NOT NULL REFERENCES passengers(passenger_id)` | Passenger named on the ticket. |
| `ticket_number` | `TEXT NOT NULL` | Synthetic 13-digit electronic document number using a dummy prefix; not valid for travel. |
| `ticket_status` | `TEXT NOT NULL` | Ticket document snapshot status; ISSUED means the ticket exists, not that every coupon was flown. |
| `issuing_channel` | `TEXT NOT NULL` | Distribution channel through which this document was issued. |
| `currency_code` | `TEXT NOT NULL` | ISO 4217 currency for the ticket fare. |
| `base_fare_amount` | `INTEGER NOT NULL` | Ticket base fare in whole KRW, summed across its segments. |
| `tax_amount` | `INTEGER NOT NULL` | Ticket tax and fee total in whole KRW. |
| `total_amount` | `INTEGER NOT NULL` | Ticket base fare plus taxes in whole KRW. |
| `fare_product` | `TEXT NOT NULL` | Commercial fare product: ECONOMY_SAVER, ECONOMY_FLEX or BUSINESS. |

## `turnarounds`

Ground stay at the focal airport linking an arriving operating leg to the next departing operating leg of the same aircraft. The overall handling start is the start of coordination, which can precede individual jobs. (100 rows)

| Column | Declaration | Description |
|---|---|---|
| `turn_id` | `TEXT PRIMARY KEY NOT NULL` | Turnaround identifier. |
| `inbound_id` | `TEXT NOT NULL UNIQUE REFERENCES flights(flight_id)` | Inbound operating leg. |
| `outbound_id` | `TEXT NOT NULL UNIQUE REFERENCES flights(flight_id)` | Next outbound operating leg. |
| `handling_started_at` | `TEXT NOT NULL` | Actual start of ground handling. |
| `ready_at` | `TEXT NOT NULL` | Actual aircraft ready time. |

