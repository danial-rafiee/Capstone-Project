"""Single-meter period totals, coverage and explicit reference comparisons.

Partial measurement intervals are allocated using constant average power.
Such results are explicitly marked as estimated. Missing time is never filled
with zero or silently extrapolated to a full-period total.
"""

from datetime import datetime, timezone
from decimal import Decimal

from .analytics_service import AnalyticsService
from .energy_settings import EnergySettings
from .meter import Meter
from .reading import Reading
from .time_window import TimeWindow, duration_seconds


def to_json_ready(value):
    """Serialize Decimal as exact strings; leave nulls and booleans intact."""
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        if value.utcoffset() is None:
            raise ValueError("Cannot serialize a timestamp without a timezone.")
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value, dict):
        return {key: to_json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_json_ready(item) for item in value]
    return value


class PeriodAnalyticsService:
    """Prepare B data for A's dashboard; scoring and AI remain C's job."""

    def __init__(self, settings: EnergySettings):
        if not isinstance(settings, EnergySettings):
            raise TypeError("Period settings must be an EnergySettings object.")
        self._settings = settings

    def summarize(self, meter: Meter, readings: list[Reading], window: TimeWindow) -> dict:
        if not isinstance(meter, Meter) or not isinstance(window, TimeWindow):
            raise TypeError("A Meter and TimeWindow are required.")
        if meter.get_building() is not self._settings.get_building():
            raise ValueError("The meter and settings must share the same Building object.")
        # Reuse existing relationship, type, duplicate and overlap checks.
        AnalyticsService(self._settings, readings)
        if any(reading.get_meter() is not meter for reading in readings):
            raise ValueError("Every reading must reference the supplied Meter object.")

        energy, covered = Decimal(0), Decimal(0)
        series, gaps = [], []
        cursor = window.start
        for reading in sorted(readings, key=lambda item: item.get_interval()[0]):
            source_start, source_end = reading.get_interval()
            start, end = max(source_start, window.start), min(source_end, window.end)
            if end <= start:
                continue
            if start > cursor:
                gaps.append({"start": cursor, "end": start})
            cursor = end
            seconds = duration_seconds(start, end)
            source_seconds = duration_seconds(source_start, source_end)
            # Dividing last also preserves exact whole-interval energy.
            interval_energy = reading.get_energy_kwh() * seconds / source_seconds
            estimated = start != source_start or end != source_end
            series.append({
                "start": start, "end": end, "energy_kwh": interval_energy,
                "average_power_kw": reading.get_energy_kwh() * Decimal(3600) / source_seconds,
                "energy_estimated": estimated,
            })
            covered += seconds
            energy += interval_energy

        if cursor < window.end:
            gaps.append({"start": cursor, "end": window.end})
        status = "no_data" if not series else "complete" if covered == window.seconds else "partial"
        has_data = bool(series)
        return {
            "building_id": meter.get_building_id(), "meter_id": meter.get_meter_id(),
            "start": window.start, "end": window.end,
            "reading_count": len(series), "status": status,
            "period_seconds": window.seconds, "covered_seconds": covered,
            "coverage_fraction": covered / window.seconds,
            "energy_kwh": energy if has_data else None,
            "estimated_cost_eur": energy * self._settings.get_tariff() if has_data else None,
            "estimated_co2_kg": energy * self._settings.get_carbon_factor() if has_data else None,
            "energy_estimated": any(item["energy_estimated"] for item in series),
            "allocation_method": "constant_average_power",
            "tariff_eur_per_kwh": self._settings.get_tariff(),
            "carbon_factor_kg_per_kwh": self._settings.get_carbon_factor(),
            "series": series, "gaps": gaps,
        }

    def compare(
        self, meter: Meter, current_readings: list[Reading], reference_readings: list[Reading],
        current_window: TimeWindow, reference_window: TimeWindow,
    ) -> dict:
        """Compare explicit equal-duration periods using the same current factors.

        Savings may be negative. This is a period comparison, not proof of a
        causal saving or a weather/occupancy-normalized baseline.
        """
        if not isinstance(current_window, TimeWindow) or not isinstance(reference_window, TimeWindow):
            raise TypeError("Comparison windows must be TimeWindow objects.")
        if current_window.seconds != reference_window.seconds:
            raise ValueError("Current and reference windows must have equal durations.")
        if reference_window.end > current_window.start:
            raise ValueError("The reference window must end before or at the current start.")
        current = self.summarize(meter, current_readings, current_window)
        reference = self.summarize(meter, reference_readings, reference_window)
        ready = current["status"] == reference["status"] == "complete"
        saved = reference["energy_kwh"] - current["energy_kwh"] if ready else None
        reference_energy = reference["energy_kwh"]
        return {
            "current": current, "reference": reference,
            "comparison": {
                "status": "ready" if ready else "unavailable",
                "energy_saved_kwh": saved,
                "cost_saved_eur": saved * self._settings.get_tariff() if ready else None,
                "co2_saved_kg": saved * self._settings.get_carbon_factor() if ready else None,
                "energy_saved_percent": saved * Decimal(100) / reference_energy
                    if ready and reference_energy > 0 else None,
                "energy_estimated": current["energy_estimated"] or reference["energy_estimated"],
            },
        }
