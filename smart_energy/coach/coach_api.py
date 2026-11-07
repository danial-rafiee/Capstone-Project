"""Flask API blueprint for Subsystem C (Coach)."""

from flask import Blueprint, jsonify
from smart_energy.coach.exceptions import (
    BuildingNotFoundError,
    CoachBaseException,
    EvaluationPersistenceError,
    InvalidScoreError,
)


def create_coach_blueprint(repository) -> Blueprint:
    """Factory creating the coach blueprint with dependency injection."""
    coach_bp = Blueprint("coach_api", __name__, url_prefix="/api/coach")

    @coach_bp.errorhandler(CoachBaseException)
    def handle_coach_exception(error: CoachBaseException):
        response = jsonify({
            "error": error.__class__.__name__,
            "message": error.message,
            "status_code": error.status_code,
        })
        response.status_code = error.status_code
        return response

    @coach_bp.route("/evaluations/<int:building_id>", methods=["GET"])
    def get_building_evaluations(building_id: int):
        if building_id <= 0:
            raise BuildingNotFoundError(building_id)

        try:
            records = repository.list_for_building(building_id)
        except Exception as exc:
            raise EvaluationPersistenceError(str(exc)) from exc

        output = []
        for item in records:
            output.append({
                "evaluation_id": item.get("evaluation_id") or item.get("id"),
                "building_id": item.get("building_id"),
                "score": float(item["score"]) if item.get("score") is not None else None,
                "penalty_eur": float(item["penalty_eur"]) if item.get("penalty_eur") is not None else None,
                "peak_detected": bool(item.get("peak_detected")),
                "advice_summary": item.get("advice_summary"),
                "created_at": item["created_at"].isoformat() if hasattr(item.get("created_at"), "isoformat") else str(item.get("created_at")),
            })

        return jsonify({
            "building_id": building_id,
            "count": len(output),
            "evaluations": output,
        }), 200

    return coach_bp




