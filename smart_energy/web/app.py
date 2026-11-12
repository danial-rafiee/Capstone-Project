# Flask application factory for the Smart Energy Management web interface

from flask import Flask, render_template, jsonify, request
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import os

from smart_energy.analytics.database import Database
from smart_energy.analytics.building_repository import BuildingRepository
from smart_energy.analytics.meter_repository import MeterRepository
from smart_energy.analytics.reading_repository import ReadingRepository
from smart_energy.analytics.energy_settings import EnergySettings

from smart_energy.analytics.time_window import TimeWindow
from smart_energy.analytics.operating_schedule import OperatingSchedule
from smart_energy.analytics.period_analytics import PeriodAnalyticsService, to_json_ready

from smart_energy.web.domain.coach_panel import CoachPanel
from smart_energy.web.errors import register_web_error_handlers
from smart_energy.coach import evaluate_period
from smart_energy.coach.coach_service import CoachService
from smart_energy.coach.score_calculator import ScoreCalculator
from smart_energy.coach.building_context import BuildingContext
from smart_energy.coach.coach_models import CoachRequest


def get_db_connection() -> Database:
    # Connect to database
    return Database()


def create_app(test_config: dict | None = None):
    # Initialize Flask app and basic config
    app = Flask(__name__)
    if test_config is not None:
        app.config.update(test_config)

    register_web_error_handlers(app)

    @app.get("/")
    def home():
        # Main dashboard route to load meter and building info
        db = get_db_connection()
        building = BuildingRepository(db).get_by_id(1)
        meter = MeterRepository(db).get_by_id(101, building) if building else None

        if not building or not meter:
            coach_default = CoachPanel(question="How can we optimize energy consumption?",
                                       answer="No meter data available.")
            return render_template(
                "dashboard.html",
                building_name="Not Found",
                summary={},
                coach=coach_default,
                building=None,
                meter=None,
                time_range={"preset": "24h", "start": "-", "end": "-"},
                estimated_cost_eur=0.0,
                estimated_co2_kg=0.0,
                off_hours_energy_kwh="0",
                coverage_percent=0.0,
                energy_series=[],
                max_energy=1.0,
                latest_interval_kwh=0.0,
                sustainability_score=None
            )

        # Get time preset from query params (default to 24h)
        preset = request.args.get('preset', '24h')
        end_time = datetime.now(timezone.utc)

        if preset == '7d':
            start_time = end_time - timedelta(days=7)
        elif preset == '30d':
            start_time = end_time - timedelta(days=30)
        else:
            preset = '24h'
            start_time = end_time - timedelta(days=1)

        window = TimeWindow(start_time, end_time)

        # Set up building operating schedule
        schedule = OperatingSchedule(
            "Europe/Berlin",
            {day: [("09:00", "17:00")] for day in range(5)},
        )

        # Fetch readings and apply settings
        readings = ReadingRepository(db).list_for_period(meter, window.start, window.end)

        settings = EnergySettings(
            building=building,
            tariff=Decimal("0.30"),
            carbon_factor=Decimal("0.40"),
            off_hours_share=Decimal("0.20")
        )

        # Run analytics service for the period
        service = PeriodAnalyticsService(settings, schedule)
        summary = service.summarize(meter, readings, window)

        # Prepare payload and compute metrics safely in Python
        summary_payload = to_json_ready(summary)

        # Ensure energy_kwh is safely cast to float for clean template rendering
        raw_energy = summary_payload.get('energy_kwh')
        summary_payload['energy_kwh'] = float(raw_energy) if raw_energy is not None else 0.0

        coverage_fraction_val = summary.get('coverage_fraction')
        coverage_percent = float(coverage_fraction_val) * 100 if coverage_fraction_val is not None else 0.0

        series_list = summary_payload.get('series', [])
        max_energy = max([float(item.get('energy_kwh', 0)) for item in series_list], default=1.0)
        if max_energy == 0:
            max_energy = 1.0

        # Get the latest interval reading from the current period's series
        latest_reading_val = float(series_list[-1].get('energy_kwh', 0.0)) if series_list else 0.0

        # Subsystem C integration: supply reference_energy_kwh for flexible summary evaluation
        if "reference_energy_kwh" not in summary_payload:
            summary_payload["reference_energy_kwh"] = summary_payload.get('energy_kwh', 0.0) * 0.95

        coach_data = evaluate_period(summary_payload)
        sustainability_score = coach_data.get("score") if isinstance(coach_data, dict) else None

        # --- Subsystem C AI Coach Integration (Interactive) ---
        user_question = request.args.get('question',
                                         'How can we optimize energy consumption during off-hours without violating essential loads?')

        calculator = ScoreCalculator()
        coach_service = CoachService(calculator=calculator)

        period_label = f"{preset}: {window.start.strftime('%Y-%m-%d %H:%M')} to {window.end.strftime('%Y-%m-%d %H:%M')}"
        period_summary_for_coach = {
            "period": period_label,
            "score": sustainability_score,
            "penalties": {
                "growth_penalty": coach_data.get("growth_penalty", 0.0) if isinstance(coach_data, dict) else 0.0,
                "off_hours_penalty": coach_data.get("off_hours_penalty", 0.0) if isinstance(coach_data, dict) else 0.0
            }
        }

        building_id = getattr(building, 'id', 1)
        building_ctx = BuildingContext(building_id)
        coach_req = CoachRequest(
            question=user_question,
            context=building_ctx,
            period_summary=period_summary_for_coach
        )

        coach_response = coach_service.answer_question(coach_req)

        coach_panel_data = CoachPanel(
            question=user_question,
            answer=coach_response.answer
        )

        return render_template(
            "dashboard.html",
            building_name=building.get_name(),
            summary=summary_payload,
            coach=coach_panel_data,
            building=building,
            meter=meter,
            time_range={
                "preset": preset,
                "start": window.start.strftime('%Y-%m-%d %H:%M'),
                "end": window.end.strftime('%Y-%m-%d %H:%M')
            },
            estimated_cost_eur=float(summary_payload.get('estimated_cost_eur') or 0),
            estimated_co2_kg=float(summary_payload.get('estimated_co2_kg') or 0),
            off_hours_energy_kwh=summary_payload.get('off_hours_energy_kwh', '0'),
            coverage_percent=coverage_percent,
            energy_series=series_list,
            max_energy=max_energy,
            latest_interval_kwh=latest_reading_val,
            sustainability_score=sustainability_score
        )

    @app.get("/api/analytics/<int:building_id>/<int:meter_id>")
    def api_analytics(building_id: int, meter_id: int):
        # API endpoint returning analytics JSON
        db = get_db_connection()
        building = BuildingRepository(db).get_by_id(building_id)
        meter = MeterRepository(db).get_by_id(meter_id, building) if building else None

        if not building or not meter:
            return {"error": "Building or Meter not found"}, 404

        preset = request.args.get('preset', '24h')
        end_time = datetime.now(timezone.utc)

        if preset == '7d':
            start_time = end_time - timedelta(days=7)
        elif preset == '30d':
            start_time = end_time - timedelta(days=30)
        else:
            preset = '24h'
            start_time = end_time - timedelta(days=1)

        window = TimeWindow(start_time, end_time)

        schedule = OperatingSchedule(
            "Europe/Berlin",
            {day: [("09:00", "17:00")] for day in range(5)},
        )

        readings = ReadingRepository(db).list_for_period(meter, window.start, window.end)
        settings = EnergySettings(
            building=building,
            tariff=Decimal("0.30"),
            carbon_factor=Decimal("0.40"),
            off_hours_share=Decimal("0.20")
        )

        service = PeriodAnalyticsService(settings, schedule)
        summary = service.summarize(meter, readings, window)

        return jsonify(to_json_ready(summary))

    return app