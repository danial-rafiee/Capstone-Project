"""Save and retrieve meters belonging to a building."""

from contextlib import closing

from .building import Building
from .database import Database
from .meter import Meter


class MeterRepository:
    def __init__(self, database: Database):
        if not isinstance(database, Database):
            raise TypeError("Database must be a Database object.")

        self._database = database

    def save(self, meter: Meter) -> None:
        """Insert a meter, or update its building and name."""
        if not isinstance(meter, Meter):
            raise TypeError("Meter must be a Meter object.")

        sql = """
            INSERT INTO meters (meter_id, building_id, name)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE
                building_id = %s,
                name = %s
        """

        values = (
            meter.get_meter_id(),
            meter.get_building_id(),
            meter.get_name(),
            meter.get_building_id(),
            meter.get_name(),
        )

        with closing(self._database.connect()) as connection:
            with closing(connection.cursor()) as cursor:
                cursor.execute(sql, values)

            connection.commit()

    def get_by_id(
        self, meter_id: int, building: Building
    ) -> Meter | None:
        if isinstance(meter_id, bool) or not isinstance(meter_id, int):
            raise TypeError("Meter ID must be an integer.")
        if meter_id <= 0:
            raise ValueError("Meter ID must be positive.")
        if not isinstance(building, Building):
            raise TypeError("Building must be a Building object.")

        sql = """
            SELECT meter_id, name
            FROM meters
            WHERE meter_id = %s AND building_id = %s
        """

        with closing(self._database.connect()) as connection:
            with closing(connection.cursor()) as cursor:
                cursor.execute(
                    sql, (meter_id, building.get_building_id())
                )
                row = cursor.fetchone()

        if row is None:
            return None

        return Meter(
            meter_id=row[0],
            building=building,
            name=row[1],
        )