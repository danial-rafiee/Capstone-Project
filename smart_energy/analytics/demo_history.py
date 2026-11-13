"""Gap-only simulated history for an existing demo meter; never replace readings."""

from contextlib import closing
from datetime import timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from hashlib import sha256
from zoneinfo import ZoneInfo

from .building import Building
from .energy_settings import EnergySettings
from .errors import AnalyticsError
from .meter import Meter
from .operating_schedule import OperatingSchedule
from .period_analytics import PeriodAnalyticsService
from .reading import Reading
from .time_window import TimeWindow, duration_seconds


class DemoHistoryGenerator:
    """Deterministic office-like simulation in UTC hours and local business hours.

    This is synthetic data, not measured usage or an actual energy forecast.
    Existing measurements are preserved exactly, including partial-hour rows.
    """

    def __init__(self, timezone_name="Europe/Berlin", seed="group18-demo-v1"):
        self.schedule = OperatingSchedule(timezone_name, {
            day: [("09:00", "17:00")] for day in range(5)})
        self.seed = str(seed)

    def plan(self, meter, existing, window):
        # Validate the original data before filling gaps; never hide overlaps.
        service = PeriodAnalyticsService(EnergySettings(
            meter.get_building(), Decimal(".30"), Decimal(".40"), Decimal(".10")),
            self.schedule)
        summary = service.summarize(meter, existing, window)
        additions = []
        for gap in summary["gaps"]:
            cursor = gap["start"]
            while cursor < gap["end"]:
                hour = cursor.replace(minute=0, second=0, microsecond=0)
                end = min(gap["end"], hour + timedelta(hours=1))
                occupied = self.schedule.occupied_seconds(TimeWindow(cursor, end))
                seconds = duration_seconds(cursor, end)
                # Stable per-meter, per-hour variation; no dependency on run date.
                digest = sha256(f"{self.seed}:{meter.get_meter_id()}:{hour.isoformat()}".encode()).digest()
                variation = Decimal(85 + int.from_bytes(digest[:2], "big") % 31) / 100
                # Slow deterministic variation allows non-identical reference totals.
                cycle = Decimal(90 + hour.date().toordinal() % 21) / 100
                kwh = ((Decimal(".7") * seconds + Decimal("3.3") * occupied)
                       / Decimal(3600) * variation * cycle)
                additions.append(Reading(meter, cursor, end,
                    kwh.quantize(Decimal(".000001"), rounding=ROUND_HALF_UP)))
                cursor = end
        return additions


class DemoHistorySeeder:
    """Preview or atomically append missing rows for a single existing meter.

    Apply takes the same parent-meter lock as ReadingRepository.add. This
    serializes cooperating writers; direct SQL writers must also respect it.
    No tables, buildings, meters or existing readings are created/modified here.
    """

    def __init__(self, database, generator=None):
        self.database = database
        self.generator = generator if generator is not None else DemoHistoryGenerator()

    def run(self, building_id, meter_id, window, *, apply=False):
        for value in (building_id, meter_id):
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError("Building and meter IDs must be positive integers.")
        if not isinstance(window, TimeWindow) or window.seconds < Decimal(60 * 86400):
            raise ValueError("A window of at least 60 elapsed days is required.")
        with closing(self.database.connect()) as connection:
            try:
                with closing(connection.cursor()) as cursor:
                    cursor.execute(
                        "SELECT building_id, name FROM meters WHERE meter_id = %s"
                        + (" FOR UPDATE" if apply else ""), (meter_id,))
                    row = cursor.fetchone()
                    if row is None or row[0] != building_id:
                        raise AnalyticsError("Demo meter not found in this building.",
                                             "meter_not_found")
                    meter_name = row[1]
                    cursor.execute("SELECT name FROM buildings WHERE building_id = %s", (building_id,))
                    building_row = cursor.fetchone()
                    if building_row is None:
                        raise AnalyticsError("Demo building not found.", "building_not_found")
                    building = Building(building_id, building_row[0])
                    meter = Meter(meter_id, building, meter_name)
                    cursor.execute(
                        "SELECT start_utc, end_utc, energy_kwh FROM readings "
                        "WHERE meter_id = %s AND start_utc < %s AND end_utc > %s "
                        "ORDER BY start_utc, reading_id",
                        (meter_id, window.end.replace(tzinfo=None), window.start.replace(tzinfo=None)))
                    existing = [Reading(meter, start.replace(tzinfo=timezone.utc),
                                        end.replace(tzinfo=timezone.utc), energy)
                                for start, end, energy in cursor.fetchall()]
                    additions = self.generator.plan(meter, existing, window)
                    analytics = PeriodAnalyticsService(EnergySettings(
                        building, Decimal(".30"), Decimal(".40"), Decimal(".10")),
                        self.generator.schedule)
                    before = analytics.summarize(meter, existing, window)
                    combined = existing + additions
                    after = analytics.summarize(meter, combined, window)
                    comparisons = {}
                    for days in (1, 7, 30):
                        current = TimeWindow(window.end - timedelta(days=days), window.end)
                        reference = TimeWindow(current.start - timedelta(days=days), current.start)
                        report = analytics.compare(meter, combined, combined, current, reference)
                        comparisons[str(days)] = {
                            "current_status": report["current"]["status"],
                            "reference_status": report["reference"]["status"],
                            "current_coverage_fraction": report["current"]["coverage_fraction"],
                            "reference_coverage_fraction": report["reference"]["coverage_fraction"],
                            "comparison": report["comparison"],
                            "score_inputs_status": report["score_inputs_status"],
                        }
                    if after["status"] != "complete" or any(
                            item["comparison"]["status"] != "ready" for item in comparisons.values()):
                        raise RuntimeError("Planned history must cover all current/reference periods.")
                    if apply and additions:
                        cursor.executemany(
                            "INSERT INTO readings (meter_id, start_utc, end_utc, energy_kwh) "
                            "VALUES (%s, %s, %s, %s)",
                            [(meter_id, reading.get_interval()[0].replace(tzinfo=None),
                              reading.get_interval()[1].replace(tzinfo=None), reading.get_energy_kwh())
                             for reading in additions])
                if apply:
                    connection.commit()
                else:
                    connection.rollback()  # End the read-only preview transaction.
                zone = ZoneInfo(self.generator.schedule.get_timezone())
                latest = after["series"][-1]
                return {
                    "mode": "applied" if apply else "preview_no_writes",
                    "data_kind": "SIMULATED gap-fill; existing readings preserved",
                    "building_id": building_id, "meter_id": meter_id,
                    "start": window.start, "end": window.end,
                    "timezone": self.generator.schedule.get_timezone(),
                    "seed": self.generator.seed,
                    "existing_readings_in_window": len(existing),
                    "proposed_new_readings": len(additions),
                    "inserted_readings": len(additions) if apply else 0,
                    "coverage_before": before["coverage_fraction"],
                    "coverage_after" if apply else "projected_coverage": after["coverage_fraction"],
                    "comparisons_after" if apply else "projected_comparisons": comparisons,
                    "dashboard_end_utc": window.end,
                    "dashboard_start_local": window.start.astimezone(zone).isoformat(),
                    "dashboard_end_local": window.end.astimezone(zone).isoformat(),
                    "latest_interval_in_window": {
                        "start_utc": latest["start"], "end_utc": latest["end"],
                        "start_local": latest["start"].astimezone(zone).isoformat(),
                        "end_local": latest["end"].astimezone(zone).isoformat(),
                        "energy_kwh": latest["energy_kwh"],
                    },
                }
            except Exception:
                connection.rollback()
                raise
