# Domain-generated databases

The project authored relational schemas and synthetic records for these seven datasets. External schemas, requirements or industrial metadata inform some designs. The domain descriptions on each page identify that basis.

| Evaluation use | Dataset | What to inspect |
|---|---|---|
| Compare extractions with authored Gold | [HospitalFlow](hospitalflow/) · [PlateFlow](plateflow/) · [UniversityFlow](universityflow/) · [WarehouseFlow](warehouseflow/) | Case-specific questions, reference SQL and CSV, source evidence and per-question DFGs |
| Measure sensitivity to physical storage | [MaintenanceFlow](maintenanceflow/) · [ProcurementFlow](procurementflow/) | The same requests and underlying events across layouts with varying table count, FK distance, naming and timestamp distractors |

| Pilot aviation scenarios | [AirlineFlow](airlineflow/) | Four nested databases (5/10/15/20 tables), five requests, reference SQL/logs and ERDs |

[All datasets](../)
