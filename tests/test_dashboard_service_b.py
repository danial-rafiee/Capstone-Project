"""B orchestration tests using real analytics/C scoring and fake repository IO."""

from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock
from zoneinfo import ZoneInfo

import pytest

from smart_energy.analytics import Building, Meter, Reading
from smart_energy.analytics.dashboard_service import DashboardService
from smart_energy.analytics.errors import AnalyticsError
from smart_energy.analytics.operating_schedule import OperatingSchedule
from smart_energy.analytics.period_analytics import to_json_ready
from smart_energy.analytics.time_window import TimeWindow
from smart_energy.coach.score_calculator import ScoreCalculator


@pytest.fixture
def scenario():
    building = Building(1, "Demo Office")
    meter = Meter(101, building, "Main Meter")
    zone = ZoneInfo("Europe/Berlin")
    current = TimeWindow(datetime(2026, 11, 4, 8, tzinfo=zone),
                         datetime(2026, 11, 4, 10, tzinfo=zone))
    reference = TimeWindow(datetime(2026, 11, 3, 8, tzinfo=zone),
                           datetime(2026, 11, 3, 10, tzinfo=zone))
    def readings(window, first, second):
        middle = window.start + timedelta(hours=1)
        return [Reading(meter, window.start, middle, Decimal(first)),
                Reading(meter, middle, window.end, Decimal(second))]
    buildings = Mock()
    buildings.get_by_id.return_value = building
    meters = Mock()
    meters.get_by_id.return_value = meter
    repository = Mock()
    repository.list_for_period.side_effect = [readings(current, "2", "3"),
                                              readings(reference, "3", "4")]
    factory = Mock(side_effect=ScoreCalculator)
    config = dict(tariff=Decimal(".30"), carbon_factor=Decimal(".40"),
                  allowance_share=Decimal(".10"),
                  schedule=OperatingSchedule("Europe/Berlin", {
                      day: [("09:00", "17:00")] for day in range(5)}),
                  score_calculator_factory=factory)
    service = DashboardService(buildings, meters, repository, **config)
    return service, current, reference, buildings, meters, repository, factory, readings


def test_combined_payload_uses_real_b_and_c_and_shared_allowance(scenario):
    service, now, before, _, _, repo, factory, _ = scenario
    result = service.build_summary(1, 101, now, before)
    assert result["energy_kwh"] == 5
    assert result["estimated_cost_eur"] == Decimal("1.50")
    assert result["estimated_co2_kg"] == 2
    assert result["score"] == 74
    assert result["penalties"] == {"growth_penalty": 0, "off_hours_penalty": 26}
    assert result["score_status"] == "ready"
    assert result["latest_interval_kwh"] == 3
    assert result["latest_interval"]["end"] == now.end
    assert result["comparison"]["energy_change_percent"] < 0
    assert result["comparison"]["energy_saved_percent"] > 0
    assert result["reference_policy"] == "explicit"
    factory.assert_called_once_with(allowance_share=Decimal(".10"))
    assert repo.list_for_period.call_count == 2


def test_default_reference_is_adjacent_equal_elapsed_duration(scenario):
    service, now, _, _, _, repo, _, readings = scenario
    previous = TimeWindow(now.start - (now.end - now.start), now.start)
    repo.list_for_period.side_effect = [readings(now, "2", "3"),
                                       readings(previous, "3", "4")]
    result = service.build_summary(1, 101, now)
    assert result["reference"]["start"] == previous.start
    assert result["reference"]["end"] == now.start
    assert result["reference_policy"] == "preceding_equal_duration"


@pytest.mark.parametrize("missing", ["current", "reference"])
def test_missing_period_disables_calculator_without_fabricating_zero(scenario, missing):
    service, now, before, _, _, repo, factory, readings = scenario
    repo.list_for_period.side_effect = [
        [] if missing == "current" else readings(now, "2", "3"),
        [] if missing == "reference" else readings(before, "3", "4")]
    result = service.build_summary(1, 101, now, before)
    assert result["score"] is None
    assert result["score_status"] == "unavailable"
    assert result["comparison"]["energy_change_percent"] is None
    if missing == "current":
        assert result["energy_kwh"] is None
        assert result["latest_interval_kwh"] is None
        assert result["estimated_cost_eur"] is None
    factory.assert_not_called()


