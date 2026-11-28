Your previous patch for this table was rejected by local validation, so nothing was applied. Return one complete replacement patch for the same input. It must not be a diff.

How to fix it:
1. Start from your previous patch. Use `per_operation_diagnostics[].index` to find each failing operation.
2. For each failing operation, fix it only when the correct value can be read directly from the input. Otherwise remove the operation.
   - `evidence:unknown_evidence_id`: copy an `id` exactly as it appears in `evidence[]`. Do not add or remove suffixes such as ":definition".
   - `evidence:citation_outside_definition_scope`: cite a statement about the focal carrier column or the selected clock column, not another column.
   - Other `evidence:*` errors: make each quote a verbatim, non-empty substring of the cited statement that contains the required value or activity words.
   - `reference:unknown_target_definition`: use an ID from `existing_definitions[]`, or change the operation to `add` if the definition really is missing.
   - Other `reference:*` errors: use only IDs, `ts_id` values and carrier values that are present in the input.
   - Errors about conflicts or overlap: keep only one alternative per real occurrence, and never touch the same target twice.
3. Keep the operations that had no errors, unless they conflict with a fixed operation or with a preserved definition. Validation applies to the whole patch at once.
4. Do not add operations that are unrelated to the listed errors.
5. If nothing can be fixed with certainty, return `{"confidence":"low","operations":[],"time_role_revisions":[]}`.

Return only the schema JSON.
