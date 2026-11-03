# HospitalFlow simulator

Simulates a hospital process and stores it the way MIMIC-IV stores it. One YAML
file decides **what exists, how much, what happens, and how it is written down**.
Every run produces a relational database **and** the true event history, so any
extraction pipeline can be scored against the history that generated the data.

```
config.yaml ─▶ ① process engine ─▶ true object-centric history ─▶ ② recorder ─▶ database.sqlite
                                              │                                   schema.sql
                                              └──────────────▶ gold/ (OCEL 2.0, CSV, provenance)
```

Gold always comes from ①, never from the tables, so information lost by the
recording (no timestamp, date only, NULL) is visible as a gap, not hidden.

## UI (recommended)

```bash
cd simulation/hospital
pip install -r requirements.txt
python -m hospital_sim ui          # opens http://127.0.0.1:8765
```

| Panel | What it does |
|---|---|
| left · Variables | edit every `$variable` (distribution type, parameters, unit, min/max), live histogram preview, **Save** writes the values back into the YAML (comments kept), **Save as…** makes a new config |
| middle · Process model | flows as blocks (choice, parallel, repeat, spawn, background); click a `$variable` to edit it, click `→ flow` to jump; after **Run**, each activity shows `n` events and how many have a timestamp in the DB |
| right · Recording | for every activity, the table.column that keeps its time (row / column / derived / date only / none); every table with its grain and column sources; hover an activity to highlight where it is stored |

In VS Code (local or Remote/SSH) the port is forwarded automatically; open the
link from the terminal. Use `--port`, `--configs`, `--out`, `--no-browser` as needed.
Runs from the UI write to `out/<config name>/`.

## Run from the command line

```bash
cd simulation/hospital
pip install -r requirements.txt
python -m hospital_sim run configs/mimic_like.yaml --out out/mimic_like
python -m hospital_sim run configs/mimic_like.yaml --seed 7 --set n_patients=500 --out out/big
python -m hospital_sim validate configs/mimic_like.yaml     # dry run, no files
```

Same config + same seed → byte-identical output. Recording noise uses its own
random stream, so changing a `null_rate` never changes the simulated process.

## The four sections

| Section | You decide | Example |
|---|---|---|
| `objects` | object types, attributes, parent links, **how ids look** | `stay_id` = first `transfer_id`; `poe_id = "{subject_id}-{seq}"`; random id order |
| `variables` | every number and distribution, referenced as `$name` | arrivals, LOS, P(ICU), doses per order, lab turnaround |
| `process` | arrivals and the care process as reusable flows | ED → admit → ward ↔ ICU → discharge, orders in the background |
| `recording` | tables, and for each column where its value comes from | event as a row, as a column, as a date only, or not at all |

### 1. Objects
```yaml
transfer:
  links: [patient, admission]          # parents taken from the current flow
  id: {start: 30000000, step: {dist: int_uniform, low: 1, high: 900}, order: random}
icu_stay:
  links: [patient, admission]
  id: {same_as: transfer, pick: first}  # shares the transfer namespace
pharmacy_order:
  attributes: {med: {pick: medications}}  # row from a catalog
```
Id rules: `start/step` (counter; `namespace:` to share one), `format` (text built
from parent ids), `same_as` (reuse a child's id), `from_row` (id assigned by a
table, e.g. `poe`). Details: `hospital_sim/ids.py`.

### 2. Variables
`{dist: lognormal, median: 40, sigma: 0.7, unit: h}` — also `const, uniform,
exponential, normal, gamma, triangular, poisson, int_uniform, geometric, choice,
empirical, bernoulli`, with `min/max` clipping. Durations are minutes unless `unit`.
Override from the command line with `--set name=value`.

### 3. Process
| Node | Meaning |
|---|---|
| `act` | event; `on:` related objects, `delay:`, `attrs:`, `clip:` (emit at the deadline instead of dropping) |
| `create` / `link` / `set` | make an object (`as:` alias, `link_to:`), add parents later, change attributes |
| `wait` | advance the clock |
| `xor` | choice with probabilities (`else: true` for the rest) |
| `and` | parallel branches |
| `repeat` | sequential repetition (`isolate: true` gives each repetition a fresh scope) |
| `spawn` | concurrent children (`count` or `foreach: alias.list_attr`, `start`, `gap`) |
| `during` | `main` path bounds `background` work (orders stop at discharge) |
| a string | call a named flow |

Durations can come from an object: `{from_attr: rx.med.interval, unit: h}`.
Events after `clock.observation_end_days` are censored, so ongoing stays appear
with `dischtime` NULL. Details: `hospital_sim/engine.py`.

### 4. Recording
| Table kind | One row per | Typical MIMIC table |
|---|---|---|
| `object` | object | `admissions`, `transfers`, `icustays`, `pharmacy` |
| `event` | event of listed activities | `poe`, `emar`, `vitalsign` |
| `static` | catalog entry | `d_labitems`, `d_items` |

Column sources: `id`, `attr`, `event_time` (column encoding), `time` (row
encoding), `activity` / `activity_map`, `event_attr`, `rowid`, `seq`, `rowid_of`,
`field`, `const`. Modifiers: `of:` (take it from a linked object), `format: date`,
`offset:` (technical times such as `storetime`), `only_for:`, `null_rate:`
(noise), `pk/fk/type/desc`. Details: `hospital_sim/recorder.py`.

## Outputs

| File | Content |
|---|---|
| `database.sqlite`, `schema.sql` | the generated DB with declared PK/FK |
| `data_dictionary.md` | generated from `desc:` fields (a starting point, not a final dictionary) |
| `gold/ocel.json` | OCEL 2.0 JSON of the true history |
| `gold/events.csv`, `event_objects.csv`, `objects.csv` | same history as flat files |
| `gold/provenance.csv` | for every event: which table / row / column holds its time (`exact` or `derived`) |
| `summary.json` | counts, per-activity share recoverable from the DB, FK violations |

## What `configs/mimic_like.yaml` reproduces from MIMIC-IV

- `subject_id → hadm_id → stay_id` hierarchy; ED stays without an admission (`hadm_id` NULL)
- `stay_id` = first `transfer_id` of the stay; ED and ICU stays share the namespace without collisions; one ICU stay can span several ICU transfers
- discharge pseudo-transfer (`eventtype='discharge'`, `outtime` NULL)
- one `poe` table for all order types, `New` and `D/C` rows, `discontinue_of_poe_id`
- `pharmacy` and `prescriptions` store the **same** dispensing record (`pharmacy_id`)
- `emar` rows reference both `poe_id` and `pharmacy_id`; `charttime` / `scheduletime` / `storetime`
- `labevents` grouped by `specimen_id`, codes resolved via `d_labitems`, outpatient tests with `hadm_id` NULL, `charttime` = collection < `storetime` = result
- `triage` with no timestamp, `procedures_icd` with date only, `diagnoses_icd` with no time
- random, non-contiguous ids that do not follow time order

Not modelled (yet): chartevents, microbiology, notes, multi-hospital time zones,
data-entry errors beyond `null_rate`. Default numbers are **illustrative**;
calibrate `variables` before using results as evidence about MIMIC.
