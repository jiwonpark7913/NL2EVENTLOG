"""Shared closed JSON object schema construction."""


def record(**fields):
    """PURPOSE: Define a structured output object with no undeclared fields.
    INPUT: Field names mapped to JSON schemas, in their required output order.
    OUTPUT: Object schema requiring every field and forbidding extra properties.
    """
    return {"type": "object", "properties": fields, "required": list(fields),
            "additionalProperties": False}
