# OCEL-derived relational benchmark (work in progress)

## Datasets and order
1. **BPI 2019 OCEL 2.0**, converted from OCEL 1.0 by Khayatbashi, Hartig & Jalali; [Zenodo record](https://zenodo.org/records/22663565). **No object–object links or object-attribute changes in this conversion.**
2. **Order Management OCEL 2.0**, simulated data; [Zenodo source](https://zenodo.org/records/18373906).

BPI 2017 is intentionally excluded.

## Generic preprocessing
```bash
python tools/ocel_to_relational.py --source /path/to/source.sqlite --out datasets/bpi2019_ocel
python tools/ocel_to_relational.py --source /path/to/order-management.sqlite --out datasets/order_management_ocel
```

The generic conversion produces a **controlled normalized OCEL→DB test**. It does not reproduce a real operational DB, and the outputs are **not yet validated** against the actual downloaded logs.

**Important limitations:** The current reference CSV preserves only direct E2O associations and does not include event timestamps until independently verified from the per-event-type tables. It is an intermediate reference, *not* a complete Gold Event Log. No O2O transitive propagation is performed. For process-mining traces use a validated occurrence timestamp mapping and explicit flattening policy before scoring. A more realistic business-schema reconstruction is a separate experiment.

Only `input/database.sqlite` and `input/data_dictionary.json` are model inputs. Never pass `review/gold_flatten`, the source OCEL, or provenance to model prompts. Separate source transformation, human review and evaluation.