def test_partial_period_preserves_coverage_and_does_not_score(scenario):
    service, now, before, _, _, repo, factory, readings = scenario
    repo.list_for_period.side_effect = [readings(now, "2", "3")[:1],
                                       readings(before, "3", "4")]
    result = service.build_summary(1, 101, now, before)
    assert result["energy_kwh"] == 2
    assert result["status"] == "partial"
    assert result["coverage_fraction"] == Decimal(".5")
    assert result["score"] is None
    factory.assert_not_called()


def test_measured_zero_energy_is_preserved_but_not_scored(scenario):
    service, now, before, _, _, repo, factory, readings = scenario
    repo.list_for_period.side_effect = [readings(now, "0", "0"),
                                       readings(before, "3", "4")]
    result = service.build_summary(1, 101, now, before)
    assert result["energy_kwh"] == result["estimated_cost_eur"] == 0
    assert result["status"] == "complete"
    assert result["score"] is None
    assert result["comparison"]["energy_change_percent"] == -100
    factory.assert_not_called()


def test_score_zero_is_a_valid_result_not_unavailable(scenario):
    service, now, before, _, _, repo, _, readings = scenario
    repo.list_for_period.side_effect = [readings(now, "20", "1"),
                                       readings(before, "3", "4")]
    result = service.build_summary(1, 101, now, before)
    assert result["score"] == 0
    assert result["score_status"] == "ready"


def test_latest_is_clipped_to_selected_period_and_marked_estimated(scenario):
    service, now, before, _, _, repo, _, _ = scenario
    meter = service._meters.get_by_id.return_value
    repo.list_for_period.side_effect = [
        [Reading(meter, now.start - timedelta(hours=1), now.end, Decimal("9"))],
        [Reading(meter, before.start, before.end, Decimal("8"))]]
    result = service.build_summary(1, 101, now, before)
    assert result["latest_interval_kwh"] == result["energy_kwh"] == 6
    assert result["latest_interval"]["start"] == now.start
    assert result["score_inputs_estimated"] is True


@pytest.mark.parametrize("kind, code", [("building", "building_not_found"),
                                        ("meter", "meter_not_found")])
def test_missing_entities_raise_specific_error_before_reading_query(scenario, kind, code):
    service, now, before, buildings, meters, repo, _, _ = scenario
    (buildings if kind == "building" else meters).get_by_id.return_value = None
    with pytest.raises(AnalyticsError) as error:
        service.build_summary(1, 101, now, before)
    assert error.value.code == code
    repo.list_for_period.assert_not_called()


def test_database_errors_are_not_returned_as_successful_zero(scenario):
    service, now, before, _, _, repo, _, _ = scenario
    repo.list_for_period.side_effect = AnalyticsError("Unavailable", "database_unavailable")
    with pytest.raises(AnalyticsError, match="Unavailable"):
        service.build_summary(1, 101, now, before)


def test_missing_calendar_disables_score_without_assuming_zero_off_hours(scenario):
    service, now, before, _, _, _, factory, _ = scenario
    service._schedule = None
    result = service.build_summary(1, 101, now, before)
    assert result["energy_kwh"] == 5
    assert result["off_hours_energy_kwh"] is None
    assert result["off_hours_status"] == "not_configured"
    assert result["score"] is None
    factory.assert_not_called()


def test_calculator_failure_is_propagated_to_web_error_boundary(scenario):
    service, now, before, _, _, _, factory, _ = scenario
    factory.side_effect = RuntimeError("C scoring unavailable")
    with pytest.raises(RuntimeError, match="C scoring unavailable"):
        service.build_summary(1, 101, now, before)


def test_invalid_reference_rejected_before_io(scenario):
    service, now, _, buildings, _, _, _, _ = scenario
    with pytest.raises(ValueError, match="equal durations"):
        service.build_summary(1, 101, now, TimeWindow(now.start-timedelta(hours=1), now.start))
    with pytest.raises(ValueError, match="reference window"):
        service.build_summary(1, 101, now, now)
    buildings.get_by_id.assert_not_called()


def test_combined_summary_serializes_without_losing_null_or_precision(scenario):
    import json
    service, now, before, _, _, _, _, _ = scenario
    result = to_json_ready(service.build_summary(1, 101, now, before))
    assert result["energy_kwh"] == "5"
    assert float(result["score"]) == 74
    assert result["latest_interval"]["end"].endswith("+00:00")
    json.dumps(result)
