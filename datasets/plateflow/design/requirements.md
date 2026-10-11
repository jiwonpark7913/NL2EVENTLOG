# PlateFlow Requirements

- A fictional steelworks maintains distinct records for slab materials, planned rolling instructions, released rolling instructions, furnace-charge tracking, as-rolled mother materials, cutting/finishing instructions, individual cut Plate materials and operation history.
- Preserve milestone timestamps on material records and repeated operation occurrences with start/completion times in history.
- Separate planned, actual and technical times.
- Model one-to-many mother-to-piece relationships.
- Extract mother-material lifecycle logs including descendant-piece operations exactly once.
- Use a table that defines the synthetic process-code meanings.

- The physical separation follows selected tables in the supplied Korean manufacturer metadata.
- Relationship counts, keys, types, code values and execution rules are newly specified assumptions.
