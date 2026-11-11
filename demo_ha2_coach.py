"""
Subsystem C - Homework Assignment 2 Real-Time Streaming Demo
Author: Hananeh Hajari

Demonstrates all required OOP concepts:
1. Abstract Base Classes: BaseStreamProcessor with @abstractmethod
2. Inheritance & Polymorphism: InactiveMeterFilter, RealTimeScoreTransformer, RealTimeCoachAlerter
3. Operator Overloading: Chaining stages via pipe operator (|)
4. Iterators & Generators: Consuming MeterStream iterator and generate_meter_events() generator
"""
from decimal import Decimal
from datetime import datetime, timezone
from smart_energy.streaming.source.meter_event import MeterEvent
from smart_energy.streaming.source.meter_stream import MeterStream
from smart_energy.coach.stream_pipeline import BaseStreamProcessor
from smart_energy.coach.realtime_coach import (
    InactiveMeterFilter,
    RealTimeScoreTransformer,
    RealTimeCoachAlerter,
)


def run_subsystem_c_ha2_demo():
    print("=" * 68)
    print("Subsystem C: Real-Time Event-Driven Streaming Pipeline Demo")
    print("=" * 68)

    # 1. Synthetic live IoT smart meter events for filtering and scoring evaluation
    sample_events = [
        # Filtered out: sub-threshold consumption (0.2 kW <= 0.5 kW)
        MeterEvent(101, datetime(2026, 11, 5, 10, 0, tzinfo=timezone.utc), Decimal("0.2"), True),
        # Filtered out: inactive meter reading (active = False)
        MeterEvent(102, datetime(2026, 11, 5, 11, 0, tzinfo=timezone.utc), Decimal("4.0"), False),
        # Passed: normal daytime operational load
        MeterEvent(103, datetime(2026, 11, 5, 14, 0, tzinfo=timezone.utc), Decimal("4.5"), True),
        # Passed: daytime excess usage (triggers Growth Penalty Pg)
        MeterEvent(104, datetime(2026, 11, 5, 15, 0, tzinfo=timezone.utc), Decimal("8.0"), True),
        # Passed: off-hours draw exceeding allowance (triggers Off-Hours Penalty Po)
        MeterEvent(105, datetime(2026, 11, 5, 23, 0, tzinfo=timezone.utc), Decimal("3.0"), True),
    ]

    # 2. Instantiate stream using the custom project iterator (MeterStream)
    stream = MeterStream(sample_events)

    # 3. Pipeline composition via operator overloading (|)
    filter_stage = InactiveMeterFilter(min_threshold_kw=Decimal("0.5"))
    transform_stage = RealTimeScoreTransformer(reference_kw=Decimal("5.0"), allowance_share=Decimal("0.10"))
    alert_stage = RealTimeCoachAlerter(score_warning_threshold=75.0)

    # Pipe stages together sequentially
    pipeline = filter_stage | transform_stage | alert_stage

    print(f"\n[Pipeline Architecture]")
    print(f"Total stages composed with '|' operator: {len(pipeline.stages)}")
    for idx, stage in enumerate(pipeline.stages, start=1):
        print(f"  Stage {idx}: {stage.__class__.__name__} (inherits BaseStreamProcessor)")

    # 4. Stream consumption and real-time event transformation
    print(f"\n[Real-Time Streaming Output]")
    for record in pipeline.run(stream):
        print("-" * 68)
        print(f"Meter ID: {record['meter_id']} | Time: {record['timestamp']}")
        print(f"  Power: {record['power_kw']} kW | Off-Hours: {record['is_off_hours']}")
        print(f"  Growth Penalty (Pg): {record['growth_penalty']} | Off-Hours Penalty (Po): {record['off_hours_penalty']}")
        print(f"  Real-time Score: {record['sustainability_score']} / 100")
        print(f"  AI Coach Alert: {record['coach_alert']}")

    print("\n" + "=" * 68)
    print("Real-time pipeline completed successfully.")
    print("=" * 68)


if __name__ == "__main__":
    run_subsystem_c_ha2_demo()


