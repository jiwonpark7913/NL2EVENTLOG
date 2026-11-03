# Dictionary-input ablation setup

- Purpose: distinguish the effect of rich identifier documentation from schema/data evidence. These files prepare evaluation inputs; they do not run the method or demonstrate an accuracy difference.
- All conditions use the same database, SQL schema, question IDs/texts and private Gold. Do not regenerate an independent simulation per condition.

| Condition | Dictionary | Information available |
| --- | --- | --- |
| full_dictionary | input/data_dictionary.json | Reviewed full business definitions, row grain, domains, NULL meanings, declared keys and documented logical identifier relationships; no grouping decisions or event extraction answers. |
| concise_dictionary | input/ablation/data_dictionary.concise.json | Brief table/column definitions, keys, domains, units, datetime and NULL meanings; no repeated identity explanations, logical namespace notes, extended descriptions or documentation references. |
| no_dictionary | None | The same executable DB, SQL schema and question text. Column/table names and declared constraints remain available; this is not a no-schema condition. |

## Select exact model inputs

- Conditions are listed in input/ablation/conditions.json. Use only the selected condition paths; do not send the containing directory. The default input/model_input_manifest.json continues to select the full dictionary.
- Prepare a path list from the repository root:

```bash
python hospital_ablation.py datasets/hospitalflow --condition full_dictionary
python hospital_ablation.py datasets/hospitalflow --condition concise_dictionary
python hospital_ablation.py datasets/hospitalflow --condition no_dictionary
```

- These commands print only the selected input paths. They do not call an LLM. Connect that path list to the method runner, keeping model, prompt, sampling parameters and evaluation code fixed across conditions.
- README, docs, source, design, private, input/questions.jsonl and task_scope_catalog.json are excluded from all three model-input conditions. The scope catalog would reveal explicit activity lists and requires a separately declared experiment.
- Candidate decisions, gold memberships and event extraction annotations remain private evaluation answers. No-dictionary and concise conditions must not receive full-dictionary content indirectly through previous conversation or a shared retrieval/cache corpus. Use isolated model contexts and condition-aware cache namespaces; cached results cannot be shared across input conditions.
- The private identity grouping labels are unchanged. A model can reasonably become UNRESOLVED when a condition omits necessary identity evidence; report this alongside correctness rather than fabricating a correspondence.

## Dictionary sizes

| Condition | UTF-8 bytes | Characters |
| --- | --- | --- |
| full_dictionary | 90429 | 90429 |
| concise_dictionary | 38241 | 38241 |
| no_dictionary | 0 | 0 |

- Counts above are file byte/character counts, not tokenizer-based token counts. [Input hashes and size report](dictionary_ablation_inputs.json) verify shared inputs and Gold.
- The concise condition removes several fields together, so it measures the joint effect of reduced documentation. It does not isolate a causal effect of one sentence or NULL metadata field. No dictionary adds no fabricated claims; declared SQL FK information remains available in every condition.
