"""Generate illustrative meter events on demand."""

from collections.abc import Iterator
from datetime import datetime, timezone
from decimal import Decimal

from .meter_event import MeterEvent


def generate_meter_events() -> Iterator[MeterEvent]:
    timestamp = datetime(2026, 11, 4, 9, 1, tzinfo=timezone.utc)

    # Sample inputs, not readings from real devices.
    samples = (
        (101, "6.0", True),
        (102, "0.2", True),
        (103, "4.0", False),
    )

    for meter_id, power, active in samples:
        yield MeterEvent(
            meter_id=meter_id,
            timestamp=timestamp,
            power_kw=Decimal(power),
            active=active,
            interval_seconds=60,
        )