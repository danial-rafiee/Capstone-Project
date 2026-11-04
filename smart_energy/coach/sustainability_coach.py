from typing import List, Optional, Dict
from decimal import Decimal

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
        self._occupied_hours = occupied_hours or "Mon-Fri 08:00-18:00"
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
    ) -> Dict[str, Optional[Decimal]]:
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

        # Allowance A = allowance_share * R
        allowance = self._allowance_share * reference_energy

        # Growth Penalty Pg = min(50, max(0, 100 * (E - R) / R))
        growth_ratio = (current_energy - reference_energy) / reference_energy
        raw_pg = Decimal("100") * growth_ratio
        pg = min(Decimal("50"), max(Decimal("0"), raw_pg))

        # Off-hours Penalty Po = min(50, 100 * max(0, O - A) / E)
        excess_off = max(Decimal("0"), off_hours_energy - allowance)
        raw_po = Decimal("100") * (excess_off / current_energy)
        po = min(Decimal("50"), raw_po)

        # Final Score = max(0, 100 - Pg - Po)
        final_score = max(Decimal("0"), Decimal("100") - pg - po)

        return {
            "score": round(final_score, 1),
            "growth_penalty": round(pg, 1),
            "off_hours_penalty": round(po, 1),
            "status": "ready",
        }


class CoachService:
    """Coordinates score calculation and AI sustainability coaching."""

    def __init__(self, calculator: ScoreCalculator):
        self.set_calculator(calculator)
        self._last_status = "idle"

    def get_calculator(self) -> ScoreCalculator:
        return self._calculator

    def set_calculator(self, calculator: ScoreCalculator) -> None:
        if not isinstance(calculator, ScoreCalculator):
            raise TypeError("calculator must be a ScoreCalculator instance.")
        self._calculator = calculator

    def get_status(self) -> str:
        return self._last_status

    def assess_sustainability(
        self, current_e: Decimal, ref_e: Decimal, off_hours_e: Decimal
    ) -> dict:
        return self._calculator.calculate(current_e, ref_e, off_hours_e)

    def answer_question(
        self, question: str, context: BuildingContext, period_summary: dict
    ) -> Dict[str, str]:
        """Provides comfort-aware advice respecting occupied hours and essential loads."""
        if not question or not isinstance(question, str) or not question.strip():
            raise ValueError("Question cannot be empty.")
        if not isinstance(context, BuildingContext):
            raise TypeError("context must be a BuildingContext instance.")

        score_val = period_summary.get("score")
        score_text = f"{score_val}/100" if score_val is not None else "unavailable"

        essential_list = ", ".join(context.get_essential_loads()) or "None"
        advice = (
            f"Advice for selected period: Score is {score_text}. "
            f"Occupied hours ({context.get_occupied_hours()}) and essential equipment "
            f"({essential_list}) are strictly respected. Review non-essential off-hours consumption."
        )
        self._last_status = "ready"
        return {
            "answer": advice,
            "period": "Selected Period",
            "status": self._last_status,
        }