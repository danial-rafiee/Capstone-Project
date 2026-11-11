"""Demonstrate validation, a generator and a stream iterator."""

from datetime import datetime, timezone
from decimal import Decimal

from smart_energy.streaming.source.meter_event import MeterEvent
from smart_energy.streaming.source.meter_stream import MeterStream
from smart_energy.streaming.source.sample_source import generate_meter_events


def main():
    event = MeterEvent(
        meter_id=101,
        timestamp=datetime(2026, 11, 4, 9, 1, tzinfo=timezone.utc),
        power_kw=Decimal("6.0"),
        active=True,
        interval_seconds=60,
    )

    print("Meter ID:", event.meter_id)
    print("Timestamp:", event.timestamp.isoformat())
    print("Average power:", event.power_kw, "kW")
    print("Active:", event.active)
    print("Interval:", event.interval_seconds, "seconds")
    print("Energy:", event.energy_kwh, "kWh")

    try:
        MeterEvent(
            meter_id=102,
            timestamp=event.timestamp,
            power_kw=Decimal("-1"),
        )
    except ValueError as error:
        print("Invalid event rejected:", error)

    print("\nReading the generated stream")

    events = generate_meter_events()
    stream = MeterStream(events)

    for item in stream:
        print(
            "Meter:", item.meter_id,
            "| Power:", item.power_kw,
            "| Active:", item.active,
        )


if __name__ == "__main__":
    main()