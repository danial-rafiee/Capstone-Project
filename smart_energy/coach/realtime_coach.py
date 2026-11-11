"""
Real-time stream filters, score transformers, and AI coach alert stages.
Adheres to the uniform BaseStreamProcessor contract.
"""
from decimal import Decimal
from typing import Optional
from smart_energy.coach.stream_pipeline import BaseStreamProcessor
from smart_energy.streaming.source.meter_event import MeterEvent


class InactiveMeterFilter(BaseStreamProcessor):
    """Filters out inactive meters or readings below threshold power."""

    def __init__(self, min_threshold_kw: Decimal = Decimal("0.5")):
        self.min_threshold_kw = min_threshold_kw

    def process(self, event: MeterEvent) -> Optional[MeterEvent]:
        if not event.active:
            return None
        if event.power_kw <= self.min_threshold_kw:
            return None
        return event


class RealTimeScoreTransformer(BaseStreamProcessor):
    """
    Transforms raw power readings into dynamic penalties and sustainability score.
    """

    def __init__(self, reference_kw: Decimal = Decimal("5.0"), allowance_share: Decimal = Decimal("0.10")):
        self.reference_kw = reference_kw
        self.allowance_share = allowance_share

    def process(self, event: MeterEvent) -> Optional[dict]:
        power = event.power_kw
        is_off_hours = event.timestamp.hour < 8 or event.timestamp.hour >= 18

        # Growth Penalty (Pg)
        if power > self.reference_kw:
            growth_pct = ((power - self.reference_kw) / self.reference_kw) * Decimal("100")
            pg = min(Decimal("50"), max(Decimal("0"), growth_pct))
        else:
            pg = Decimal("0")

        # Off-hours Penalty (Po)
        po = Decimal("0")
        if is_off_hours:
            allowance = self.allowance_share * self.reference_kw
            if power > allowance:
                excess_ratio = (power - allowance) / power
                po = min(Decimal("50"), Decimal("100") * excess_ratio)

        realtime_score = max(Decimal("0"), Decimal("100") - pg - po)

        return {
            "meter_id": event.meter_id,
            "timestamp": event.timestamp.isoformat(),
            "power_kw": float(power),
            "is_off_hours": is_off_hours,
            "growth_penalty": float(round(pg, 2)),
            "off_hours_penalty": float(round(po, 2)),
            "sustainability_score": float(round(realtime_score, 2)),
        }


class RealTimeCoachAlerter(BaseStreamProcessor):
    """Generates instant AI coach intervention alerts based on score drop."""

    def __init__(self, score_warning_threshold: float = 75.0):
        self.threshold = score_warning_threshold

    def process(self, event_data: dict) -> Optional[dict]:
        if not isinstance(event_data, dict):
            return None

        result = dict(event_data)
        score = result.get("sustainability_score", 100.0)

        if score < self.threshold:
            reasons = []
            if result.get("off_hours_penalty", 0) > 0:
                reasons.append("off-hours energy leakage")
            if result.get("growth_penalty", 0) > 0:
                reasons.append("peak capacity overload")
            cause = " and ".join(reasons) if reasons else "high consumption"
            result["coach_alert"] = f"CRITICAL: Score {score}/100. Prompt alert: {cause} detected."
        else:
            result["coach_alert"] = f"OPTIMAL: Score {score}/100. Building operates efficiently."

        return result