# OCEL 2.0 → Relational Database benchmark

BPI 2017 is intentionally excluded. Work proceeds in this order: **MIMIC-IV Demo → BPI 2019 → Order Management**.

## Verified upstream sources
- BPI 2019: [Zenodo 22663565](https://zenodo.org/records/22663565), `BPIC19_ocel2.zip`, MD5 `06d7911d54db9a9f1ca33ad991488676`. This is a conversion of a legacy OCEL; **no object-to-object relationships or object attribute updates were added**.
- Order Management: [Zenodo 8428112](https://zenodo.org/records/8428112), `order-management.sqlite`, MD5 `4635d8689ce03687866210afa41457b2`. This is simulated, not real operational data.

## Reproduce
```bash
python -m pip install pm4py
python tests/test_ocel_benchmark.py
python tools/download_ocel_benchmark.py bpi2019 --dest /tmp/bpi19
python tools/ocel_to_relational.py --source /tmp/bpi19/bpi2019.sqlite --out datasets/bpi2019_ocel
python tools/download_ocel_benchmark.py order_management --dest /tmp/order
python tools/ocel_to_relational.py --source /tmp/order/order-management.sqlite --out datasets/order_management_ocel
```

For BPI 2019 the actual converted SQLite filename depends on the archive member. Use the source path printed by the downloader rather than assuming it is `bpi2019.sqlite`. The [OCEL build workflow](../../.github/workflows/ocel-benchmark.yml) discovers that path and publishes a downloadable artifact after validation. It does **not** commit datasets automatically.

## Evaluation separation
Only `input/database.sqlite` and `input/data_dictionary.json` may be given to the model. `review/gold_flatten/*.csv` contains direct event-to-object flattening with case_id, event_id, activity and timestamp. Separate `*_cases.csv` files retain the full case population including objects with no related events. The reconstructed database also retains direct OCEL object–object links when available. The source OCEL and review references are evaluator-only. Every event directly linked to two distinct objects of one type produces two flattened rows; retain both.

This implementation uses a **controlled OCEL-native normalized relational schema**. It is not representative of a recovered ERP database. It is useful for testing instance linking and event coverage but **not as independent evidence that EEG reconstructs hidden event semantics**. A future business-schema redesign must be conducted separately and without reading test answers during design.

The generator refuses to emit references with incomplete timestamps. It retains case instances without events and raw O2O links, but does not propagate events via O2O relations or reconstruct full attribute histories. Those require explicitly defined benchmark policies and further human review before labeling the output Gold.

## BPI 2019 oversized JSON handling (2026-11-17)

The pinned 87,645,028-byte ZIP contains `BPIC19_ocel2.json`, whose
uncompressed size exceeds the previous arbitrary 2 GB safety threshold.
The archive checksum was verified in GitHub Actions. The new converter
`tools/stream_ocel_json.py` uses `ijson` to stream the JSON member
directly from the ZIP into a compact SQLite **staging source**, without
materializing the expanded JSON or loading the full log into PM4Py.

The staging source intentionally preserves event ID, event type,
timestamp, object ID, object type, direct E2O links, and direct O2O links.
**It currently discards event and object attributes.** Therefore this
conversion is appropriate for evaluating type-level case selection,
activity occurrence extraction, and direct linking; it is **not yet an
attribute-complete OCEL benchmark**. Independently validate source counts,
timestamp coverage, referential integrity and flattening before calling
any generated CSV a finalized Gold log.
