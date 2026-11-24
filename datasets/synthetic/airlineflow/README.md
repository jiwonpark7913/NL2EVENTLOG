# AirlineFlow

AirlineFlow is an authored synthetic aviation example for NL2EventLog. It provides four nested databases with **5, 10, 15 and 20 tables**, together with five pilot requests. It covers inbound-to-outbound aircraft turnaround, departure preparation, passenger processing, checked baggage and airport-linked security visits.

All records are synthetic. The study window contains 48 inbound flights, 48 outbound flights and 48 turnarounds across 12 days. The sample passengers and bags represent selected example records. Flight-level operational completion is recorded separately from individual scans. All timestamps use KST.

## Inspect the scenario

![Five-table layout](variants/l05/docs/schema.svg)

The left ERD column marks PK, FK and single-column UQ constraints. Arrows point from child references to parent keys. The schema also declares a composite UNIQUE(ticket_id, flight_id) constraint in passenger_legs.

Download and open the [scenario viewer](docs/scenario.html) in a browser to view all four ERDs, embedded dictionaries and an example turnaround trace. Open **Raw tables** to browse SQLite rows or download a complete table as CSV.

## Four database sizes

| Variant | Tables | Added domain | Database | Dictionary | ERD |
|---|---:|---|---|---|---|
| l05 | 5 | Flight, turnaround, boarding session, handling job, movement report | [SQLite](variants/l05/input/database.sqlite) | [Dictionary](variants/l05/input/data_dictionary.json) | [ERD](variants/l05/docs/schema.svg) |
| l10 | 10 | Booking, passenger, ticket, passenger flight leg, passenger action | [SQLite](variants/l10/input/database.sqlite) | [Dictionary](variants/l10/input/data_dictionary.json) | [ERD](variants/l10/docs/schema.svg) |
| l15 | 15 | Bag leg and scan, checkpoint, security visit and observation | [SQLite](variants/l15/input/database.sqlite) | [Dictionary](variants/l15/input/data_dictionary.json) | [ERD](variants/l15/docs/schema.svg) |
| l20 | 20 | Airline, airport, individual aircraft, employee and dispatch assignment | [SQLite](variants/l20/input/database.sqlite) | [Dictionary](variants/l20/input/data_dictionary.json) | [ERD](variants/l20/docs/schema.svg) |

Earlier tables and rows are identical across successive variants. These sizes increase catalog size and the number of similar candidate activities together. Treat them as nested pilot scenarios. Their differences do not isolate a single difficulty factor.

## Pilot requests and references

The [model question file](evaluation/model_questions.jsonl) has question_id and text fields. Requests and data dictionaries are in English.

| ID | Case | Requested events | Minimum tables | Cases | Reference events |
|---|---|---|---:|---:|---:|
| D | Outbound flight | Boarding start/close, baggage loading close, aircraft ready, off-block | 5 | 48 | 240 |
| T | Turnaround | Inbound landing/in-block, handling milestones, outbound preparation and take-off | 5 | 48 | 672 |
| P | Passenger flight leg | Check-in and boarding confirmation | 10 | 288 | 576 |
| B | Passenger flight leg | Check-in/boarding and each checked bag's acceptance/loading | 15 | 288 | 864 |
| S | Security visit | Queue entry, screening start and screening completion | 15 | 288 | 864 |

The [variant manifest](evaluation/variant_manifest.json) records allowed requests, paths, row counts and checksums. Start with D and T on all four variants to compare the same requests and reference events as the catalog grows. Each request is an explicit pilot request. Implicit scope and paraphrase pairs can be added after the first run.

Authored [reference SQL and event logs](private/) are evaluator material. The directory name identifies its role and does not impose access controls. Supply the model only its selected variant's database, dictionary and one question. Use the existing one-to-one activity-label matching evaluator consistently when evaluating generated labels. Preserve event multiplicities.

Run the reference verification from this folder:

```bash
python verify.py
```

This runs all 15 supported request/variant combinations, checks foreign keys and checksums, and compares SQL output with authored CSV references. LLM extraction has not yet been run on this dataset.

## Representation choices

- flights identifies dated operating legs. Flight numbers repeat across dates.
- turnarounds connects an inbound_id and an outbound_id using UNIQUE foreign keys. The example assumes one aircraft and no swaps. At l20, the aircraft and connecting airport agree across the pair.
- movement_reports distinguishes LAND (landing), IN (in-block), OUT (off-block), AIR (take-off) and EST (estimated off-block). Use value_at for the represented time and received_at for message receipt.
- handling_jobs stores actual start/completion and posting time. Jobs can overlap. Its service_provider_code, priority_code and work_zone_code describe ground operations.
- Movement reports include source_code, validation_code and message_format_code. These operational attributes are synthetic. The existing kind and job_code values identify activities.
- passenger_id is an internal synthetic person key. passengers stores date_of_birth, a single recorded nationality and a locally coded gender. Date of birth is an attribute. Age is not calculated.
- tickets links to passengers by passenger_id. Copied passenger snapshots at issuance are not modeled.
- Security timestamps assume an airport feed linked to a passenger leg. Airline availability of such a feed is an explicit scenario assumption.
- The T reference requires following the UNIQUE inbound-flight-to-turnaround relation. Verify EEG and compiler support for this direction when running the method.

## Public design references

The physical schema and records are authored for this example. Sources inform the business entities and milestones.

- [Postgres Pro Airlines demo, 2017 schema family](https://postgrespro.com/docs/enterprise/13/demodb-schema-objects.html) provides bookings, tickets and ticket-flight relationships. Its passenger fields are in tickets, while this example uses a separate person table.
- [Amadeus official booking example](https://github.com/amadeus4dev/amadeus-flight-booking-django/blob/master/amadeus_demo_api/demo/views.py) shows birth date and gender on a traveler and nationality on a travel document. Here, nationality is simplified into passengers.
- [EUROCONTROL A-CDM](https://www.eurocontrol.int/publication/eurocontrol-specification-airport-collaborative-decision-making-cdm) informs inbound, turnaround and outbound milestones.
- [IATA Resolution 753 implementation guide](https://www.iata.org/contentassets/5c4aa8b8b3b1432697d2bf3301450684/reso753-implementation-guide---2023_issue-4.02.pdf) distinguishes baggage acceptance and loading.

[Domain-generated datasets](../) · [All datasets](../../)
