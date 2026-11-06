"""Flask Web API routes for Subsystem C (AI Coach & Sustainability Score)."""

from decimal import Decimal
from flask import Blueprint, jsonify, request
from smart_energy.coach.coach_repository import CoachEvaluationRepository


def create_coach_blueprint(coach_repository: CoachEvaluationRepository) -> Blueprint:
    """Factory to create a Flask Blueprint with injected repository dependency."""
    coach_bp = Blueprint("coach_api", __name__, url_prefix="/api/coach")

    @coach_bp.route("/evaluations/<int:building_id>", methods=["GET"])
    def get_building_evaluations(building_id: int):
        """Web API to retrieve all sustainability score evaluations for a building."""
        evaluations = coach_repository.list_for_building(building_id)

        output = [
            {
                "evaluation_id": item["evaluation_id"],
                "building_id": item["building_id"],
                "score": float(item["score"]),
                "penalty_eur": float(item["penalty_eur"]),
                "peak_detected": item["peak_detected"],
                "advice_summary": item["advice_summary"],
                "created_at": item["created_at"].isoformat() if item["created_at"] else None,
            }
            for item in evaluations
        ]
        return jsonify({"building_id": building_id, "count": len(output), "evaluations": output}), 200

    @coach_bp.route("/evaluations", methods=["POST"])
    def save_evaluation():
        """Web API to persist a new sustainability score evaluation."""
        payload = request.get_json(silent=True) or {}
        building_id = payload.get("building_id")
        score = payload.get("score")

        if building_id is None or score is None:
            return jsonify({"error": "building_id and score are required fields."}), 400

        eval_id = coach_repository.save_evaluation(
            building_id=int(building_id),
            score=Decimal(str(score)),
            penalty_eur=Decimal(str(payload.get("penalty_eur", "0.00"))),
            peak_detected=bool(payload.get("peak_detected", False)),
            advice_summary=str(payload.get("advice_summary", "Evaluation recorded")),
        )
        return jsonify({"message": "Evaluation stored successfully", "evaluation_id": eval_id}), 201

    return coach_bp