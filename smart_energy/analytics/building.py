"""A building with validated identity and name."""


class Building:
    """Store building information through explicit getters and setters."""

    def __init__(self, building_id: int, name: str):
        self.set_building_id(building_id)
        self.set_name(name)

    def get_building_id(self) -> int:
        return self._building_id

    def set_building_id(self, building_id: int) -> None:
        if isinstance(building_id, bool) or not isinstance(building_id, int):
            raise TypeError("Building ID must be an integer.")
        if building_id <= 0:
            raise ValueError("Building ID must be greater than zero.")
        self._building_id = building_id

    def get_name(self) -> str:
        return self._name

    def set_name(self, name: str) -> None:
        if not isinstance(name, str):
            raise TypeError("Building name must be text.")
        name = name.strip()
        if not name:
            raise ValueError("Building name must not be empty.")
        self._name = name
