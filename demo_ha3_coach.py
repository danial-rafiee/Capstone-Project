"""Demonstration script for Subsystem C (HA3): Shared MySQL Persistence & Web API."""

from decimal import Decimal
from flask import Flask
from smart_energy.analytics.database import Database
from smart_energy.coach.coach_repository import CoachRepository, CoachEvaluationRepository
from smart_energy.coach.coach_api import create_coach_blueprint
from smart_energy.coach.exceptions import EvaluationPersistenceError


def main() -> None:
    print("--- Starting HA3 Subsystem C Demonstration (MySQL) ---")

    # 1. Initialize shared MySQL Database and Repository
    database = Database()
    coach_repository = CoachEvaluationRepository(database)
    assert CoachRepository is CoachEvaluationRepository
    building_id = 1

    # 2. Persist evaluations into shared MySQL database
    print("\n[1] Storing sustainability evaluations into MySQL...")
    eval_id_1 = coach_repository.save_evaluation(
        building_id=building_id,
        score=Decimal("87.50"),
        penalty_eur=Decimal("1.25"),
        peak_detected=False,
        advice_summary="Optimal consumption. Keep operating within standard threshold.",
    )
    eval_id_2 = coach_repository.save_evaluation(
        building_id=building_id,
        score=Decimal("62.00"),
        penalty_eur=Decimal("4.80"),
        peak_detected=True,
        advice_summary="Peak consumption detected during off-hours. Shift cooling load.",
    )
    print(f"Persisted evaluation IDs in MySQL: {eval_id_1}, {eval_id_2}")

    # 3. Retrieve evaluations from MySQL using CoachEvaluationRepository
    print("\n[2] Reading evaluations from MySQL via CoachEvaluationRepository...")
    records = coach_repository.list_for_building(building_id)
    print(f"Total retrieved records for building {building_id}: {len(records)}")
    for rec in records[:2]:
        print(
            f" - ID: {rec['evaluation_id']} | Score: {rec['score']} | "
            f"Penalty: EUR {rec['penalty_eur']} | Advice: {rec['advice_summary']}"
        )

    # 4. Expose and verify Web API using Flask test client
    print("\n[3] Testing Web API endpoint with Flask test client...")
    app = Flask(__name__)
    app.register_blueprint(create_coach_blueprint(coach_repository))

    client = app.test_client()
    response = client.get(f"/api/coach/evaluations/{building_id}")

    print(f"HTTP GET /api/coach/evaluations/{building_id} -> Status: {response.status_code}")
    print("Response JSON payload:")
    print(response.get_json())
    print("\n--- Subsystem C HA3 MySQL Integration Completed Successfully ---")


if __name__ == "__main__":
    main()
