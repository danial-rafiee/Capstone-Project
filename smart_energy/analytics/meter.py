"""An energy meter associated with a building."""

from .building import Building


class Meter:
    """Store meter information and its connection to a Building object."""

    def __init__(self, meter_id: int, building: Building, name: str):
        self.set_meter_id(meter_id)
        self.set_building(building)
        self.set_name(name)

    def get_meter_id(self) -> int:
        return self._meter_id

    def set_meter_id(self, meter_id: int) -> None:
        if isinstance(meter_id, bool) or not isinstance(meter_id, int):
            raise TypeError("Meter ID must be an integer.")
        if meter_id <= 0:
            raise ValueError("Meter ID must be greater than zero.")
        self._meter_id = meter_id

    def get_building(self) -> Building:
        return self._building

    def set_building(self, building: Building) -> None:
        if not isinstance(building, Building):
            raise TypeError("Meter must be connected to a Building object.")
        self._building = building

    def get_building_id(self) -> int:
        return self._building.get_building_id()

    def get_name(self) -> str:
        return self._name

    def set_name(self, name: str) -> None:
        if not isinstance(name, str):
            raise TypeError("Meter name must be text.")
        name = name.strip()
        if not name:
            raise ValueError("Meter name must not be empty.")
        self._name = name
