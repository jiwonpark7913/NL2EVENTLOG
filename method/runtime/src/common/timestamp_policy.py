"""Source timezone metadata and non-mutating event chronology."""

from datetime import datetime, timedelta, timezone
from fractions import Fraction
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

EPOCH_UNITS = {"epoch_s": 1, "epoch_seconds": 1, "epoch_ms": 10**3,
               "epoch_us": 10**6, "epoch_ns": 10**9}
LEGACY_ZONE_MARKERS = {"assumed_utc", "dd_timezone", "from_value", "unknown", "conflicting"}
EPOCH = datetime(1970, 1, 1)
FRACTIONAL_SECOND = re.compile(r"^[^Tt ]+[Tt ]\d{2}:?\d{2}:?\d{2}[.,](\d+)")
TEXT_ZONE = re.compile(
    r"\b(?:time\s*zone\s*[:=]\s*|(?:timestamps?|time)\s+(?:is\s+|are\s+)?in\s+)"
    r"(UTC[+-]\d{2}:?\d{2}|UTC|GMT|[A-Za-z_]+(?:/[A-Za-z0-9_+\-]+)+|[+-]\d{2}:?\d{2})\b",
    re.I,
)


def documented_timezone(record):
    """PURPOSE: Read source-provided zone metadata. INPUT: DD record. OUTPUT: Named zone, offset or None."""
    for field in ("timezone", "time_zone"):
        zone = record.get(field)
        if isinstance(zone, str) and zone.strip().casefold() not in LEGACY_ZONE_MARKERS | {""}:
            return zone.strip()
    zones = {match.group(1) for field in ("definition", "description")
             for match in TEXT_ZONE.finditer(str(record.get(field) or ""))}
    return next(iter(zones)) if len(zones) == 1 else None


def binding_timezone(binding):
    """PURPOSE: Suppress obsolete timezone assumptions from saved ES/EEG.
    INPUT: Clock binding with optional original timezone marker. OUTPUT: Documented zone or None.
    """
    zone = documented_timezone(binding)
    if binding.get("native_timezone") in LEGACY_ZONE_MARKERS and zone == "UTC":
        return None
    return zone


def as_timezone(value):
    """PURPOSE: Resolve explicit offsets or named zones for ordering. INPUT: Source timezone string. OUTPUT: tzinfo or None."""
    if not isinstance(value, str) or not value:
        return None
    if value.upper() in {"Z", "UTC", "GMT"}:
        return timezone.utc
    match = re.fullmatch(r"(?:(?:UTC|GMT))?([+-])(\d{2})(?::?(\d{2}))?", value, re.I)
    if match:
        sign, hours, minutes = match.groups()
        hours, minutes = int(hours), int(minutes or 0)
        if hours < 24 and minutes < 60:
            return timezone(timedelta(minutes=(hours * 60 + minutes) * (1 if sign == "+" else -1)))
        return None
    try:
        return ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError):
        return None


def iso_clock(text):
    """PURPOSE: Parse an ISO-like clock without discarding extra fractional digits.
    INPUT: Clock text. OUTPUT: Parsed datetime plus exact fractional second.
    """
    text = text.strip()
    parsed = datetime.fromisoformat(text)
    match = FRACTIONAL_SECOND.search(text)
    fraction = Fraction("0." + match[1]) if match else Fraction(parsed.microsecond, 10**6)
    return parsed.replace(microsecond=0), fraction


def localize(parsed, zone):
    """PURPOSE: Attach documented zone only for an unambiguous local wall clock.
    INPUT: Naive datetime and tzinfo. OUTPUT: Aware datetime or None for a gap or fold.
    """
    if not isinstance(zone, ZoneInfo):
        return parsed.replace(tzinfo=zone)
    instants = {candidate.astimezone(timezone.utc) for fold in (0, 1)
                if (candidate := parsed.replace(tzinfo=zone, fold=fold)).astimezone(timezone.utc)
                .astimezone(zone).replace(tzinfo=None) == parsed}
    return next(iter(instants)) if len(instants) == 1 else None


def timestamp_order(value, zone=None, encoding=None, *, day=None, clock=None):
    """PURPOSE: Sort comparable instants without modifying the exported timestamp.
    INPUT: Raw occurrence, source zone, optional epoch or split-clock encoding and components.
    OUTPUT: Domain-ranked ordering key. Absolute, local and invalid clocks remain separate.
    """
    if value is None or value == "":
        return (3, "", "")
    try:
        if encoding in EPOCH_UNITS:
            return (0, "", Fraction(str(value)) / EPOCH_UNITS[encoding])
        if day is not None and clock is not None:
            day = str(day)
            if len(day) == 8 and day.isdecimal():
                day = f"{day[:4]}-{day[4:6]}-{day[6:]}"
            clock = str(clock)
            if encoding == "seconds_since_midnight":
                midnight, _ = iso_clock(day)
                parsed = midnight + timedelta(seconds=int(clock))
                fraction = Fraction(0)
            else:
                if encoding == "compact_hhmmss":
                    clock = f"{clock[:2]}:{clock[2:4]}:{clock[4:]}"
                parsed, fraction = iso_clock(f"{day}T{clock}")
        else:
            text = str(value).strip()
            if encoding == "compact" and len(text) == 8 and text.isdecimal():
                text = f"{text[:4]}-{text[4:6]}-{text[6:]}"
            parsed, fraction = iso_clock(text)
        if parsed.tzinfo is None and (known := as_timezone(zone)):
            aware = localize(parsed, known)
            if aware is None:
                return (2, str(zone), str(value))
            parsed = aware
        if parsed.tzinfo is not None:
            delta = parsed.astimezone(timezone.utc).replace(tzinfo=None) - EPOCH
            return (0, "", delta.days * 86400 + delta.seconds + fraction)
        delta = parsed - EPOCH
        return (1, zone or "", delta.days * 86400 + delta.seconds + fraction)
    except (OverflowError, TypeError, ValueError, ZeroDivisionError):
        return (2, "", str(value))


def event_time_order(row):
    """PURPOSE: Read the exported clock contract. INPUT: Event row. OUTPUT: Non-mutating chronology key."""
    return timestamp_order(row.get("occurrence_timestamp", row.get("timestamp")),
                           row.get("timestamp_timezone"),
                           row.get("timestamp_clock_encoding") or row.get("timestamp_kind"),
                           day=row.get("timestamp_day"), clock=row.get("timestamp_clock"))
