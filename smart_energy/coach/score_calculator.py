"""Sustainability score and penalty calculator for Subsystem C."""
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Optional, Any, Union

try:
    from smart_energy.coach.exceptions import InvalidEvaluationDataError
except ImportError:
    # Fallback to ValueError if exceptions module is not in path
    class InvalidEvaluationDataError(ValueError):
        pass


class ScoreCalculator:
    """
    Python-based sustainability score and penalty calculation.
    Formula:
      A = allowance_share * R
      Pg = min(50, max(0, 100 * (E - R) / R))
      Po = min(50, 100 * max(0, O - A) / E)
      Score = max(0, 100 - Pg - Po)
    """

    def __init__(self, allowance_share: Union[Decimal, float] = Decimal("0.20")):
        self._allowance_share = Decimal("0.20")
        self.set_allowance_share(allowance_share)

    def get_allowance_share(self) -> Decimal:
        return self._allowance_share

    def set_allowance_share(self, share: Union[Decimal, float]) -> None:
        try:
            val = Decimal(str(share))
        except Exception:
            raise InvalidEvaluationDataError("Allowance share must be a valid numeric Decimal.")

        if not (Decimal("0.0") <= val <= Decimal("1.0")):
            raise InvalidEvaluationDataError("Allowance share must be between 0.0 and 1.0.")
        self._allowance_share = val

    def calculate(
        self,
        current_energy: Optional[Union[Decimal, float]],
        reference_energy: Optional[Union[Decimal, float]],
        off_hours_energy: Optional[Union[Decimal, float]],
    ) -> Dict[str, Any]:
        """Calculates score and breakdown penalties."""
        if current_energy is None or reference_energy is None or off_hours_energy is None:
            return {
                "score": None,
                "growth_penalty": None,
                "off_hours_penalty": None,
                "status": "unavailable",
            }

        try:
            e = Decimal(str(current_energy))
            r = Decimal(str(reference_energy))
            o = Decimal(str(off_hours_energy))
        except Exception:
            return {
                "score": None,
                "growth_penalty": None,
                "off_hours_penalty": None,
                "status": "unavailable",
            }

        # Guard against zero/negative bases
        if e <= Decimal("0") or r <= Decimal("0") or o < Decimal("0"):
            return {
                "score": None,
                "growth_penalty": None,
                "off_hours_penalty": None,
                "status": "unavailable",
            }

        allowance = self._allowance_share * r

        growth_ratio = (e - r) / r
        raw_pg = Decimal("100") * growth_ratio
        pg = min(Decimal("50"), max(Decimal("0"), raw_pg))

        excess_off = max(Decimal("0"), o - allowance)
        raw_po = Decimal("100") * (excess_off / e)
        po = min(Decimal("50"), raw_po)

        final_score = max(Decimal("0"), Decimal("100") - pg - po)

        return {
            "score": float(final_score.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)),
            "growth_penalty": float(pg.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)),
            "off_hours_penalty": float(po.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)),
            "status": "ready",
        }


def evaluate_period(data: dict) -> dict:
    """Consolidated backend evaluator for Subsystem A.

    Accepts either:
      1. A full comparison payload from service.compare(...) containing 'score_inputs'
      2. A period summary dictionary from service.summarize(...)
    """
    if not isinstance(data, dict):
        return {"score": None, "status": "unavailable"}

    # Case 1: Standard comparison payload from service.compare
    if "score_inputs" in data:
        status = data.get("score_inputs_status", "unavailable")
        if status != "ready":
            return {"score": None, "status": status}
        inputs = data.get("score_inputs") or {}
        calc = ScoreCalculator()
        return calc.calculate(
            current_energy=inputs.get("current_energy"),
            reference_energy=inputs.get("reference_energy"),
            off_hours_energy=inputs.get("off_hours_energy"),
        )

    # Case 2: Direct summary payload from service.summarize
    current_e = data.get("energy_kwh")
    off_hours_e = data.get("off_hours_energy_kwh", Decimal("0.0"))
    ref_e = data.get("reference_energy_kwh") or data.get("reference_energy")

    if current_e is not None and ref_e is not None:
        calc = ScoreCalculator()
        return calc.calculate(
            current_energy=current_e,
            reference_energy=ref_e,
            off_hours_energy=off_hours_e,
        )

    return {"score": None, "status": "unavailable"}