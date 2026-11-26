# Dataset analysis

[Back to AirlineFlow](../README.md)

![Test-set request distributions](dataset_statistics.svg)

All counts are derived from the frozen request registry and reference logs, not model outputs. [Machine-readable statistics](dataset_statistics.json) · [Full registry](../evaluation/query_registry.csv) · [Test registry](../evaluation/test_registry.csv).

## Evaluation units

- 72 unique natural-language requests: 12 pilot and 60 held-out evaluation requests.
- 108 database–request conditions: 12 pilot requests at each of four levels (48) and 60 test requests at L15.
- 49 distinct test reference event logs; 18 test families. Repeated references are intentional (matched comparisons).
- 32,208 event rows across 72 references, including 29,088 test rows. The count includes multiplicity and overlap between requests; it is not a count of independent database events.

| Group | IDs | Requests | Families | Reference rows | Purpose |
|---|---|---:|---:|---:|---|
| Pilot | Q01–Q12 | 12 | 6 | 3,120 | Development and schema expansion |
| A | Q13–Q24 | 12 | 4 | 6,192 | Attribution depth: 0/1/2 physical attribution joins |
| B | Q25–Q36 | 12 | 4 | 5,760 | Source diversity: 2/3/4 event-source tables |
| C | Q37–Q48 | 12 | 3 | 5,424 | Activity count: 2/4/8/12 definitions |
| D | Q49–Q60 | 12 | 3 | 10,560 | Semantic complexity: 2 × 2 case/activity explicitness |
| E | Q61–Q72 | 12 | 4 | 1,152 | Attribution role: inbound/outbound/mixed |

## Request characteristics (test only)

### Case entity
| Value | Requests |
|---|---:|
| Bag Leg | 5 |
| Booking | 2 |
| Flight | 12 |
| Passenger Leg | 8 |
| Security Visit | 5 |
| Ticket | 2 |
| Turnaround | 26 |

### Activity count
| Value | Requests |
|---|---:|
| 2 | 28 |
| 3 | 7 |
| 4 | 9 |
| 6 | 10 |
| 8 | 3 |
| 12 | 3 |

### Event-source tables
| Value | Requests |
|---|---:|
| 1 | 30 |
| 2 | 22 |
| 3 | 4 |
| 4 | 4 |

### Logical attribution depth
| Value | Requests |
|---|---:|
| 1 | 16 |
| 2 | 34 |
| 3 | 10 |

### Maximum physical SQL JOIN depth (including scope joins)
| Value | Requests |
|---|---:|
| 0 | 16 |
| 1 | 30 |
| 2 | 8 |
| 3 | 6 |

### Case / activity explicitness
| Value | Requests |
|---|---:|
| Explicit / Explicit | 51 |
| Explicit / Implicit | 3 |
| Implicit / Explicit | 3 |
| Implicit / Implicit | 3 |

### Event encoding
| Value | Requests |
|---|---:|
| Both | 18 |
| Carrier-driven | 42 |

## Interpretation

A–C are matched-family sensitivity analyses: case cardinality, activity identity or event volume can also vary. D changes wording while retaining the reference within each family. E is categorical, not an ordinal difficulty ladder. Pilot and test can share source occurrences; the latter is request-held-out, not a new-domain split. The four nested schemas assess schema expansion rather than large-volume query throughput. This is synthetic data; its timing and cardinalities do not estimate real airport populations.

Reproduce the distributions with `python docs/analyze_dataset.py` from this dataset directory. The script reads the registry and manifest only and writes no benchmark inputs.
