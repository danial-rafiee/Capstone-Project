# Flask application factory

from flask import Flask, render_template
from datetime import datetime, timezone
from decimal import Decimal
import os

# Import database and repository modules
from smart_energy.analytics.database import Database
from smart_energy.analytics.building_repository import BuildingRepository
from smart_energy.analytics.meter_repository import MeterRepository
from smart_energy.analytics.reading_repository import ReadingRepository
from smart_energy.analytics.energy_settings import EnergySettings
from smart_energy.analytics.analytics_service import AnalyticsService

# Import domain classes from the web/domain directory
from smart_energy.web.domain.time_range import TimeRange
from smart_energy.web.domain.energy_summary import EnergySummary
from smart_energy.web.domain.coach_panel import CoachPanel

# Import web error handlers for cross-layer integration
from smart_energy.web.errors import register_web_error_handlers


def get_db_connection() -> Database:
    """Helper function to instantiate Database (it automatically reads from environment variables)."""
    return Database()


def create_app(test_config: dict | None = None):
    app = Flask(__name__)
    if test_config is not None:
        app.config.update(test_config)

    # Register web error handlers
    register_web_error_handlers(app)

    @app.get("/")
    def home():
        # Connect to MySQL using database class
        db = get_db_connection()
        building = BuildingRepository(db).get_by_id(1)
        meter = MeterRepository(db).get_by_id(101, building) if building else None

        time_range = TimeRange(preset="24h")
        coach = CoachPanel(question="How can we optimize energy consumption?", answer="Reduce peak hour usage.")

        if not building or not meter:
            summary = EnergySummary(totals=0, savings=0)
            return render_template(
                "dashboard.html",
                summary=summary,
                coach=coach,
                estimated_cost_eur=0.0,
                estimated_co2_kg=0.0,
                totals={},
                readings=[],
                building=None,
                meter=None,
                time_range=time_range
            )

        # Fetch readings from MySQL repository
        readings = ReadingRepository(db).list_for_meter(meter)

        # Configure energy settings with required Decimal parameters per EnergySettings definition
        settings = EnergySettings(
            building=building,
            tariff=Decimal("0.30"),
            carbon_factor=Decimal("0.40"),
            off_hours_share=Decimal("0.20")
        )
        analytics = AnalyticsService(settings, readings)
        raw_totals = analytics.totals() or {}

        # Safely extract values with fallbacks
        energy_val = raw_totals.get('energy_kwh', raw_totals.get('energy', 0))
        cost_val = raw_totals.get('cost_eur', raw_totals.get('cost', 0))
        co2_val = raw_totals.get('co2_kg', raw_totals.get('co2', 0))

        # Create EnergySummary instance expected by dashboard.html template
        summary = EnergySummary(
            totals=energy_val,
            savings=0,
            score=85
        )

        # Format totals for frontend display with units
        totals = {
            "energy_kwh": f"{float(energy_val):.2f} kWh",
            "cost_eur": f"{float(cost_val):.2f} EUR",
            "co2_kg": f"{float(co2_val):.2f} kg",
        }

        return render_template(
            "dashboard.html",
            summary=summary,
            coach=coach,
            building=building,
            meter=meter,
            totals=totals,
            readings=readings,
            time_range=time_range,
            estimated_cost_eur=float(cost_val),
            estimated_co2_kg=float(co2_val)
        )

    # Optional JSON API endpoint to explicitly test data integration
    @app.get("/api/analytics/<int:building_id>/<int:meter_id>")
    def api_analytics(building_id: int, meter_id: int):
        db = get_db_connection()
        building = BuildingRepository(db).get_by_id(building_id)
        meter = MeterRepository(db).get_by_id(meter_id, building) if building else None

        if not building or not meter:
            return {"error": "Building or Meter not found"}, 404

        readings = ReadingRepository(db).list_for_meter(meter)
        settings = EnergySettings(
            building=building,
            tariff=Decimal("0.30"),
            carbon_factor=Decimal("0.40"),
            off_hours_share=Decimal("0.20")
        )
        analytics = AnalyticsService(settings, readings)
        raw_totals = analytics.totals() or {}

        energy_val = raw_totals.get('energy_kwh', raw_totals.get('energy', 0))
        cost_val = raw_totals.get('cost_eur', raw_totals.get('cost', 0))
        co2_val = raw_totals.get('co2_kg', raw_totals.get('co2', 0))

        return {
            "building_id": building.get_building_id(),
            "building_name": building.get_name(),
            "meter_id": meter.get_meter_id(),
            "meter_name": meter.get_name(),
            "totals": {
                "energy_kwh": f"{float(energy_val):.2f} kWh",
                "cost_eur": f"{float(cost_val):.2f} EUR",
                "co2_kg": f"{float(co2_val):.2f} kg",
            },
            "readings_count": len(readings)
        }

    return app