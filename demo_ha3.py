"""Store energy readings in MySQL and calculate their totals."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from smart_energy.analytics.building import Building
from smart_energy.analytics.meter import Meter
from smart_energy.analytics.reading import Reading
from smart_energy.analytics.energy_settings import EnergySettings
from smart_energy.analytics.analytics_service import AnalyticsService

from smart_energy.analytics.database import Database
from smart_energy.analytics.building_repository import BuildingRepository
from smart_energy.analytics.meter_repository import MeterRepository
from smart_energy.analytics.reading_repository import ReadingRepository


def main():
    database = Database()

    building_repository = BuildingRepository(database)
    meter_repository = MeterRepository(database)
    reading_repository = ReadingRepository(database)

    # 1. Save and retrieve the building.
    building_repository.save(Building(1, "Demo Office"))

    building = building_repository.get_by_id(1)
    if building is None:
        raise RuntimeError("Building could not be retrieved.")

    print("Building:", building.get_name())

    # 2. Save and retrieve its meter.
    meter_repository.save(Meter(101, building, "Main Meter"))

    meter = meter_repository.get_by_id(101, building)
    if meter is None:
        raise RuntimeError("Meter could not be retrieved.")

    print("Meter:", meter.get_name())

    # 3. Prepare two illustrative, adjacent readings.
    start = datetime(2026, 11, 4, 9, 0, tzinfo=timezone.utc)
    middle = start + timedelta(minutes=5)
    end = middle + timedelta(minutes=5)

    samples = [
        Reading(meter, start, middle, Decimal("3.0")),
        Reading(meter, middle, end, Decimal("2.0")),
    ]

    # Allow rerunning the demo without inserting duplicate samples.
    existing = {
        reading.get_interval(): reading
        for reading in reading_repository.list_for_meter(meter)
    }

    for sample in samples:
        stored = existing.get(sample.get_interval())

        if stored is None:
            reading_repository.add(sample)
        elif stored.get_energy_kwh() != sample.get_energy_kwh():
            raise ValueError(
                "An existing demo interval has different energy. "
                "No stored value was overwritten."
            )

    # 4. Read the saved samples back from MySQL.
    sample_intervals = {
        sample.get_interval() for sample in samples
    }

    loaded_readings = [
        reading
        for reading in reading_repository.list_for_meter(meter)
        if reading.get_interval() in sample_intervals
    ]

    # 5. Calculate using retrieved readings and sample factors.
    settings = EnergySettings(
        building=building,
        tariff=Decimal("0.30"),
        carbon_factor=Decimal("0.40"),
        off_hours_share=Decimal("0.10"),
    )

    analytics = AnalyticsService(settings, loaded_readings)
    totals = analytics.totals()

    print("\nAnalytics from MySQL readings")
    print("Demo reading count:", totals["reading_count"])
    print("Total energy:", f'{totals["energy_kwh"]:.1f}', "kWh")
    print(
        "Estimated cost:",
        f'{totals["estimated_cost_eur"]:.2f}',
        "EUR",
    )
    print(
        "Estimated CO2:",
        f'{totals["estimated_co2_kg"]:.2f}',
        "kg",
    )

    # 6. Verify that a duplicate reading is rejected.
    try:
        reading_repository.add(samples[0])
    except ValueError as error:
        print("\nDuplicate rejected:", error)
    else:
        raise RuntimeError("A duplicate reading was unexpectedly accepted.")


if __name__ == "__main__":
    main()