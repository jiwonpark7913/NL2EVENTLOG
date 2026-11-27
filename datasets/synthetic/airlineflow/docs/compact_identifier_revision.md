# Compact management identifier revision

Version: Stochastic-v2-CompactIDs-20261127

Use readable internal management numbers, not real-world externally assigned ticket or aircraft registration numbers. Prefixes: F (flight), TU (turnaround), BS (boarding session), J (handling job), MR (movement report), BK (booking), P (passenger), T (ticket), PL (passenger leg), PA (passenger action), BL (bag leg), TAG (bag tag), SC (bag scan), SV (security visit), SE (security event), AC (aircraft), AL (airline), EM (employee), CP (checkpoint), FD (dispatch). The numeric component is zero-padded to at least three digits and assigned in the order of the original independent opaque keys, not chronological or parent order. Public operational codes and flight numbers are preserved.

The release is a bijective remapping, not a population change. Every source row and every Gold occurrence must equal the prior release after remapping. Canonical scoring remains three columns. All 72 enriched CSVs and the review HTML are regenerated. The selected table's actual data dictionary is embedded per variant and shown immediately below the original table, with the selected timestamp column highlighted.
