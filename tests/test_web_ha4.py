import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from smart_energy.web.app import create_app
from smart_energy.web.domain.time_range import TimeRange
from smart_energy.web.domain.energy_summary import EnergySummary
from smart_energy.web.domain.coach_panel import CoachPanel
from smart_energy.analytics.building import Building
from smart_energy.analytics.meter import Meter


@pytest.fixture
def client():
    app = create_app({"TESTING": True})
    with app.test_client() as client:
        yield client


def test_dashboard_route_status(client):
    # Use spec=Building and spec=Meter so isinstance checks pass successfully
    mock_building = MagicMock(spec=Building)
    mock_building.get_building_id.return_value = 1
    mock_building.get_name.return_value = "Test Building"

    mock_meter = MagicMock(spec=Meter)
    mock_meter.get_meter_id.return_value = 101
    mock_meter.get_name.return_value = "Test Meter"

    with patch('smart_energy.web.app.BuildingRepository.get_by_id', return_value=mock_building), \
            patch('smart_energy.web.app.MeterRepository.get_by_id', return_value=mock_meter), \
            patch('smart_energy.web.app.ReadingRepository.list_for_meter', return_value=[]), \
            patch('smart_energy.web.app.AnalyticsService.totals',
                  return_value={'energy_kwh': 10, 'cost_eur': 3, 'co2_kg': 4}):
        response = client.get('/')
        assert response.status_code == 200


def test_api_analytics_endpoint(client):
    mock_building = MagicMock(spec=Building)
    mock_building.get_building_id.return_value = 1
    mock_building.get_name.return_value = "Test Building"

    mock_meter = MagicMock(spec=Meter)
    mock_meter.get_meter_id.return_value = 101
    mock_meter.get_name.return_value = "Test Meter"

    with patch('smart_energy.web.app.BuildingRepository.get_by_id', return_value=mock_building), \
            patch('smart_energy.web.app.MeterRepository.get_by_id', return_value=mock_meter), \
            patch('smart_energy.web.app.ReadingRepository.list_for_meter', return_value=[]), \
            patch('smart_energy.web.app.AnalyticsService.totals',
                  return_value={'energy_kwh': 10, 'cost_eur': 3, 'co2_kg': 4}):
        response = client.get('/api/analytics/1/101')
        assert response.status_code == 200
        assert response.json["building_id"] == 1


def test_time_range_conversion():
    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=1)
    tr = TimeRange("custom", start=start, end=end)
    data = tr.to_dict()
    assert isinstance(data, dict)
    assert data["preset"] == "custom"


def test_energy_summary_decimal_handling():
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