"""Building-specific factors for energy calculations and scoring input."""

from decimal import Decimal

from .building import Building


class EnergySettings:
    """Store the tariff, carbon factor and configurable off-hours allowance."""

    def __init__(
        self,
        building: Building,
        tariff: Decimal,
        carbon_factor: Decimal,
        off_hours_share: Decimal,
    ):
        self.set_building(building)
        self.configure(tariff, carbon_factor, off_hours_share)

    def configure(
        self, tariff: Decimal, carbon_factor: Decimal, off_hours_share: Decimal
    ) -> None:
        """Validate a complete configuration before replacing any factors."""
        self._validate_factor(tariff, "Tariff")
        self._validate_factor(carbon_factor, "Carbon factor")
        self._validate_share(off_hours_share)

        self._tariff = tariff
        self._carbon_factor = carbon_factor
        self._off_hours_share = off_hours_share

    def get_building(self) -> Building:
        return self._building

    def set_building(self, building: Building) -> None:
        if not isinstance(building, Building):
            raise TypeError("Energy settings must belong to a Building object.")
        self._building = building

    def get_building_id(self) -> int:
        return self._building.get_building_id()

    def get_tariff(self) -> Decimal:
        return self._tariff

    def set_tariff(self, tariff: Decimal) -> None:
        self._validate_factor(tariff, "Tariff")
        self._tariff = tariff

    def get_carbon_factor(self) -> Decimal:
        return self._carbon_factor

    def set_carbon_factor(self, carbon_factor: Decimal) -> None:
        self._validate_factor(carbon_factor, "Carbon factor")
        self._carbon_factor = carbon_factor

    def get_off_hours_share(self) -> Decimal:
        return self._off_hours_share

    def set_off_hours_share(self, off_hours_share: Decimal) -> None:
        self._validate_share(off_hours_share)
        self._off_hours_share = off_hours_share

    def _validate_factor(self, value: Decimal, label: str) -> None:
        if not isinstance(value, Decimal):
            raise TypeError(f"{label} must be a Decimal value.")
        if not value.is_finite() or value < 0:
            raise ValueError(f"{label} must be finite and non-negative.")

    def _validate_share(self, off_hours_share: Decimal) -> None:
        self._validate_factor(off_hours_share, "Off-hours allowance share")
        if off_hours_share > 1:
            raise ValueError("Off-hours allowance share must be between 0 and 1.")
