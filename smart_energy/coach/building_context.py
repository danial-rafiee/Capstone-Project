"""Building context model for Subsystem C."""
from typing import List, Optional


class BuildingContext:
    """Stores building context, occupied hours, and essential equipment for coaching."""

    def __init__(
        self,
        building_id: int,
        occupied_hours: Optional[str] = None,
        essential_loads: Optional[List[str]] = None,
    ):
        if not isinstance(building_id, int) or building_id <= 0:
            raise ValueError("Building ID must be a positive integer.")
        self._building_id = building_id
        self._occupied_hours = occupied_hours or "Mon-Fri 09:00-17:00"
        self._essential_loads = essential_loads or []

    def get_building_id(self) -> int:
        return self._building_id

    def get_occupied_hours(self) -> str:
        return self._occupied_hours

    def set_occupied_hours(self, hours: str) -> None:
        if not hours or not isinstance(hours, str):
            raise ValueError("Occupied hours must be a valid non-empty string.")
        self._occupied_hours = hours

    def get_essential_loads(self) -> List[str]:
        return list(self._essential_loads)

    def add_essential_load(self, load_name: str) -> None:
        if not load_name or not isinstance(load_name, str):
            raise ValueError("Load name must be a valid non-empty string.")
        self._essential_loads.append(load_name)