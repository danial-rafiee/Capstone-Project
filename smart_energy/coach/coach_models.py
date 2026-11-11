# smart_energy/coach/coach_models.py
"""Domain models for Subsystem C AI Coach requests and responses.

Complies with Capstone Proposal (asl.pdf Subsystem C class diagram).
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any
from smart_energy.coach.building_context import BuildingContext


@dataclass
class CoachRequest:
    """Encapsulates a user inquiry directed to the AI Sustainability Coach.

    Attributes:
        question: User prompt or inquiry text.
        context: BuildingContext instance encapsulating operational boundaries.
        period_summary: Aggregated metrics dictionary provided by Subsystem B.
    """
    question: str
    context: BuildingContext
    period_summary: Dict[str, Any]

    def __post_init__(self):
        if not self.question or not self.question.strip():
            raise ValueError("CoachRequest question cannot be empty or whitespace.")
        if not isinstance(self.context, BuildingContext):
            raise TypeError("CoachRequest context must be an instance of BuildingContext.")
        if not isinstance(self.period_summary, dict):
            raise TypeError("CoachRequest period_summary must be a dictionary.")


@dataclass
class CoachResponse:
    """Encapsulates the structured response returned by the AI Coach.

    Attributes:
        answer: Energy advice or contextual explanation.
        status: Operation status ('ready', 'fallback', 'error').
        period: Human-readable label of the period evaluated.
        score: Normalized sustainability score [0.0, 100.0].
        penalties: Calculated penalty breakdown (Pg, Po).
    """
    answer: str
    status: str
    period: str
    score: Optional[float] = None
    penalties: Optional[Dict[str, float]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the response payload to a dictionary for API transmission."""
        return {
            "answer": self.answer,
            "status": self.status,
            "period": self.period,
            "score": self.score,
            "penalties": self.penalties or {}
        }