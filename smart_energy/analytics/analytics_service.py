"""In-memory energy totals for validated readings from one building."""

from decimal import Decimal

from .energy_settings import EnergySettings
from .reading import Reading


class AnalyticsService:
    """Calculate consumption, cost and CO2 for the readings supplied to it."""

    def __init__(self, settings: EnergySettings, readings=None):
        self._readings = []
        self.set_settings(settings)
        self.set_readings([] if readings is None else readings)

    def get_settings(self) -> EnergySettings:
        return self._settings

    def set_settings(self, settings: EnergySettings) -> None:
        if not isinstance(settings, EnergySettings):
            raise TypeError("Analytics settings must be an EnergySettings object.")
        self._validate_readings(self._readings, settings)
        self._settings = settings

    def get_readings(self) -> list[Reading]:
        # Return a new list so changing that list cannot add unchecked readings.
        return list(self._readings)

    def set_readings(self, readings: list[Reading]) -> None:
        self._validate_readings(readings, self._settings)
        self._readings = list(readings)

    def add_reading(self, reading: Reading) -> None:
        self.set_readings(self._readings + [reading])

    def totals(self) -> dict:
        if not self._readings:
            raise ValueError("No readings are available for calculation.")

        # Readings and settings are objects that can be updated through setters.
        # Recheck their relationships and intervals before calculating totals.
        self._validate_readings(self._readings, self._settings)
        energy = sum(
            (reading.get_energy_kwh() for reading in self._readings), Decimal("0")
        )

        return {
            "building_id": self._settings.get_building_id(),
            "reading_count": len(self._readings),
            "energy_kwh": energy,
            "estimated_cost_eur": energy * self._settings.get_tariff(),
            "estimated_co2_kg": energy * self._settings.get_carbon_factor(),
        }

    def _validate_readings(
        self, readings: list[Reading], settings: EnergySettings
    ) -> None:
        if not isinstance(readings, list):
            raise TypeError("Readings must be provided as a list.")

        known_meters = {}
        checked = []
        for reading in readings:
            if not isinstance(reading, Reading):
                raise TypeError("Every reading must be a Reading object.")
            meter = reading.get_meter()
            if meter.get_building() is not settings.get_building():
                raise ValueError("All readings must belong to the settings building.")

            meter_id = meter.get_meter_id()
            if meter_id in known_meters and known_meters[meter_id] is not meter:
                raise ValueError("Different meters must have different IDs.")
            known_meters[meter_id] = meter

            start, end = reading.get_interval()
            for previous in checked:
                if previous.get_meter_id() == meter_id:
                    previous_start, previous_end = previous.get_interval()
                    if start < previous_end and previous_start < end:
                        raise ValueError(
                            "Duplicate or overlapping intervals for the same meter."
                        )
            checked.append(reading)
