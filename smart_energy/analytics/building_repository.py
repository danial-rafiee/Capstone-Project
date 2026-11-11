"""Save and retrieve Building objects using MySQL."""

from contextlib import closing

from .building import Building
from .database import Database


class BuildingRepository:
    def __init__(self, database: Database):
        if not isinstance(database, Database):
            raise TypeError("Database must be a Database object.")

        self._database = database

    def save(self, building: Building) -> None:
        """Insert a building, or update its name if its ID exists."""
        if not isinstance(building, Building):
            raise TypeError("Building must be a Building object.")

        sql = """
            INSERT INTO buildings (building_id, name)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE name = %s
        """

        values = (
            building.get_building_id(),
            building.get_name(),
            building.get_name(),
        )

        with closing(self._database.connect()) as connection:
            with closing(connection.cursor()) as cursor:
                cursor.execute(sql, values)

            connection.commit()

    def get_by_id(self, building_id: int) -> Building | None:
        if isinstance(building_id, bool) or not isinstance(building_id, int):
            raise TypeError("Building ID must be an integer.")
        if building_id <= 0:
            raise ValueError("Building ID must be positive.")

        sql = """
            SELECT building_id, name
            FROM buildings
            WHERE building_id = %s
        """

        with closing(self._database.connect()) as connection:
            with closing(connection.cursor()) as cursor:
                cursor.execute(sql, (building_id,))
                row = cursor.fetchone()

        if row is None:
            return None

        return Building(building_id=row[0], name=row[1])