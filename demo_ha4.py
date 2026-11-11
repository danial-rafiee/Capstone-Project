"""Demonstrate subsystem B error handling without modifying MySQL data."""

import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import patch

from mysql.connector import Error as MySQLError

from smart_energy.analytics import (
    Building, Meter, Reading, EnergySettings, AnalyticsService,
)
from smart_energy.analytics.database import Database
from smart_energy.analytics.errors import AnalyticsErrorHandler


def show_error(label, operation):
    """Catch at the application boundary and format the subsystem error."""
    try:
        operation()
    except Exception as error:
        response = AnalyticsErrorHandler().handle(error)
        print(label + ":", json.dumps(response))
    else:
        raise RuntimeError("The example was expected to reject this operation.")


def main():
    building = Building(1, "Demo Office")
    meter = Meter(101, building, "Main Meter")
    settings = EnergySettings(
        building, Decimal("0.30"), Decimal("0.40"), Decimal("0.10")
    )
    start = datetime(2026, 11, 4, 9, 0, tzinfo=timezone.utc)
    middle = start + timedelta(minutes=5)
    end = middle + timedelta(minutes=5)
    readings = [
        Reading(meter, start, middle, Decimal("3.0")),
        Reading(meter, middle, end, Decimal("2.0")),
    ]
    service = AnalyticsService(settings, readings)

    print("Valid calculation:", json.dumps(service.totals(), default=str))

    show_error("Missing readings", AnalyticsService(settings).totals)

    show_error(
        "Invalid energy",
        lambda: Reading(meter, start, middle, Decimal("-1")),
    )

    show_error("Duplicate interval", lambda: service.add_reading(readings[0]))
    print("Reading count after rejection:", len(service.get_readings()))

    # Inject a connection failure; do not stop MySQL or touch its data.
    with patch(
        "smart_energy.analytics.database.mysql.connector.connect",
        side_effect=MySQLError("Simulated internal database failure"),
    ):
        show_error("Simulated connection failure", Database().connect)


if __name__ == "__main__":
    main()
