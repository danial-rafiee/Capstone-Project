# Subsystem A tests (Saeid)

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from smart_energy.web.app import create_app
from smart_energy.web.domain.time_range import TimeRange
from smart_energy.web.domain.energy_summary import EnergySummary
from smart_energy.web.domain.coach_panel import CoachPanel
from smart_energy.web.errors import WebAppError, WebAppErrorHandler
from smart_energy.analytics.building import Building
from smart_energy.analytics.meter import Meter


@pytest.fixture
def client():
    app = create_app({"TESTING": True})
    with app.test_client() as client:
        yield client


# Web Routes Testing
def test_dashboard_route_status(client):
    mock_building = MagicMock(spec=Building)
    mock_building.get_building_id.return_value = 1
    mock_building.get_name.return_value = "Test Building"

    mock_meter = MagicMock(spec=Meter)
    mock_meter.get_meter_id.return_value = 101
    mock_meter.get_name.return_value = "Test Meter"

    mock_summary = {
        "totals": "10.0",
        "cost": "3.0",
        "co2": "4.0",
        "score": 85.0,
        "status": "Good"
    }

    with patch('smart_energy.web.app.BuildingRepository.get_by_id', return_value=mock_building), \
            patch('smart_energy.web.app.MeterRepository.get_by_id', return_value=mock_meter), \
            patch('smart_energy.web.app.ReadingRepository.list_for_meter', return_value=[]), \
            patch('smart_energy.web.app.PeriodAnalyticsService') as mock_analytics:
        instance = mock_analytics.return_value
        instance.summarize.return_value = mock_summary

        response = client.get('/')
        assert response.status_code == 200


def test_api_analytics_endpoint(client):
    mock_building = MagicMock(spec=Building)
    mock_building.get_building_id.return_value = 1

    mock_meter = MagicMock(spec=Meter)
    mock_meter.get_meter_id.return_value = 101

    mock_summary = {
        "totals": "10.0",
        "cost": "3.0",
        "co2": "4.0",
        "score": 85.0,
        "status": "Good"
    }

    with patch('smart_energy.web.app.BuildingRepository.get_by_id', return_value=mock_building), \
            patch('smart_energy.web.app.MeterRepository.get_by_id', return_value=mock_meter), \
            patch('smart_energy.web.app.ReadingRepository.list_for_meter', return_value=[]), \
            patch('smart_energy.web.app.PeriodAnalyticsService') as mock_analytics:
        instance = mock_analytics.return_value
        instance.summarize.return_value = mock_summary
        instance.compare.return_value = (mock_summary, mock_summary, 5.0)

        response = client.get('/api/analytics/1/101')
        assert response.status_code == 200
        assert response.json["status"] == "Good"


def test_api_latest_endpoint(client):
    mock_building = MagicMock(spec=Building)
    mock_building.get_building_id.return_value = 1

    mock_meter = MagicMock(spec=Meter)
    mock_meter.get_meter_id.return_value = 101

    mock_reading = MagicMock()
    mock_reading.get_energy_kwh.return_value = 4.75

    with patch('smart_energy.web.app.BuildingRepository.get_by_id', return_value=mock_building), \
            patch('smart_energy.web.app.MeterRepository.get_by_id', return_value=mock_meter), \
            patch('smart_energy.web.app.ReadingRepository.list_for_meter', return_value=[mock_reading]):
        response = client.get('/api/latest')
        assert response.status_code == 200
        assert response.json["latest_interval_kwh"] == 4.75


# Presets & Domain Logic Testing
def test_time_range_presets_and_energy_summary():
    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=1)

    # Testing TimeRange presets
    tr = TimeRange("custom", start=start, end=end)
    assert tr.to_dict()["preset"] == "custom"

    summary = EnergySummary(Decimal('15.5'), Decimal('4.65'), None, 90.5, "No penalties")
    assert summary.get_totals() == Decimal('15.5')
    assert isinstance(summary.to_dict(), dict)


def test_coach_panel_interactions():
    panel = CoachPanel("Initial Question", "Initial Answer")
    panel.submit_question("How to optimize energy usage?")
    assert panel.get_question() == "How to optimize energy usage?"

    panel.set_response("Switch to LED and smart scheduling.")
    assert "LED" in panel.get_answer()
    assert isinstance(panel.to_dict(), dict)


# Service Errors & Routing Error Handling
def test_web_app_error_handling_and_routing(client):
    error = WebAppError("Resource not found", code="not_found")
    handled = WebAppErrorHandler.handle(error)
    assert handled["error"] is True
    assert handled["code"] == "not_found"

    @client.application.route('/test-error')
    def trigger_error():
        raise WebAppError("Bad request test", code="bad_request")

    response = client.get('/test-error')
    assert response.status_code == 400
    assert response.json["code"] == "bad_request"