# Operational schema enrichment (v1)

87 additional attributes across 15 tables, with unchanged table count, existing event clocks, key paths and Gold occurrence multisets. The first five tables are unchanged. Passenger display names are replaced by fictional structured names; no real passenger records are used. All amounts, statuses, assignments, codes, weights and dispatch quantities are synthetic; the three airport identifiers and names are public geographic reference data. No new event timestamps or lifecycle events are introduced in this revision. This is a realistic relational projection of selected operational fields, not a full PSS/DCS/BRS or regulator-compliant database.

## Sources and mapping

- Reservations/passengers/tickets/segments: [Duffel Orders](https://duffel.com/docs/api/v2/orders), [Duffel order schema](https://duffel.com/docs/api/v2/orders/schema), [Amadeus Flight Offers](https://github.com/amadeus4dev/amadeus-open-api-specification/blob/main/spec/yaml/FlightOffersSearch_v2_swagger_specification.yaml). Locator, payment state, currency, fare/tax, traveler identity, cabin/seat. Channels, local fare products and synthetic document numbers are design choices.
- Departure processing: public reservation/seat schemas plus the existing DCS action codes; capture channel, terminal and result are local synthetic metadata, not standard-mandated database columns.
- Baggage: [IATA Resolution 753](https://www.iata.org/en/programs/ops-infra/baggage/baggage-tracking) (acceptance/loading/transfer/delivery). Only the two existing acceptance/loading points are represented here; device/location/container fields are local synthetic design. No invented transfer or arrival event.
- Security: [ACI Airport Data Portal](https://airportscouncil.org/airport-operations/airport-data-portal/) conceptual checkpoint/queue context. Person-level visit, lane, device, observation quality fields are modeled assumptions, not a publicly disclosed production schema. Completion is not a security clearance decision.
- Airport register: [OurAirports data dictionary](https://ourairports.com/help/data-dictionary.html) for airport identifiers, country and names; timezone is an IANA zone.
- Carrier and fleet: [BTS Carrier Decode](https://www.transtats.bts.gov/Fields.asp?gnoyr_VQ=GDH), [BTS Schedule B-43](https://transtats.bts.gov/DL_SelectFields.aspx?QO_fu146_anzr=Nv4+Pn44vr4+Sv0n0pvny&gnoyr_VQ=GEH), [FAA aircraft registry](https://www.faa.gov/licenses_certificates/aircraft_certification/aircraft_registry/releasable_aircraft_download). Synthetic carrier/fleet values, no real registration IDs.
- Employees and dispatch: [14 CFR 121.683](https://www.law.cornell.edu/cfr/text/14/121.683), [14 CFR 121.687](https://www.law.cornell.edu/cfr/text/14/121.687) illustrate qualification records and dispatch attributes. They are design references, not claims of applicability to the modeled Korean/Japanese routes. Fuel quantities are illustrative only and not valid for flight planning.

## Table-level design

| Table | Added columns |
|---|---|
| `bookings` | record_locator, sales_channel, booking_status, currency_code, base_fare_amount, tax_amount, total_amount, payment_status |
| `passengers` | given_name, family_name, preferred_language, loyalty_tier |
| `tickets` | ticket_number, ticket_status, issuing_channel, currency_code, base_fare_amount, tax_amount, total_amount, fare_product |
| `passenger_legs` | coupon_no, booking_class, cabin_class, fare_basis, seat_no, checkin_sequence, departure_status, checked_bag_allowance, segment_base_fare, segment_tax |
| `passenger_actions` | station_code, processing_channel, terminal_code, device_id, result_code, rejection_reason |
| `bag_legs` | tag_license_plate, weight_kg, bag_type, origin_station, destination_station, handling_status |
| `bag_scans` | station_code, location_code, device_id, capture_method, container_id, source_system |
| `checkpoints` | terminal_code, checkpoint_name, checkpoint_type, lane_count, operational_status |
| `security_visits` | queue_type, lane_no, visit_status |
| `security_events` | station_code, source_system, device_id, capture_method, quality_code |
| `airlines` | carrier_code, country_code, home_base, carrier_type |
| `airports` | airport_name, icao_code, country_code, timezone, airport_type |
| `aircraft` | registration_ref, manufacturer, aircraft_type_code, manufacture_year, seat_capacity, fleet_status |
| `employees` | employee_name, department, base_station, qualification_status, employment_status |
| `flight_dispatch` | operation_type, alternate_station, planned_fuel_kg, minimum_fuel_kg, release_status, dispatch_system |

Column declarations and descriptions: [field specification](../source/operational_fields_v1.json). Full dictionaries are generated per variant, preserving the original and standard editions' prior descriptions. New fields use identical neutral descriptions in both editions. No forward FK into an absent higher-layer table; station codes in L10/L15 are source attributes. No request-specific event mapping in these added dictionary descriptions. The release validates all 108 SQL conditions and exact preservation of original data (except fictional display names), shared rows, seat uniqueness, fare totals, and DDL/DD column agreement. Human semantic review and production scorer integration remain separate.
