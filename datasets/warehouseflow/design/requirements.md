# Adapted execution specification

The original RSchema requirement is preserved in source/requirements_original.md. Retain all six original logical tables, all attributes and all declared PK/FK relationships. Normalize English identifiers to snake_case without changing entity structure. Materialize a warehouse task simulation with IN/OUT task completion timestamps, positive goods quantities, nonnegative stock and capacity limits. Worker assignments and goods details may be many-to-many with task headers. Query-specific logs use warehouses as cases and each task as one event.
