"""Five distinct unit tests for Danial's HA4 contribution.

These tests use in-memory readings and a mocked connection failure. They never
open a real MySQL connection or modify the project's stored readings.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import patch

import pytest
from mysql.connector import Error as MySQLError

from smart_energy.analytics import (
    Building, Meter, Reading, EnergySettings, AnalyticsService,
)
from smart_energy.analytics.database import Database
from smart_energy.analytics.errors import AnalyticsError, AnalyticsErrorHandler


@pytest.fixture
def sample_data():
    """Create fresh objects for each test, with no shared mutable state."""
    building = Building(1, "Demo Office")
    meter = Meter(101, building, "Main Meter")
    settings = EnergySettings(
        building, Decimal("0.30"), Decimal("0.40"), Decimal("0.10")
    )
    start = datetime(2026, 11, 4, 9, 0, tzinfo=timezone.utc)
    readings = [
        Reading(meter, start, start + timedelta(minutes=5), Decimal("3.0")),
        Reading(meter, start + timedelta(minutes=5),
                start + timedelta(minutes=10), Decimal("2.0")),
    ]
    return meter, settings, start, readings


def test_valid_readings_produce_correct_energy_cost_and_carbon(sample_data):
    _, settings, _, readings = sample_data

    result = AnalyticsService(settings, readings).totals()

    assert result == {
        "building_id": 1,
        "reading_count": 2,
        "energy_kwh": Decimal("5.0"),
        "estimated_cost_eur": Decimal("1.50"),
        "estimated_co2_kg": Decimal("2.00"),
    }


def test_no_readings_raise_a_specific_application_error(sample_data):
    _, settings, _, _ = sample_data
    service = AnalyticsService(settings)

    with pytest.raises(AnalyticsError) as caught:
        service.totals()

    assert caught.value.code == "no_readings"
    assert AnalyticsErrorHandler().handle(caught.value) == {
        "error": {
            "code": "no_readings",
            "message": "No readings are available for calculation.",
        }
    }


def test_negative_energy_is_rejected_and_formatted_as_validation_error(sample_data):
    meter, _, start, _ = sample_data

    with pytest.raises(ValueError) as caught:
        Reading(meter, start, start + timedelta(minutes=5), Decimal("-1"))

    response = AnalyticsErrorHandler().handle(caught.value)
    assert response == {
        "error": {
            "code": "validation_error",
            "message": "The energy data or operation is not valid.",
        }
    }


def test_overlap_is_rejected_without_changing_existing_results(sample_data):
    meter, settings, start, readings = sample_data
    service = AnalyticsService(settings, readings)
    before = service.totals()
    overlap = Reading(
        meter, start + timedelta(minutes=2),
        start + timedelta(minutes=7), Decimal("1.0"),
    )

    with pytest.raises(ValueError) as caught:
        service.add_reading(overlap)

    assert AnalyticsErrorHandler().handle(caught.value)["error"]["code"] == "validation_error"
    assert service.get_readings() == readings
    assert service.totals() == before


def test_connection_failure_preserves_cause_and_hides_internal_details(monkeypatch):
    monkeypatch.setenv("SMART_ENERGY_DB_PORT", "3306")
    driver_error = MySQLError("INTERNAL_DB_DETAIL_FOR_TEST_ONLY")

    with patch(
        "smart_energy.analytics.database.mysql.connector.connect",
        side_effect=driver_error,
    ):
        with pytest.raises(AnalyticsError) as caught:
            Database().connect()

    assert caught.value.code == "database_unavailable"
    assert caught.value.__cause__ is driver_error
    response = AnalyticsErrorHandler().handle(caught.value)
    assert response == {
        "error": {
            "code": "database_unavailable",
            "message": "The energy database connection is unavailable.",
        }
    }
    assert "INTERNAL_DB_DETAIL_FOR_TEST_ONLY" not in str(response)
