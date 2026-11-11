# smart_energy/coach/exceptions.py
"""Domain exception hierarchy for Subsystem C (Sustainability Scoring & AI Coach)."""


class CoachError(Exception):
    """Base exception class for all Subsystem C domain errors."""
    def __init__(self, message: str = "Coach domain error", status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class BuildingNotFoundError(CoachError):
    """Raised when building metadata or context cannot be resolved."""
    def __init__(self, building_id):
        msg = f"Building {building_id} not found."
        super().__init__(msg, status_code=404)
        self.building_id = building_id
        self.message = msg


class InvalidEvaluationDataError(CoachError):
    """Raised when numeric energy inputs or boundary parameters are invalid."""
    def __init__(self, message: str = "Invalid evaluation data"):
        super().__init__(message, status_code=400)
        self.message = message


class InvalidScoreError(CoachError):
    """Raised when score calculations violate operational boundaries."""
    def __init__(self, score):
        msg = f"Invalid score: {score}. Score must be between 0.0 and 100.0."
        super().__init__(msg, status_code=422)
        self.score = score
        self.message = msg