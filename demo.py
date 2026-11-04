
"""Run the current Smart Energy example with: python3 demo.py"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from smart_energy.analytics import (
    Building,
    Meter,
    Reading,
    EnergySettings,
    AnalyticsService,
)


def main():
    office = Building(1, "Demo Office")
    meter = Meter(101, office, "Main Meter")

    print("Meter ID:", meter.get_meter_id())
    print("Meter name:", meter.get_name())
    print("Connected building ID:", meter.get_building_id())
    print("Connected building name:", meter.get_building().get_name())

    meter.set_name("First Floor Meter")
    print("Updated meter name:", meter.get_name())

    try:
        meter.set_building("Demo Office")
    except TypeError as error:
        print("Invalid connection rejected:", error)

    print("Building after rejected update:", meter.get_building().get_name())

    # Illustrative interval data; these are not real meter measurements.
    start = datetime(2026, 11, 4, 9, 0, tzinfo=timezone.utc)
    end = datetime(2026, 11, 4, 9, 5, tzinfo=timezone.utc)
    reading = Reading(meter, start, end, Decimal("2.5"))

    print("\nEnergy reading")
    print("Reading meter ID:", reading.get_meter_id())
    interval_start, interval_end = reading.get_interval()
    print("Start:", interval_start.isoformat())
    print("End:", interval_end.isoformat())
    print("Energy:", reading.get_energy_kwh(), "kWh")

    reading.set_energy_kwh(Decimal("3.0"))
    print("Updated energy:", reading.get_energy_kwh(), "kWh")

    try:
        reading.set_energy_kwh(Decimal("-1"))
    except ValueError as error:
        print("Invalid energy rejected:", error)

    print("Energy after rejected update:", reading.get_energy_kwh(), "kWh")

    # Illustrative factors from the capstone example, not live market values.
    settings = EnergySettings(
        office, Decimal("0.30"), Decimal("0.40"), Decimal("0.10")
    )

    print("\nEnergy settings")
    print("Settings building ID:", settings.get_building_id())
    print("Tariff:", settings.get_tariff(), "EUR/kWh")
    print("Carbon factor:", settings.get_carbon_factor(), "kg CO2/kWh")
    print("Off-hours allowance share:", settings.get_off_hours_share())

    try:
        settings.configure(Decimal("0.35"), Decimal("-0.40"), Decimal("0.10"))
    except ValueError as error:
        print("Invalid settings rejected:", error)

    print("Tariff after rejected configuration:", settings.get_tariff(), "EUR/kWh")

    next_reading = Reading(
        meter, end, end + timedelta(minutes=5), Decimal("2.0")
    )
    analytics = AnalyticsService(settings)
    analytics.add_reading(reading)
    analytics.add_reading(next_reading)
    results = analytics.totals()

    print("\nEnergy analytics")
    print("Reading count:", results["reading_count"])
    print("Total energy:", results["energy_kwh"], "kWh")
    print("Estimated cost:", f'{results["estimated_cost_eur"]:.2f}', "EUR")
    print("Estimated CO2:", f'{results["estimated_co2_kg"]:.2f}', "kg")

    try:
        analytics.add_reading(reading)
    except ValueError as error:
        print("Duplicate reading rejected:", error)

    print("Reading count after rejection:", len(analytics.get_readings()))


if __name__ == "__main__":
    main()
