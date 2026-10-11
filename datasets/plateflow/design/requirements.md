# PlateFlow v2 Requirements

A fictional steelworks maintains distinct records for slab materials, planned rolling instructions, released rolling instructions, furnace-charge tracking, as-rolled mother materials, cutting/finishing instructions, individual cut Plate materials and operation history. Preserve milestone timestamps on material records and repeated operation occurrences with start/completion times in history. Separate planned, actual and technical times. Model one-to-many mother-to-piece lineage. Extract mother-material lifecycle logs including descendant-piece operations exactly once. Use a synthetic code domain for operation meanings.

The physical separation follows selected tables in the supplied POSCO metadata. Cardinalities, keys, types, code values and execution rules are newly specified assumptions.
