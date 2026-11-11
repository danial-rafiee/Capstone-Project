# smart_energy/coach/coach_api.py
"""Flask Web API Blueprint for Subsystem C (AI Sustainability Coach)."""

from flask import Blueprint, jsonify, request
from datetime import datetime
from decimal import Decimal

from smart_energy.coach.building_context import BuildingContext
from smart_energy.coach.coach_service import CoachService
from smart_energy.coach.coach_models import CoachRequest
from smart_energy.coach.exceptions import CoachError, BuildingNotFoundError, InvalidEvaluationDataError


def _serialize_record(record: dict) -> dict:
    """Helper to convert Decimal and datetime instances into JSON-serializable types."""
    res = {}
    for k, v in record.items():
        if isinstance(v, Decimal):
            res[k] = float(v)
        elif isinstance(v, datetime):
            res[k] = v.isoformat()
        else:
            res[k] = v
    return res


def create_coach_blueprint(coach_service_or_repo, repository=None) -> Blueprint:
    """Factory creating blueprint. Supports both (repo) and (service, repo) signatures."""
    if repository is None and hasattr(coach_service_or_repo, "list_for_building"):
        repo = coach_service_or_repo
        service = None
    else:
        service = coach_service_or_repo
        repo = repository

    bp = Blueprint("coach_api", __name__, url_prefix="/api/coach")

    @bp.route("/evaluations/<int:building_id>", methods=["GET"])
    def get_evaluations(building_id: int):
        if repo is None:
            return jsonify({"error": "Repository not configured"}), 500

        try:
            records = repo.list_for_building(building_id)
            serialized = [_serialize_record(r) for r in records]
            return jsonify({
                "building_id": building_id,
                "count": len(serialized),
                "evaluations": serialized
            }), 200
        except BuildingNotFoundError as err:
            return jsonify({"error": err.message}), err.status_code
        except Exception as err:
            return jsonify({"error": f"Internal database error: {str(err)}"}), 500

    @bp.route("/ask", methods=["POST"])
    def ask_coach():
        if service is None:
            return jsonify({"error": "Coach service not configured"}), 500

        payload = request.get_json(silent=True)
        if not payload:
            return jsonify({"error": "Invalid or missing JSON payload"}), 400

        question = payload.get("question")
        if not question or not str(question).strip():
            return jsonify({"error": "Question cannot be empty or whitespace"}), 400

        try:
            b_id = int(payload.get("building_id", 1))
            occupied = payload.get("occupied_hours", "Mon-Fri 08:00-18:00")
            essential = payload.get("essential_loads", ["Server Room", "Emergency Lighting"])
            context = BuildingContext(building_id=b_id, occupied_hours=occupied, essential_loads=essential)

            period_summary = {
                "period": payload.get("period", "selected period"),
                "score": payload.get("score", 100.0),
                "penalties": payload.get("penalties", {})
            }

            coach_req = CoachRequest(question=question, context=context, period_summary=period_summary)
            coach_resp = service.answer_question(coach_req)

            return jsonify(coach_resp.to_dict()), 200

        except (CoachError, InvalidEvaluationDataError) as dom_err:
            status = getattr(dom_err, "status_code", 400)
            msg = getattr(dom_err, "message", str(dom_err))
            return jsonify({"error": msg}), status
        except Exception as exc:
            return jsonify({"error": f"Failed to process inquiry: {str(exc)}"}), 500

    return bp
