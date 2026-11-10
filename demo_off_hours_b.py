"""Simulated B E/R/O handoff; no database writes, score or AI calls.

Agreed demo assumption: Monday-Friday 09:00-17:00, Europe/Berlin.
These values are illustrative and are not a real building configuration.
"""

import argparse
import json
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from smart_energy.analytics import Building, Meter, Reading, EnergySettings
from smart_energy.analytics.operating_schedule import OperatingSchedule
from smart_energy.analytics.period_analytics import PeriodAnalyticsService, to_json_ready
from smart_energy.analytics.time_window import TimeWindow


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--full', action='store_true', help='Print the complete period JSON contract.')
    args = parser.parse_args()
    building = Building(1, 'Demo Office')
    meter = Meter(101, building, 'Main Meter')
    settings = EnergySettings(building, Decimal('.30'), Decimal('.40'), Decimal('.10'))
    schedule = OperatingSchedule('Europe/Berlin', {day: [('09:00', '17:00')] for day in range(5)})
    zone = ZoneInfo(schedule.get_timezone())
    current = TimeWindow(datetime(2026, 11, 4, 8, tzinfo=zone), datetime(2026, 11, 4, 10, tzinfo=zone))
    reference = TimeWindow(datetime(2026, 11, 3, 8, tzinfo=zone), datetime(2026, 11, 3, 10, tzinfo=zone))
    # One-hour readings align with the 09:00 opening boundary: no proration.
    def readings(window, first, second):
        from datetime import timedelta
        middle = window.start + timedelta(hours=1)
        return [Reading(meter, window.start, middle, Decimal(first)),
                Reading(meter, middle, window.end, Decimal(second))]
    service = PeriodAnalyticsService(settings, schedule)
    result = service.compare(meter, readings(current, '2', '3'), readings(reference, '3', '4'),
                             current, reference)
    # This is a documented integration example, not a score calculated by B.
    handoff = {'score_inputs': result['score_inputs'],
               'allowance_share': result['score_allowance_share'],
               'status': result['score_inputs_status']}
    print('SIMULATED SCHEDULE: Monday-Friday 09:00-17:00 Europe/Berlin')
    print('B SUMMARY:')
    if args.full:
        print(json.dumps(to_json_ready(result), indent=2))
    else:
        for label in ('current', 'reference'):
            summary = result[label]
            print(label.upper(), json.dumps(to_json_ready({key: summary[key] for key in (
                'status', 'energy_kwh', 'off_hours_energy_kwh', 'occupied_energy_kwh',
                'off_hours_energy_estimated', 'coverage_fraction')})))
        print('COMPARISON:', json.dumps(to_json_ready(result['comparison'])))
    print('E/R/O INPUTS FOR C (score not calculated by B):')
    print(json.dumps(to_json_ready(handoff), indent=2))
    missing = service.summarize(meter, [], current)
    print('NO DATA:', missing['off_hours_status'], 'O:', missing['off_hours_energy_kwh'])


if __name__ == '__main__':
    main()
