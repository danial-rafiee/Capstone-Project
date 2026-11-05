"""AI sustainability coach coordination service for Subsystem C."""
from decimal import Decimal
from typing import Dict

from .building_context import BuildingContext
from .score_calculator import ScoreCalculator


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