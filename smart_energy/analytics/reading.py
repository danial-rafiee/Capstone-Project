"""Interval energy measured by a meter, expressed in kWh."""

from datetime import datetime, timezone
from decimal import Decimal

from .meter import Meter


class Reading:
    """Associate a meter with energy consumed during [start, end)."""

    def __init__(
        self, meter: Meter, start: datetime, end: datetime, energy_kwh: Decimal
    ):
        self.set_meter(meter)
        self.set_interval(start, end)
        self.set_energy_kwh(energy_kwh)

    def get_meter(self) -> Meter:
        return self._meter

    def set_meter(self, meter: Meter) -> None:
        if not isinstance(meter, Meter):
            raise TypeError("Reading must be connected to a Meter object.")
        self._meter = meter

    def get_meter_id(self) -> int:
        return self._meter.get_meter_id()

    def get_interval(self) -> tuple[datetime, datetime]:
        return self._start, self._end

    def set_interval(self, start: datetime, end: datetime) -> None:
        if not isinstance(start, datetime) or not isinstance(end, datetime):
            raise TypeError("Reading start and end must be datetime objects.")
        if start.utcoffset() is None or end.utcoffset() is None:
            raise ValueError("Reading timestamps must include a timezone.")

        start = start.astimezone(timezone.utc)
        end = end.astimezone(timezone.utc)
        if end <= start:
            raise ValueError("Reading end must be later than its start.")

        # Assign both values only after the entire interval is validated.
        self._start = start
        self._end = end

    def get_energy_kwh(self) -> Decimal:
        return self._energy_kwh

    def set_energy_kwh(self, energy_kwh: Decimal) -> None:
        if not isinstance(energy_kwh, Decimal):
            raise TypeError("Reading energy must be a Decimal value in kWh.")
        if not energy_kwh.is_finite() or energy_kwh < 0:
            raise ValueError("Reading energy must be finite and non-negative.")
        self._energy_kwh = energy_kwh
