from decimal import Decimal
from datetime import datetime, timezone
from smart_energy.streaming.source.meter_event import MeterEvent
from smart_energy.streaming.source.meter_stream import MeterStream
from smart_energy.streaming.pipeline import Pipeline
from smart_energy.coach.realtime_coach import (
    InactiveMeterFilter,
    RealTimeScoreTransformer,
)


def main():
    print("=" * 60)
    print("Saeid's Pipeline & Stream Processing Integration Demo")
    print("=" * 60)

    # 1. Create test meter events
    events = [
        MeterEvent(101, datetime(2026, 11, 6, 12, 0, tzinfo=timezone.utc), Decimal("0.3"), True),  # Will be filtered out
        MeterEvent(102, datetime(2026, 11, 6, 12, 5, tzinfo=timezone.utc), Decimal("6.0"), True),  # Will pass through
    ]

    stream = MeterStream(events)

    # 2. Define pipeline stages and use operator overloading (|)
    filter_stage = InactiveMeterFilter(min_threshold_kw=Decimal("0.5"))
    transform_stage = RealTimeScoreTransformer(reference_kw=Decimal("5.0"), allowance_share=Decimal("0.10"))

    # Combine stages using the custom operator overloading
    pipeline = filter_stage | transform_stage

    print(f"Pipeline successfully created with {len(pipeline.stages)} stages.")

    # 3. Execute the data stream
    for result in pipeline.run(stream):
        print("-" * 60)
        print(f"Processed Result -> Meter ID: {result['meter_id']} | Score: {result['sustainability_score']}")

    print("=" * 60)


if __name__ == "__main__":
    main()