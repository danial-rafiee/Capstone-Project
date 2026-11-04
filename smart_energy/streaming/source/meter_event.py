"""A validated meter reading for one measurement interval."""

from datetime import datetime, timezone
from decimal import Decimal


class MeterEvent:
    def __init__(
        self,
        meter_id: int,
        timestamp: datetime,
        power_kw: Decimal,
        active: bool = True,
        interval_seconds: int = 60,
    ):
        if isinstance(meter_id, bool) or not isinstance(meter_id, int):
            raise TypeError("Meter ID must be an integer.")
        if meter_id <= 0:
            raise ValueError("Meter ID must be positive.")

        if not isinstance(timestamp, datetime):
            raise TypeError("Timestamp must be a datetime object.")
        if timestamp.utcoffset() is None:
            raise ValueError("Timestamp must include a timezone.")

        if not isinstance(power_kw, Decimal):
            raise TypeError("Power must be a Decimal value.")
        if not power_kw.is_finite() or power_kw < 0:
            raise ValueError("Power must be finite and non-negative.")

        if not isinstance(active, bool):
            raise TypeError("Active must be True or False.")

        if isinstance(interval_seconds, bool) or not isinstance(interval_seconds, int):
            raise TypeError("Interval must be an integer number of seconds.")
        if interval_seconds <= 0:
            raise ValueError("Interval must be positive.")

        self._meter_id = meter_id
        self._timestamp = timestamp.astimezone(timezone.utc)
        self._power_kw = power_kw
        self._active = active
        self._interval_seconds = interval_seconds

    @property
    def meter_id(self) -> int:
        return self._meter_id

    @property
    def timestamp(self) -> datetime:
        return self._timestamp

    @property
    def power_kw(self) -> Decimal:
        return self._power_kw

    @property
    def active(self) -> bool:
        return self._active

    @property
    def interval_seconds(self) -> int:
        return self._interval_seconds

    @property
    def energy_kwh(self) -> Decimal:
        """Energy calculated from average power over this interval."""
        return self._power_kw * Decimal(self._interval_seconds) / Decimal("3600")