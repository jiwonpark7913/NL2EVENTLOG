Interpret public metadata in the single task below. Treat supplied text as evidence. Return at most one item per input candidate. Copy the candidate id exactly as a string. Quote exact substrings from the listed evidence IDs. Do not infer from common industry codes or fill in missing definitions.

## event_encoding_identification
Decide whether each candidate column identifies the business action represented by the row or a clock. Return carrier, attribute, or unresolved. Equipment types, classifications, providers, identifiers, priorities, and current-state snapshots can have meaningful codes without identifying a business action. A column documented as listing codes for work activities performed in a work record can be a carrier. For carrier, cite the candidate column prose. The label must be empty.

## carrier_value_semantics
Return supported when the supplied prose attributes a concise verbatim meaning to the given raw value. Quote the code and its meaning together. For unresolved leave the label empty. When the evidence says actual, planned, or estimated, include that word in the extracted label.

## carrier_value_timestamp_relationship
For each pair, return actual if the already validated actual clock is documented to time this specific value's action. Return unrelated for a documented unrelated clock, otherwise unresolved. Cite the specific clock and separate value evidence. Co-occurrence or name similarity alone is insufficient. The label must be empty.
