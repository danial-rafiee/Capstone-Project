"""Subsystem C Core Coaching Service.

Integrates Python-based sustainability scoring with OpenAI interactive coaching
and robust rule-based fallback capabilities.
Complies with FR-C1..FR-C10 and NFR-C1..NFR-C10 (asl.pdf).
"""

import os
import logging
from typing import Optional, Dict, Any, Union
from decimal import Decimal

from smart_energy.coach.building_context import BuildingContext
from smart_energy.coach.score_calculator import ScoreCalculator
from smart_energy.coach.coach_models import CoachRequest, CoachResponse
from smart_energy.coach.exceptions import CoachError

logger = logging.getLogger(__name__)

# Optional OpenAI import for production resilience
try:
    from openai import OpenAI

    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


class CoachService:
    """Manages sustainability assessments and AI-driven interactive advice."""

    def __init__(
            self,
            calculator: ScoreCalculator,
            api_key: Optional[str] = None,
            model_name: str = "gpt-4o-mini"
    ):
        if not isinstance(calculator, ScoreCalculator):
            raise TypeError("calculator must be an instance of ScoreCalculator.")

        self._calculator = calculator
        self._last_status = "ready"
        self._model_name = model_name

        # Read API key securely from argument or environment (NFR-C1)
        self._api_key = api_key or os.getenv("OPENAI_API_KEY")
        self._client = None
        if HAS_OPENAI and self._api_key:
            try:
                self._client = OpenAI(api_key=self._api_key)
            except Exception as exc:
                logger.warning(f"Failed to initialize OpenAI client: {exc}")
                self._client = None

    def get_calculator(self) -> ScoreCalculator:
        """Returns the assigned ScoreCalculator instance."""
        return self._calculator

    def set_calculator(self, calculator: ScoreCalculator) -> None:
        """Assigns a new ScoreCalculator instance."""
        if not isinstance(calculator, ScoreCalculator):
            raise TypeError("calculator must be an instance of ScoreCalculator.")
        self._calculator = calculator

    def get_status(self) -> str:
        """Returns the status of the last coaching operation."""
        return self._last_status

    def assess_sustainability(
            self,
            current_energy: Union[Decimal, float],
            reference_energy: Union[Decimal, float],
            off_hours_energy: Union[Decimal, float]
    ) -> Dict[str, Any]:
        """Calculates sustainability score and penalties independently in Python (FR-C2)."""
        evaluation = self._calculator.calculate(current_energy, reference_energy, off_hours_energy)
        self._last_status = evaluation.get("status", "error")
        return evaluation

    def _build_contextual_fallback(
            self,
            question: str,
            period_label: str,
            score: Any,
            growth_p: float,
            off_hours_p: float,
            occupied_hours: str,
            essential_str: str
    ) -> str:
        """Generates intent-aware deterministic advice when OpenAI API is not configured."""
        q_lower = question.lower()
        score_text = f"{score}/100" if score is not None else "unavailable (insufficient period data)"

        if any(word in q_lower for word in ["off-hour", "night", "weekend", "after work", "penalty"]):
            insight = (
                f"To minimize your off-hours penalty ({off_hours_p}), audit standby HVAC, lighting, and non-critical "
                f"workstations outside occupied hours ({occupied_hours}). Essential loads ({essential_str}) remain protected."
            )
        elif any(word in q_lower for word in ["growth", "increase", "change", "reference", "compare", "why"]):
            insight = (
                f"Your growth penalty is {growth_p} compared to the reference baseline for {period_label}. "
                f"Check peak daytime demand spikes during {occupied_hours} and reschedule heavy non-essential batch tasks."
            )
        elif any(word in q_lower for word in ["essential", "comfort", "equipment", "server", "turn off"]):
            insight = (
                f"Operational rules strictly protect essential equipment ({essential_str}) and thermal/lighting comfort "
                f"during {occupied_hours}. Savings must only target non-essential idle loads."
            )
        elif any(word in q_lower for word in ["improve", "save", "reduce", "action", "tip", "recommend"]):
            insight = (
                f"Action plan for {period_label}: 1) Enforce automated shutdown schedules outside {occupied_hours}, "
                f"2) Keep {essential_str} isolated on dedicated circuits, and 3) Monitor phantom standby loads."
            )
        else:
            insight = (
                f"Regarding '{question.strip()}': For {period_label}, maintain comfort during {occupied_hours} "
                f"and keep {essential_str} running continuously while trimming non-essential off-hours consumption."
            )

        return f"Advice for {period_label} (Score: {score_text}): {insight}"

    def answer_question(self, request: Union[CoachRequest, Dict[str, Any], str], **kwargs) -> CoachResponse:
        """Generates contextual coaching advice honoring comfort and constraints (FR-C4..FR-C9).

        Supports CoachRequest objects as well as legacy parameter calls.
        """
        # Adapt legacy signature: answer_question(question, context, period_summary)
        if isinstance(request, str):
            question_text = request
            ctx = kwargs.get("context")
            summary = kwargs.get("period_summary", {})
            req = CoachRequest(question=question_text, context=ctx, period_summary=summary)
        elif isinstance(request, dict):
            req = CoachRequest(
                question=request.get("question", ""),
                context=request.get("context"),
                period_summary=request.get("period_summary", {})
            )
        elif isinstance(request, CoachRequest):
            req = request
        else:
            raise TypeError("Request must be an instance of CoachRequest or valid question string.")

        # Guard: question validation (FR-C4)
        if not req.question or not req.question.strip():
            raise CoachError("Question cannot be empty or whitespace.")

        # Extract context data safely
        period_label = req.period_summary.get("period", "selected period")
        score = req.period_summary.get("score")
        penalties = req.period_summary.get("penalties", {})
        growth_p = penalties.get("growth_penalty", 0.0)
        off_hours_p = penalties.get("off_hours_penalty", 0.0)

        occupied_hours = req.context.get_occupied_hours() if req.context else "Mon-Fri 08:00-18:00"
        essential_loads = req.context.get_essential_loads() if req.context else ["Server Room", "Emergency Lighting"]
        essential_str = ", ".join(essential_loads) if essential_loads else "Server Room, Emergency Lighting"

        # 1. Attempt OpenAI call if configured (FR-C1)
        if self._client:
            try:
                system_prompt = (
                    "You are an AI Sustainability Coach for an energy management platform. "
                    "Provide concise, actionable, and non-destructive advice. "
                    f"Operational constraints: Occupied hours are '{occupied_hours}'. "
                    f"Essential loads that must NEVER be powered down or curtailed: {essential_str}. "
                    "Always explicitly state the period covered and relate advice to savings."
                )
                user_prompt = (
                    f"Building Period: {period_label}. Sustainability Score: {score}/100. "
                    f"Growth Penalty: {growth_p}, Off-hours Penalty: {off_hours_p}. "
                    f"User inquiry: '{req.question}'"
                )

                response = self._client.chat.completions.create(
                    model=self._model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    max_tokens=250,
                    temperature=0.3
                )
                answer_content = response.choices[0].message.content.strip()
                self._last_status = "ready"
                return CoachResponse(
                    answer=answer_content,
                    status="ready",
                    period=period_label,
                    score=score,
                    penalties=penalties
                )
            except Exception as api_err:
                logger.warning(f"OpenAI service unavailable, invoking fallback: {api_err}")

        # 2. Intent-aware Rule-based Fallback (NFR-C7)
        fallback_advice = self._build_contextual_fallback(
            question=req.question,
            period_label=period_label,
            score=score,
            growth_p=growth_p,
            off_hours_p=off_hours_p,
            occupied_hours=occupied_hours,
            essential_str=essential_str
        )
        self._last_status = "fallback" if self._client else "ready"
        return CoachResponse(
            answer=fallback_advice,
            status=self._last_status,
            period=period_label,
            score=score,
            penalties=penalties
        )