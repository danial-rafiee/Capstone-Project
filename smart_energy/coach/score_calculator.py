"""Sustainability score and penalty calculator for Subsystem C."""
from decimal import Decimal
from typing import Any, Dict, Optional


class ScoreCalculator:
    """
    Python-based sustainability score and penalty calculation.
    Formula:
      A = allowance_share * R
      Pg = min(50, max(0, 100 * (E - R) / R))
      Po = min(50, 100 * max(0, O - A) / E)
      Score = max(0, 100 - Pg - Po)
    """

    def __init__(self, allowance_share: Decimal = Decimal("0.10")):
        self.set_allowance_share(allowance_share)

    def get_allowance_share(self) -> Decimal:
        return self._allowance_share

    def set_allowance_share(self, share: Decimal) -> None:
        if not isinstance(share, Decimal):
            raise TypeError("Allowance share must be a Decimal.")
        if not (Decimal("0.0") <= share <= Decimal("1.0")):
            raise ValueError("Allowance share must be between 0.0 and 1.0.")
        self._allowance_share = share

    def calculate(
        self,
        current_energy: Optional[Decimal],
        reference_energy: Optional[Decimal],
        off_hours_energy: Optional[Decimal],
    ) -> Dict[str, Any]:
        """Calculates score and breakdown penalties."""
        if (
            current_energy is None
            or reference_energy is None
            or off_hours_energy is None
            or current_energy <= Decimal("0")
            or reference_energy <= Decimal("0")
            or off_hours_energy < Decimal("0")
        ):
            return {
                "score": None,
                "growth_penalty": None,
                "off_hours_penalty": None,
                "status": "unavailable",
            }

        allowance = self.get_allowance_share() * reference_energy

        growth_ratio = (current_energy - reference_energy) / reference_energy
        raw_pg = Decimal("100") * growth_ratio
        pg = min(Decimal("50"), max(Decimal("0"), raw_pg))

        excess_off = max(Decimal("0"), off_hours_energy - allowance)
        raw_po = Decimal("100") * (excess_off / current_energy)
        po = min(Decimal("50"), raw_po)

        final_score = max(Decimal("0"), Decimal("100") - pg - po)

        return {
            "score": round(final_score, 1),
            "growth_penalty": round(pg, 1),
            "off_hours_penalty": round(po, 1),
            "status": "ready",
        }
