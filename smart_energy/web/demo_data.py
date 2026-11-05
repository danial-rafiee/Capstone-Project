# Generates demo dashboard data

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from smart_energy.analytics import Building, Meter, Reading, EnergySettings, AnalyticsService
from smart_energy.coach import BuildingContext, ScoreCalculator, CoachService
from .domain import TimeRange, EnergySummary, CoachPanel


def build_demo_dashboard() -> dict:

    start = datetime(2026, 11, 4, 7, 55, tzinfo=timezone.utc)
    end = start + timedelta(minutes=10)
    building = Building(1, "Demo Office")
    meter = Meter(101, building, "Main Meter")
    readings = [
        Reading(meter, start, start + timedelta(minutes=5), Decimal("1.0")),
        Reading(meter, start + timedelta(minutes=5), end, Decimal("4.0")),
    ]
    settings = EnergySettings(building, Decimal("0.30"), Decimal("0.40"), Decimal("0.10"))
    totals = AnalyticsService(settings, readings).totals()

    # B does not yet compute these metrics. They are explicit, same-period fixtures.
    reference = Decimal("4.0")
    off_hours = Decimal("1.0")
    context = BuildingContext(building.get_building_id(),
                              occupied_hours="Mon-Fri 08:00-18:00",
                              essential_loads=["Server", "Safety lighting"])
    coach_service = CoachService(ScoreCalculator(settings.get_off_hours_share()))
    assessment = coach_service.assess_sustainability(totals["energy_kwh"], reference, off_hours)
    question = "How can we reduce consumption without affecting essential equipment?"
    period = f"{start.isoformat()} to {end.isoformat()}"
    response = coach_service.answer_question(question, context,
                                             {**totals, **assessment, "period": period})
    pg, po = assessment["growth_penalty"], assessment["off_hours_penalty"]
    penalties = f"Growth: {pg}; off-hours: {po}"

    return {
        "building_name": building.get_name(),
        "time_range": TimeRange("custom", start, end),
        "summary": EnergySummary(totals["energy_kwh"], reference - totals["energy_kwh"],
                                 reference, assessment["score"], penalties),
        "coach": CoachPanel(question, response["answer"]),
        "estimated_cost_eur": totals["estimated_cost_eur"],
        "estimated_co2_kg": totals["estimated_co2_kg"],
        "off_hours_energy_kwh": off_hours,
    }
