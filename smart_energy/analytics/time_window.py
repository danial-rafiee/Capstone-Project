"""Validated half-open UTC windows for subsystem B's period calculations."""

from datetime import datetime, timezone
from decimal import Decimal


def duration_seconds(start: datetime, end: datetime) -> Decimal:
    """Keep microsecond precision without converting through binary floats."""
    delta = end - start
    return Decimal(delta.days * 86400 + delta.seconds) + Decimal(delta.microseconds) / Decimal(1000000)


class TimeWindow:
    """An immutable-through-public-API interval [start, end), normalized to UTC."""

    def __init__(self, start: datetime, end: datetime):
        if not isinstance(start, datetime) or not isinstance(end, datetime):
            raise TypeError("Window bounds must be datetime objects.")
        if start.utcoffset() is None or end.utcoffset() is None:
            raise ValueError("Window bounds must include timezones.")
        start, end = start.astimezone(timezone.utc), end.astimezone(timezone.utc)
        if end <= start:
            raise ValueError("Window end must be later than its start.")
        self._start, self._end = start, end

    @property
    def start(self) -> datetime:
        return self._start

    @property
    def end(self) -> datetime:
        return self._end

    @property
    def seconds(self) -> Decimal:
        return duration_seconds(self._start, self._end)
