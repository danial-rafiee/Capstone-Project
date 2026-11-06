"""Unit tests for HA4 - Subsystem C (Coach) Exception Handling and API."""

from datetime import datetime, timezone
from decimal import Decimal
import pytest
from smart_energy.coach.coach_api import create_coach_blueprint
from smart_energy.coach.exceptions import (
    BuildingNotFoundError,
    InvalidScoreError,
)
from smart_energy.coach.score_calculator import ScoreCalculator


# Test 1: Verify custom exception handling for invalid score boundaries
def test_invalid_score_exception():
    invalid_score = 120.5
    with pytest.raises(InvalidScoreError) as exc_info:
        if invalid_score < 0.0 or invalid_score > 100.0:
            raise InvalidScoreError(invalid_score)

    assert exc_info.value.status_code == 422
    assert "120.5" in str(exc_info.value)


# Test 2: Verify custom exception handling when a building ID is not found
def test_building_not_found_exception():
    missing_id = 9999
    with pytest.raises(BuildingNotFoundError) as exc_info:
        raise BuildingNotFoundError(missing_id)

    assert exc_info.value.status_code == 404
    assert "9999" in exc_info.value.message


# Test 3: Verify business logic calculation of energy sustainability score
def test_score_calculator_valid_bounds():
    calc = ScoreCalculator()
    total_energy = Decimal("100.0")
    peak_energy = Decimal("30.0")
    off_hours_energy = Decimal("15.0")

    result = calc.calculate(total_energy, peak_energy, off_hours_energy)
    assert result is not None

    # Handle dictionary output containing score key
    score_val = result["score"] if isinstance(result, dict) else result
    assert Decimal("0.0") <= Decimal(str(score_val)) <= Decimal("100.0")


# Test 4: Verify Flask API returns 200 OK and serialized payload for valid query
def test_api_get_evaluations_success():
    from flask import Flask

    app = Flask(__name__)

    # Mock repository returning valid evaluation with datetime instance
    class DummyRepo:
        def list_for_building(self, building_id):
            return [
                {
                    "evaluation_id": 1,
                    "building_id": building_id,
                    "score": Decimal("85.50"),
                    "penalty_eur": Decimal("1.25"),
                    "peak_detected": False,
                    "advice_summary": "Optimal consumption",
                    "created_at": datetime.now(timezone.utc),
                }
            ]

    app.register_blueprint(create_coach_blueprint(DummyRepo()))
    client = app.test_client()

    response = client.get("/api/coach/evaluations/1")
    assert response.status_code == 200
    data = response.get_json()
    assert data["building_id"] == 1
    assert data["count"] == 1


# Test 5: Verify Flask API response format when no evaluations are present
def test_api_get_evaluations_empty():
    from flask import Flask

    app = Flask(__name__)

    # Mock repository returning empty list for non-existent or blank record
    class EmptyRepo:
        def list_for_building(self, building_id):
            return []

    app.register_blueprint(create_coach_blueprint(EmptyRepo()))
    client = app.test_client()

    response = client.get("/api/coach/evaluations/999")
    assert response.status_code == 200
    data = response.get_json()
    assert data["count"] == 0