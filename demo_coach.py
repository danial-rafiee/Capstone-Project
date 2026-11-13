"""
Subsystem C Demo: Sustainability Scoring and AI Coach
Author: Hananeh Hajari
"""
from decimal import Decimal
from smart_energy.coach import (
    BuildingContext,
    ScoreCalculator,
    CoachService,
)



def run_subsystem_c_demo():
    print("\n" + "=" * 50)
    print("Subsystem C: Sustainability Scoring & AI Coach Demo")
    print("=" * 50)

    # 1. تست و نمایش BuildingContext
    context = BuildingContext(
        building_id=1,
        occupied_hours="Mon-Fri 08:00-18:00",
        essential_loads=["Server Room", "Emergency Lighting"],
    )
    print("Context building ID:", context.get_building_id())
    print("Occupied hours:", context.get_occupied_hours())
    print("Essential loads:", context.get_essential_loads())

    try:
        context.set_occupied_hours("")
    except ValueError as error:
        print("Invalid occupied hours rejected:", error)

    # 2. تست و نمایش ScoreCalculator (E=120, R=100, O=34 -> Score=60)
    calculator = ScoreCalculator(allowance_share=Decimal("0.10"))
    score_result = calculator.calculate(
        current_energy=Decimal("120"),
        reference_energy=Decimal("100"),
        off_hours_energy=Decimal("34"),
    )
    print("\nSustainability Scoring:")
    print("Score:", score_result["score"], "/ 100")
    print("Growth penalty (Pg):", score_result["growth_penalty"])
    print("Off-hours penalty (Po):", score_result["off_hours_penalty"])
    print("Status:", score_result["status"])

    try:
        calculator.set_allowance_share(Decimal("1.5"))
    except ValueError as error:
        print("Invalid allowance share rejected:", error)

    # 3. تست و نمایش CoachService
    coach_service = CoachService(calculator)
    question = "Why is the score 60 and what can we improve?"
    coach_response = coach_service.answer_question(
        question=question,
        context=context,
        period_summary=score_result,
    )

    print("\nAI Coach Panel:")
    print("Question:", question)
    print("Coach Answer:", coach_response["answer"])
    print("Status:", coach_service.get_status())

    try:
        coach_service.answer_question("   ", context, score_result)
    except ValueError as error:
        print("Empty question rejected:", error)


if __name__ == "__main__":
    run_subsystem_c_demo()