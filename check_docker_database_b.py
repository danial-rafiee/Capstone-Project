"""Read-only verification of the dedicated Docker sample database.

Expects the simulated rows from docker/analytics/20-demo-readings.sql. Does not
create, overwrite or delete rows. Run against the Docker database, not an
unrelated installation with different data.
"""

import json
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from smart_energy.analytics import EnergySettings
from smart_energy.analytics.building_repository import BuildingRepository
from smart_energy.analytics.database import Database
from smart_energy.analytics.meter_repository import MeterRepository
from smart_energy.analytics.operating_schedule import OperatingSchedule
from smart_energy.analytics.period_analytics import PeriodAnalyticsService, to_json_ready
from smart_energy.analytics.reading_repository import ReadingRepository
from smart_energy.analytics.time_window import TimeWindow


def main():
    database = Database()
    building = BuildingRepository(database).get_by_id(1)
    meter = MeterRepository(database).get_by_id(101, building) if building else None
    if meter is None:
        raise RuntimeError('The dedicated Docker sample building 1 and meter 101 are missing.')
    zone = ZoneInfo('Europe/Berlin')
    current = TimeWindow(datetime(2026, 11, 4, 8, tzinfo=zone), datetime(2026, 11, 4, 10, tzinfo=zone))
    reference = TimeWindow(datetime(2026, 11, 3, 8, tzinfo=zone), datetime(2026, 11, 3, 10, tzinfo=zone))
    repository = ReadingRepository(database)
    current_readings = repository.list_for_period(meter, current.start, current.end)
    reference_readings = repository.list_for_period(meter, reference.start, reference.end)
    settings = EnergySettings(building, Decimal('.30'), Decimal('.40'), Decimal('.10'))
    schedule = OperatingSchedule('Europe/Berlin', {day: [('09:00', '17:00')] for day in range(5)})
    report = PeriodAnalyticsService(settings, schedule).compare(
        meter, current_readings, reference_readings, current, reference)
    expected = {'current_energy': Decimal('5'), 'reference_energy': Decimal('7'),
                'off_hours_energy': Decimal('2')}
    if report['score_inputs_status'] != 'ready' or report['score_inputs'] != expected:
        raise RuntimeError('Docker sample data differs from the documented E=5, R=7, O=2 scenario.')
    if report['score_inputs_estimated']:
        raise RuntimeError('The hourly Docker sample must not require energy proration.')
    print('SIMULATED DOCKER DATABASE: read-only E/R/O verification passed')
    print(json.dumps(to_json_ready({
        'score_inputs': report['score_inputs'],
        'current_cost_eur': report['current']['estimated_cost_eur'],
        'current_co2_kg': report['current']['estimated_co2_kg'],
        'comparison': report['comparison'],
    }), indent=2))


if __name__ == '__main__':
    main()
