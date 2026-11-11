# Flask application factory for the Smart Energy Management web interface

from flask import Flask, render_template, jsonify
from datetime import datetime, timezone
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


def get_db_connection() -> Database:
    """Establish and return a database connection instance."""
    return Database()


def create_app(test_config: dict | None = None):
    """Create and configure the Flask application."""
    app = Flask(__name__)
    if test_config is not None:
        app.config.update(test_config)

    register_web_error_handlers(app)

    @app.get("/")
    def home():
        """Render the main energy management dashboard."""
        db = get_db_connection()
        building = BuildingRepository(db).get_by_id(1)
        meter = MeterRepository(db).get_by_id(101, building) if building else None

        coach = CoachPanel(question="How can we optimize energy consumption?", answer="Reduce peak hour usage.")

        if not building or not meter:
            return render_template(
                "dashboard.html",
                building_name="Not Found",
                summary={},
                coach=coach,
                building=None,
                meter=None,
                time_range={"preset": "24h", "start": "-", "end": "-"},
                estimated_cost_eur=0.0,
                estimated_co2_kg=0.0,
                off_hours_energy_kwh="0",
                coverage_percent=0.0
            )

        # Define time window for analytics summary
        end_time = datetime.now(timezone.utc)
        start_time = datetime.replace(end_time, hour=0, minute=0, second=0, microsecond=0)
        window = TimeWindow(start_time, end_time)

        # Configure operating schedule
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

        # Run period analytics service
        service = PeriodAnalyticsService(settings, schedule)
        summary = service.summarize(meter, readings, window)

        # Serialize payload and safely parse numerical values for template rendering
        summary_payload = to_json_ready(summary)
        coverage_fraction_val = summary.get('coverage_fraction')
        coverage_percent = float(coverage_fraction_val) * 100 if coverage_fraction_val is not None else 0.0

        return render_template(
            "dashboard.html",
            building_name=building.get_name(),
            summary=summary_payload,
            coach=coach,
            building=building,
            meter=meter,
            time_range={
                "preset": "custom",
                "start": window.start,
                "end": window.end
            },
            estimated_cost_eur=float(summary_payload.get('estimated_cost_eur') or 0),
            estimated_co2_kg=float(summary_payload.get('estimated_co2_kg') or 0),
            off_hours_energy_kwh=summary_payload.get('off_hours_energy_kwh', '0'),
            coverage_percent=coverage_percent
        )

    @app.get("/api/analytics/<int:building_id>/<int:meter_id>")
    def api_analytics(building_id: int, meter_id: int):
        """Provide JSON analytics endpoint for external consumption."""
        db = get_db_connection()
        building = BuildingRepository(db).get_by_id(building_id)
        meter = MeterRepository(db).get_by_id(meter_id, building) if building else None

        if not building or not meter:
            return {"error": "Building or Meter not found"}, 404

        end_time = datetime.now(timezone.utc)
        start_time = datetime.replace(end_time, hour=0, minute=0, second=0, microsecond=0)
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