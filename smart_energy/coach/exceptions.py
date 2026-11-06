"""Custom exception classes for Subsystem C (Coach)."""


class CoachBaseException(Exception):
    """Base exception for coach subsystem errors."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class InvalidScoreError(CoachBaseException):
    """Raised when an energy sustainability score is outside [0.0, 100.0]."""

    def __init__(self, score: float):
        super().__init__(
            f"Invalid sustainability score '{score}'. Score must be between 0.0 and 100.0.",
            status_code=422,
        )


class BuildingNotFoundError(CoachBaseException):
    """Raised when a requested building does not exist in the database."""

    def __init__(self, building_id: int):
        super().__init__(
            f"Building with ID '{building_id}' was not found.",
            status_code=404,
        )


class EvaluationPersistenceError(CoachBaseException):
    """Raised when saving evaluation fails due to database or validation issues."""

    def __init__(self, reason: str):
        super().__init__(
            f"Failed to persist coach evaluation: {reason}",
            status_code=500,
        )