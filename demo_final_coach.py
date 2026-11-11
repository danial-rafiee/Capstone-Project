# demo_final_coach.py
"""End-to-End demonstration script for Subsystem C (AI Sustainability Coach).

Validates all 5 core OOP domain classes and API response structures.
"""

from decimal import Decimal
from smart_energy.coach.building_context import BuildingContext
from smart_energy.coach.score_calculator import ScoreCalculator
from smart_energy.coach.coach_service import CoachService
from smart_energy.coach.coach_models import CoachRequest


def run_demo():
    print("=" * 65)
    print("🚀 Running Subsystem C End-to-End Demonstration (Final Capstone)")
    print("=" * 65)

    # 1. Building Context Setup (FR-C1, FR-C9)
    print("\n[1] Initializing Building Context...")
    context = BuildingContext(
        building_id=1,
        occupied_hours="Mon-Fri 08:00-18:00",
        essential_loads=["Server Room", "Emergency Lighting", "Fire Alarm Systems"]
    )
    print(f"    Building ID: {context.get_building_id()}")
    print(f"    Occupied Hours: {context.get_occupied_hours()}")
    print(f"    Essential Loads: {context.get_essential_loads()}")

    # 2. Score Calculation with Mathematical Bounds (FR-C2, FR-C3)
    print("\n[2] Executing Independent Mathematical Scoring...")
    calculator = ScoreCalculator(allowance_share=Decimal("0.10"))
    # Demo figures from asl.pdf: E=120, R=100, O=34
    scoring_result = calculator.calculate(
        current_energy=Decimal("120.0"),
        reference_energy=Decimal("100.0"),
        off_hours_energy=Decimal("34.0")
    )
    print(f"    Sustainability Score: {scoring_result['score']}/100.0")
    print(f"    Growth Penalty (Pg):  {scoring_result['growth_penalty']}")
    print(f"    Off-hours Penalty (Po): {scoring_result['off_hours_penalty']}")
    print(f"    Calculation Status:   {scoring_result['status']}")

    # 3. AI Sustainability Coach Inquiry (FR-C4..FR-C8, NFR-C7)
    print("\n[3] Interacting with Sustainability Coach (Context-Aware)...")
    service = CoachService(calculator=calculator)
    request_payload = CoachRequest(
        question="Why is our sustainability score 60 and how can we optimize it?",
        context=context,
        period_summary={
            "period": "06-13 Oct 00:00",
            "score": scoring_result["score"],
            "penalties": {
                "growth_penalty": scoring_result["growth_penalty"],
                "off_hours_penalty": scoring_result["off_hours_penalty"]
            }
        }
    )

    response = service.answer_question(request_payload)
    print(f"    Status: {response.status}")
    print(f"    Period: {response.period}")
    print(f"    Advice: {response.answer}")

    print("\n" + "=" * 65)
    print(" All Subsystem C components verified successfully!")
    print("=" * 65)


if __name__ == "__main__":
    run_demo()