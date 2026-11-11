"""Store and retrieve interval energy readings in MySQL."""

from contextlib import closing
from datetime import timezone
from decimal import Decimal

from .database import Database
from .meter import Meter
from .reading import Reading
from .time_window import TimeWindow


class ReadingRepository:
    def __init__(self, database: Database):
        if not isinstance(database, Database):
            raise TypeError("Database must be a Database object.")

        self._database = database

    def add(self, reading: Reading) -> None:
        """Insert a new reading, rejecting duplicate or overlapping intervals."""
        if not isinstance(reading, Reading):
            raise TypeError("Reading must be a Reading object.")

        energy = reading.get_energy_kwh()

        # Match the precision of DECIMAL(18,6) without silent rounding.
        if energy > Decimal("999999999999.999999"):
            raise ValueError("Energy exceeds the database storage limit.")
        if energy != energy.quantize(Decimal("0.000001")):
            raise ValueError("Energy must have at most six decimal places.")

        start, end = reading.get_interval()

        # DATETIME stores no timezone: write UTC without timezone metadata.
        start_utc = start.astimezone(timezone.utc).replace(tzinfo=None)
        end_utc = end.astimezone(timezone.utc).replace(tzinfo=None)
        meter = reading.get_meter()

        with closing(self._database.connect()) as connection:
            try:
                with closing(connection.cursor()) as cursor:
                    # Serialize inserts made through this repository per meter.
                    cursor.execute(
                        """
                        SELECT building_id
                        FROM meters
                        WHERE meter_id = %s
                        FOR UPDATE
                        """,
                        (meter.get_meter_id(),),
                    )
                    row = cursor.fetchone()

                    if row is None:
                        raise ValueError("Save the meter before its readings.")
                    if row[0] != meter.get_building_id():
                        raise ValueError("Meter building does not match MySQL.")

                    cursor.execute(
                        """
                        SELECT reading_id
                        FROM readings
                        WHERE meter_id = %s
                          AND start_utc < %s
                          AND end_utc > %s
                        LIMIT 1
                        """,
                        (meter.get_meter_id(), end_utc, start_utc),
                    )

                    if cursor.fetchone() is not None:
                        raise ValueError(
                            "Duplicate or overlapping interval for this meter."
                        )

                    cursor.execute(
                        """
                        INSERT INTO readings (
                            meter_id, start_utc, end_utc, energy_kwh
                        )
                        VALUES (%s, %s, %s, %s)
                        """,
                        (
                            meter.get_meter_id(),
                            start_utc,
                            end_utc,
                            energy,
                        ),
                    )

                connection.commit()

            except Exception:
                connection.rollback()
                raise

    def list_for_meter(self, meter: Meter) -> list[Reading]:
        if not isinstance(meter, Meter):
            raise TypeError("Meter must be a Meter object.")

        with closing(self._database.connect()) as connection:
            with closing(connection.cursor()) as cursor:
                cursor.execute(
                    """
                    SELECT start_utc, end_utc, energy_kwh
                    FROM readings
                    WHERE meter_id = %s
                    ORDER BY start_utc, reading_id
                    """,
                    (meter.get_meter_id(),),
                )
                rows = cursor.fetchall()

        return [
            Reading(
                meter=meter,
                start=row[0].replace(tzinfo=timezone.utc),
                end=row[1].replace(tzinfo=timezone.utc),
                energy_kwh=row[2],
            )
            for row in rows
        ]

    def list_for_period(self, meter: Meter, start, end) -> list[Reading]:
        """Load intervals overlapping [start, end); preserve full measurements.

        PeriodAnalyticsService handles clipping/coverage. This method neither
        sums out-of-window energy nor mutates the stored measurement intervals.
        """
        if not isinstance(meter, Meter):
            raise TypeError("Meter must be a Meter object.")
        window = TimeWindow(start, end)
        with closing(self._database.connect()) as connection:
            with closing(connection.cursor()) as cursor:
                cursor.execute(
                    """
                    SELECT start_utc, end_utc, energy_kwh
                    FROM readings
                    WHERE meter_id = %s AND start_utc < %s AND end_utc > %s
                    ORDER BY start_utc, reading_id
                    """,
                    (meter.get_meter_id(), window.end.replace(tzinfo=None),
                     window.start.replace(tzinfo=None)),
                )
                rows = cursor.fetchall()
        return [Reading(meter, row[0].replace(tzinfo=timezone.utc),
                        row[1].replace(tzinfo=timezone.utc), row[2]) for row in rows]
