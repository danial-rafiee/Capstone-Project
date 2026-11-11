"""B/C dashboard handoff demo; simulated by default, MySQL read-only with --mysql.

Demo calendar: Monday-Friday 09:00-17:00 Europe/Berlin.
Explicit historical sample periods are used, not live readings.
"""

import argparse
import json
from datetime import datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from smart_energy.analytics import Building, Meter, Reading
from smart_energy.analytics.dashboard_service import DashboardService
from smart_energy.analytics.database import Database
from smart_energy.analytics.operating_schedule import OperatingSchedule
from smart_energy.analytics.period_analytics import to_json_ready
from smart_energy.analytics.time_window import TimeWindow
from smart_energy.coach.score_calculator import ScoreCalculator


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mysql", action="store_true", help="Read existing sample data; never seed/write.")
    args = parser.parse_args()
    configuration = dict(
        tariff=Decimal("0.30"), carbon_factor=Decimal("0.40"),
        allowance_share=Decimal("0.10"),
        schedule=OperatingSchedule("Europe/Berlin", {
            day: [("09:00", "17:00")] for day in range(5)}),
        score_calculator_factory=ScoreCalculator,
    )
    zone = ZoneInfo("Europe/Berlin")
    window = TimeWindow(datetime(2026, 11, 4, 8, tzinfo=zone),
                        datetime(2026, 11, 4, 10, tzinfo=zone))
    reference = TimeWindow(datetime(2026, 11, 3, 8, tzinfo=zone),
                           datetime(2026, 11, 3, 10, tzinfo=zone))
    if args.mysql:
        service = DashboardService.from_database(Database(), **configuration)
    else:
        building = Building(1, "Demo Office")
        meter = Meter(101, building, "Main Meter")
        def intervals(period, energies):
            middle = period.start + timedelta(hours=1)
            return [Reading(meter, period.start, middle, Decimal(energies[0])),
                    Reading(meter, middle, period.end, Decimal(energies[1]))]
        data = intervals(window, ("2", "3")) + intervals(reference, ("3", "4"))
        # Fake repository IO only; B analytics and C score calculator are real.
        repository = SimpleNamespace(list_for_period=lambda meter, start, end: [
            reading for reading in data
            if reading.get_interval()[0] < end and reading.get_interval()[1] > start])
        service = DashboardService(
            SimpleNamespace(get_by_id=lambda building_id: building),
            SimpleNamespace(get_by_id=lambda meter_id, building: meter),
            repository, **configuration)
    print("READ-ONLY MYSQL" if args.mysql else "SIMULATED REPOSITORY DATA; REAL B/C CALCULATIONS")
    print(json.dumps(to_json_ready(service.build_summary(1, 101, window, reference)), indent=2))


if __name__ == "__main__":
    main()
