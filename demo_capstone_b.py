"""Demonstrate B's selected-period contract, without changing stored data.

python demo_capstone_b.py          # simulated complete/partial/missing periods
python demo_capstone_b.py --mysql  # read existing HA3 meter 101 data only
"""

import argparse
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from smart_energy.analytics import Building, Meter, Reading, EnergySettings
from smart_energy.analytics.period_analytics import PeriodAnalyticsService, to_json_ready
from smart_energy.analytics.time_window import TimeWindow


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mysql', action='store_true', help='Read existing sample data; never insert or delete.')
    args = parser.parse_args()
    start = datetime(2026, 11, 4, 9, tzinfo=timezone.utc)
    window = TimeWindow(start, start + timedelta(minutes=10))
    if args.mysql:
        from smart_energy.analytics.database import Database
        from smart_energy.analytics.building_repository import BuildingRepository
        from smart_energy.analytics.meter_repository import MeterRepository
        from smart_energy.analytics.reading_repository import ReadingRepository
        database = Database()
        building = BuildingRepository(database).get_by_id(1)
        meter = MeterRepository(database).get_by_id(101, building) if building else None
        if meter is None:
            raise RuntimeError('Existing sample building 1 and meter 101 are required; run the HA3 setup first.')
        readings = ReadingRepository(database).list_for_period(meter, window.start, window.end)
    else:
        building = Building(1, 'Demo Office')
        meter = Meter(101, building, 'Main Meter')
        readings = [Reading(meter, start, start + timedelta(minutes=5), Decimal('3')),
                    Reading(meter, start + timedelta(minutes=5), window.end, Decimal('2'))]
    # Illustrative fixed factors; real configuration is supplied by the caller.
    service = PeriodAnalyticsService(EnergySettings(building, Decimal('0.30'), Decimal('0.40'), Decimal('0.10')))
    result = service.summarize(meter, readings, window)
    print(('MYSQL READ-ONLY PERIOD' if args.mysql else 'SIMULATED COMPLETE PERIOD'))
    print(json.dumps(to_json_ready(result), indent=2))
    if not args.mysql:
        partial = service.summarize(meter, readings[:1], window)
        print('PARTIAL:', partial['status'], 'coverage:', partial['coverage_fraction'])
        missing = service.summarize(meter, [], window)
        print('MISSING:', missing['status'], 'energy:', missing['energy_kwh'])
        reference_window = TimeWindow(start - timedelta(days=1), window.end - timedelta(days=1))
        reference = [Reading(meter, reference_window.start, reference_window.end, Decimal('7'))]
        comparison = service.compare(meter, readings, reference, window, reference_window)
        print('SIMULATED REFERENCE COMPARISON:')
        print(json.dumps(to_json_ready(comparison['comparison']), indent=2))


if __name__ == '__main__':
    main()
