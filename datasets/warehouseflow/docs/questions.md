# Question types and paired requests

- Process View includes the case concept and activity scope. Activities are not a separate addition to Process View.
- Requested activity counts are Gold annotations: Q3/Q4 counts come from the fixed catalog scope, not from explicit question text. Unavailable actions count as requested but not extractable.
- Q1 and Q2 specify a case concept and activities. Q2 uses alternate wording for the exact same scope.
- Q3 and Q4 specify a case concept without listing activities. Their Gold scope uses the declared task catalog.
- Every Q2 is paired with Q1; every Q4 is paired with Q3. Pairs have identical ES, Gold CSV and answerability.
- Answerability is independent of type. Existing unavailable actions remain unavailable and receive Q2 pairs. No evidence is fabricated.
- `answerability` is an evaluation annotation: exclude it from model inputs. `question_type` defines the taxonomy; legacy `category` records question origin.
- These are authored English paraphrases; there is no claim of model-generated linguistic diversity.
- Existing IDs are preserved. Added E/EP IDs select explicit activity subsets; added P IDs are paired paraphrases.

| Type | Included information | Answerability | Meaning |
|---|---|---|---|
| Q1 Explicit | Process View: case + explicit activity scope | O / X | Case concept and exact business activity labels |
| Q2 Paraphrased | Process View: case + explicit activity scope | O / X | Same scope as Q1, expressed with alternate business wording |
| Q3 Full Lifecycle | Process View: case; implicit activity scope | O / X | Case concept only; default recorded scope from catalog |
| Q4 Full Lifecycle Paraphrased | Process View: case; implicit activity scope | O / X | Alternate wording of Q3 with identical default scope |

| ID | Type | Paired with | Answerability | Requested activities | Extractable activities | Question |
|---|---|---|---|---|---:|---:|---|
| R01 | Q1 Explicit | — | O | 1 | 1 | Extract Goods Received events for each warehouse. |
| R02 | Q2 Paraphrased | R01 | O | 1 | 1 | For each warehouse, build a timeline of goods arriving at the warehouse. |
| R03 | Q1 Explicit | — | O | 1 | 1 | Extract Goods Dispatched events for each warehouse. |
| R04 | Q2 Paraphrased | R03 | O | 1 | 1 | For each warehouse, build a timeline of goods leaving the warehouse. |
| R05 | Q3 Full Lifecycle | — | O | 10 | 10 | Extract the full recorded lifecycle event log for each warehouse. |
| R06 | Q4 Full Lifecycle Paraphrased | R05 | O | 10 | 10 | Show the complete recorded history associated with each warehouse. |
| R07 | Q1 Explicit | — | X | 1 | 0 | Extract Warehouse Task Started events for each warehouse. |
| OW01 | Q3 Full Lifecycle | — | O | 10 | 10 | Extract the full recorded lifecycle event log for each warehouse. |
| OW02 | Q3 Full Lifecycle | — | O | 10 | 10 | Extract the full recorded lifecycle event log for each goods. |
| OW03 | Q3 Full Lifecycle | — | O | 10 | 10 | Extract the full recorded lifecycle event log for each worker. |
| OW04 | Q3 Full Lifecycle | — | O | 10 | 10 | Extract the full recorded lifecycle event log for each warehouse transaction. |
| OW05 | Q3 Full Lifecycle | — | O | 10 | 10 | Extract the full recorded lifecycle event log for each goods transaction line. |
| OW06 | Q3 Full Lifecycle | — | O | 10 | 10 | Extract the full recorded lifecycle event log for each worker transaction assignment. |
| R07P | Q2 Paraphrased | R07 | X | 1 | 0 | For each warehouse, build a timeline of the beginning of warehouse handling jobs. |
| OW01P | Q4 Full Lifecycle Paraphrased | OW01 | O | 10 | 10 | Show the complete recorded history associated with each warehouse. |
| OW01E | Q1 Explicit | — | O | 3 | 3 | Extract Receiving Requested, Goods Received, Goods Put Away events for each warehouse. |
| OW01EP | Q2 Paraphrased | OW01E | O | 3 | 3 | For each warehouse, build a timeline of a request to take goods into storage, goods arriving at the warehouse, goods being placed into their storage locations. |
| OW02P | Q4 Full Lifecycle Paraphrased | OW02 | O | 10 | 10 | Show the complete recorded history associated with each goods. |
| OW02E | Q1 Explicit | — | O | 3 | 3 | Extract Receiving Requested, Goods Received, Goods Put Away events for each goods. |
| OW02EP | Q2 Paraphrased | OW02E | O | 3 | 3 | For each goods, build a timeline of a request to take goods into storage, goods arriving at the warehouse, goods being placed into their storage locations. |
| OW03P | Q4 Full Lifecycle Paraphrased | OW03 | O | 10 | 10 | Show the complete recorded history associated with each worker. |
| OW03E | Q1 Explicit | — | O | 3 | 3 | Extract Receiving Requested, Goods Received, Goods Put Away events for each worker. |
| OW03EP | Q2 Paraphrased | OW03E | O | 3 | 3 | For each worker, build a timeline of a request to take goods into storage, goods arriving at the warehouse, goods being placed into their storage locations. |
| OW04P | Q4 Full Lifecycle Paraphrased | OW04 | O | 10 | 10 | Show the complete recorded history associated with each warehouse transaction. |
| OW04E | Q1 Explicit | — | O | 3 | 3 | Extract Receiving Requested, Goods Received, Goods Put Away events for each warehouse transaction. |
| OW04EP | Q2 Paraphrased | OW04E | O | 3 | 3 | For each warehouse transaction, build a timeline of a request to take goods into storage, goods arriving at the warehouse, goods being placed into their storage locations. |
| OW05P | Q4 Full Lifecycle Paraphrased | OW05 | O | 10 | 10 | Show the complete recorded history associated with each goods transaction line. |
| OW05E | Q1 Explicit | — | O | 3 | 3 | Extract Receiving Requested, Goods Received, Goods Put Away events for each goods transaction line. |
| OW05EP | Q2 Paraphrased | OW05E | O | 3 | 3 | For each goods transaction line, build a timeline of a request to take goods into storage, goods arriving at the warehouse, goods being placed into their storage locations. |
| OW06P | Q4 Full Lifecycle Paraphrased | OW06 | O | 10 | 10 | Show the complete recorded history associated with each worker transaction assignment. |
| OW06E | Q1 Explicit | — | O | 3 | 3 | Extract Receiving Requested, Goods Received, Goods Put Away events for each worker transaction assignment. |
| OW06EP | Q2 Paraphrased | OW06E | O | 3 | 3 | For each worker transaction assignment, build a timeline of a request to take goods into storage, goods arriving at the warehouse, goods being placed into their storage locations. |
