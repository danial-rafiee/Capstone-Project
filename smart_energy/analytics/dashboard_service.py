"""Read-only orchestration of B analytics and C scoring for the web layer.

The calculator factory is injected: the score formula stays in subsystem C.
This service does not render HTML, call OpenAI, or write database records.
"""

from .building_repository import BuildingRepository
from .energy_settings import EnergySettings
from .errors import AnalyticsError
from .meter_repository import MeterRepository
from .period_analytics import PeriodAnalyticsService
from .reading_repository import ReadingRepository
from .time_window import TimeWindow


class DashboardService:
    """Return current metrics, comparison and score in one summary dictionary."""

    def __init__(self, building_repository, meter_repository, reading_repository, *,
                 tariff, carbon_factor, allowance_share, schedule,
                 score_calculator_factory):
        if not callable(score_calculator_factory):
            raise TypeError("A callable C score calculator factory is required.")
        self._buildings = building_repository
        self._meters = meter_repository
        self._readings = reading_repository
        self._tariff = tariff
        self._carbon_factor = carbon_factor
        self._allowance_share = allowance_share
        self._schedule = schedule
        self._calculator_factory = score_calculator_factory

    @classmethod
    def from_database(cls, database, **configuration):
        """Use the existing B MySQL repositories without changing their code."""
        return cls(BuildingRepository(database), MeterRepository(database),
                   ReadingRepository(database), **configuration)

    def build_summary(self, building_id, meter_id, window, reference_window=None):
        """Load two windows and call B.compare followed by C.calculate.

        The default reference is the immediately preceding window with the
        same elapsed UTC duration. An explicit earlier equal-duration window
        can be supplied instead. Missing coverage never produces a fake score.
        Values remain Decimal/datetime; use to_json_ready at the JSON boundary.
        """
        if not isinstance(window, TimeWindow):
            raise TypeError("The selected window must be a TimeWindow.")
        explicit_reference = reference_window is not None
        if reference_window is None:
            reference_window = TimeWindow(
                window.start - (window.end - window.start), window.start)
        if not isinstance(reference_window, TimeWindow):
            raise TypeError("The reference window must be a TimeWindow.")
        if reference_window.seconds != window.seconds:
            raise ValueError("Current and reference windows must have equal durations.")
        if reference_window.end > window.start:
            raise ValueError("The reference window must end before or at the current start.")

        building = self._buildings.get_by_id(building_id)
        if building is None:
            raise AnalyticsError("Building not found.", code="building_not_found")
        meter = self._meters.get_by_id(meter_id, building)
        if meter is None:
            raise AnalyticsError("Meter not found in this building.", code="meter_not_found")
        settings = EnergySettings(building, self._tariff, self._carbon_factor,
                                  self._allowance_share)
        analytics = PeriodAnalyticsService(settings, self._schedule)
        current_readings = self._readings.list_for_period(meter, window.start, window.end)
        reference_readings = self._readings.list_for_period(
            meter, reference_window.start, reference_window.end)
        result = analytics.compare(meter, current_readings, reference_readings,
                                   window, reference_window)

        evaluation = {"score": None, "growth_penalty": None,
                      "off_hours_penalty": None, "status": "unavailable"}
        if result["score_inputs_status"] == "ready":
            calculator = self._calculator_factory(
                allowance_share=result["score_allowance_share"])
            evaluation = calculator.calculate(**result["score_inputs"])
        score_ready = evaluation["status"] == "ready" and evaluation["score"] is not None
        current = result["current"]
        latest = current["series"][-1] if current["series"] else None
        comparison = dict(result["comparison"])
        saved_percent = comparison["energy_saved_percent"]
        # Conventional change = (current - reference) / reference, unlike savings.
        comparison["energy_change_percent"] = (
            -saved_percent if saved_percent is not None else None)
        return {
            **current,
            "building_name": building.get_name(), "meter_name": meter.get_name(),
            "reference": result["reference"], "comparison": comparison,
            "reference_policy": "explicit" if explicit_reference else "preceding_equal_duration",
            "latest_interval": dict(latest) if latest is not None else None,
            "latest_interval_kwh": latest["energy_kwh"] if latest is not None else None,
            "score": evaluation["score"] if score_ready else None,
            "score_status": "ready" if score_ready else "unavailable",
            "penalties": {
                "growth_penalty": evaluation["growth_penalty"] if score_ready else None,
                "off_hours_penalty": evaluation["off_hours_penalty"] if score_ready else None,
            },
            "score_inputs": result["score_inputs"],
            "score_inputs_status": result["score_inputs_status"],
            "score_inputs_estimated": result["score_inputs_estimated"],
            "score_allowance_share": result["score_allowance_share"],
        }
