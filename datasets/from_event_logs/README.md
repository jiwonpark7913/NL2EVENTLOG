# Databases reconstructed from event logs

Each conversion maps an object-centric event log (OCEL) into SQLite and independently flattens direct event–object links into case-based reference logs. Use these datasets to evaluate occurrence coverage and attribution.

| Dataset | Upstream log | Published relational tables |
|---|---|---:|
| [BPI Challenge 2019](bpi2019_ocel/) | Purchasing, converted from legacy OCEL | 4 |
| [Order Management](order_management_ocel/) | Simulated order management | 15 |

## Verified upstream sources
- BPI 2019: [Zenodo 22663565](https://zenodo.org/records/22663565), `BPIC19_ocel2.zip`, MD5 `06d7911d54db9a9f1ca33ad991488676`. This is a conversion of a legacy OCEL; **no object-to-object relationships or object attribute updates were added**.
- Order Management: [Zenodo 8428112](https://zenodo.org/records/8428112), `order-management.sqlite`, MD5 `4635d8689ce03687866210afa41457b2`. This is simulated, not real operational data.

## Obtain the database and references

The dictionaries are checked in. The [build workflow](../../.github/workflows/ocel-benchmark.yml) produces an artifact per dataset with `input/database.sqlite`, `review/gold_flatten/` and a provenance report. Download a successful artifact from [workflow runs](https://github.com/jiwonpark7913/NL2EVENTLOG/actions/workflows/ocel-benchmark.yml) and extract it into the matching dataset folder. Artifacts expire; to regenerate, run the download, staging and conversion commands from the workflow.

The BPI converter streams the JSON archive into SQLite staging. It preserves event and object identifiers, types, timestamps and direct relations, and omits event and object attributes. The Order Management converter imports the upstream SQLite OCEL and creates typed observation tables where available.

## Read the reference

Each object type defines one case view. The generated event CSV associates each event with every directly linked object of that type. The companion cases CSV retains objects with zero events. Object-to-object links can be inspected separately. These references support linking and coverage experiments on the reconstructed schema.

[Converter](../../tools/ocel_to_relational.py) · [BPI staging code](../../tools/stream_ocel_json.py) · [All datasets](../)
