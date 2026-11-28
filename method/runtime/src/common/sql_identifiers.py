"""One SQL identifier quoting rule for profiling, attribution, and compilation."""


def quote_identifier(value: str) -> str:
    """PURPOSE: Safely quote a physical SQLite identifier.
    INPUT: Identifier string without NUL; embedded quotes are allowed.
    OUTPUT: Double-quoted SQL identifier; invalid inputs raise ValueError.
    """
    if not isinstance(value, str) or "\x00" in value:
        raise ValueError("Invalid SQLite identifier")
    return '"' + value.replace('"', '""') + '"'
