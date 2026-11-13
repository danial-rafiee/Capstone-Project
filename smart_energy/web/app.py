# Flask app setup for dashboard (subsystem A)

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
from smart_energy.web.domain.dashboard_view import DashboardView
from smart_energy.web.errors import register_web_error_handlers
from smart_energy.coach import evaluate_period
from smart_energy.coach import CoachService, BuildingContext, ScoreCalculator
from smart_energy.coach.coach_models import CoachRequest


def get_db_connection() -> Database:
    # helper for db connection
    return Database()


def create_app(test_config: dict | None = None):
    # create flask app
    app = Flask(__name__)
    if test_config is not None:
        app.config.update(test_config)

    register_web_error_handlers(app)

    @app.get("/")
    def home():
        # grab query params
        view = DashboardView()
        params = view.handle_request(request.args)
        preset = params["preset"]
        user_question = params["question"]

        # get building and meter from repo
        db = get_db_connection()
        building = BuildingRepository(db).get_by_id(1)
        meter = MeterRepository(db).get_by_id(101, building) if building else None

        # handle case where building/meter is missing
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
                latest_reading_time="-",
                estimated_cost_eur=None,
                estimated_co2_kg=None,
                off_hours_energy_kwh=None,
                coverage_percent=0.0,
                energy_series=[],
                max_energy=1.0,
                latest_interval_kwh=None,
                sustainability_score=None,
                growth_penalty=None,
                off_hours_penalty=None,
                energy_change_percent=None
            )

        reading_repo = ReadingRepository(db)
        all_meter_readings = reading_repo.list_for_meter(meter)

        # fix end_time using last reading interval so we don't get gaps
        if all_meter_readings:
            latest_reading = all_meter_readings[-1]
            start_time_interval = latest_reading.get_interval()[0]
            latest_reading_time = start_time_interval.strftime('%Y-%m-%d %H:%M')
            end_time = latest_reading.get_interval()[1]
        else:
            end_time = datetime.now(timezone.utc)
            latest_reading_time = "-"

        # set time windows based on selected preset (24h, 7d, 30d)
        if preset == '7d':
            start_time = end_time - timedelta(days=7)
            ref_end_time = start_time
            ref_start_time = ref_end_time - timedelta(days=7)
        elif preset == '30d':
            start_time = end_time - timedelta(days=30)
            ref_end_time = start_time
            ref_start_time = ref_end_time - timedelta(days=30)
        else:
            preset = '24h'
            start_time = end_time - timedelta(days=1)
            ref_end_time = start_time
            ref_start_time = ref_end_time - timedelta(days=1)

        current_window = TimeWindow(start_time, end_time)
        reference_window = TimeWindow(ref_start_time, ref_end_time)

        schedule = OperatingSchedule(
            "Europe/Berlin",
            {day: [("09:00", "17:00")] for day in range(5)},
        )

        current_readings = reading_repo.list_for_period(meter, current_window.start, current_window.end)
        reference_readings = reading_repo.list_for_period(meter, reference_window.start, reference_window.end)

        settings = EnergySettings(
            building=building,
            tariff=Decimal("0.30"),
            carbon_factor=Decimal("0.40"),
            off_hours_share=Decimal("0.20")
        )

        service = PeriodAnalyticsService(settings, schedule)

        reference_energy_val = None
        comparison_result_full = None
        comparison_status = "unavailable"

        try:
            comparison_result = service.compare(
                meter=meter,
                current_readings=current_readings,
                reference_readings=reference_readings,
                current_window=current_window,
                reference_window=reference_window
            )
            comparison_result_full = comparison_result
            summary = comparison_result["current"]
            reference_summary = comparison_result["reference"]

            if reference_summary and reference_summary.get("energy_kwh") is not None:
                reference_energy_val = float(reference_summary.get("energy_kwh"))

            comparison_data = comparison_result["comparison"]
            comparison_status = comparison_data.get("status", "unavailable")
            energy_saved_percent = comparison_data.get("energy_saved_percent")

            if energy_saved_percent is not None:
                energy_change_percent = float(-energy_saved_percent)
            else:
                energy_change_percent = None
        except Exception:
            # fallback if comparison fails
            summary = service.summarize(meter, current_readings, current_window)
            comparison_data = {"status": "unavailable", "energy_saved_percent": None}
            energy_change_percent = None

        summary_payload = to_json_ready(summary)

        # avoid showing fake zero for missing energy
        raw_energy = summary_payload.get('energy_kwh')
        summary_payload['energy_kwh'] = float(raw_energy) if raw_energy is not None else None

        coverage_fraction_val = summary.get('coverage_fraction')
        coverage_percent = float(coverage_fraction_val) * 100 if coverage_fraction_val is not None else 0.0

        series_list = summary_payload.get('series', [])
        max_energy = max([float(item.get('energy_kwh', 0)) for item in series_list], default=1.0)
        if max_energy == 0:
            max_energy = 1.0

        latest_reading_val = float(series_list[-1].get('energy_kwh')) if series_list and series_list[-1].get(
            'energy_kwh') is not None else None

        # keep ref energy None if missing
        if reference_energy_val is not None:
            summary_payload["reference_energy_kwh"] = reference_energy_val
        else:
            summary_payload["reference_energy_kwh"] = None

        # calculate score and penalties if data is ready
        sustainability_score = None
        growth_penalty_val = None
        off_hours_penalty_val = None

        if comparison_status != "unavailable" and coverage_percent > 0 and comparison_result_full is not None:
            coach_data = evaluate_period(comparison_result_full)
            if isinstance(coach_data, dict) and coach_data.get("score") is not None:
                sustainability_score = coach_data.get("score")
                growth_penalty_val = coach_data.get("growth_penalty", 0.0)
                off_hours_penalty_val = coach_data.get("off_hours_penalty", 0.0)

        start_str = current_window.start.strftime("%Y-%m-%d %H:%M")
        end_str = current_window.end.strftime("%Y-%m-%d %H:%M")
        period_label = f"{preset}: {start_str} to {end_str}"

        period_summary_for_coach = {
            "period": period_label,
            "score": sustainability_score,
            "penalties": {
                "growth_penalty": growth_penalty_val,
                "off_hours_penalty": off_hours_penalty_val
            }
        }

        # call AI coach service
        building_id = getattr(building, 'id', 1)
        building_ctx = BuildingContext(building_id)
        calculator = ScoreCalculator()
        coach_service = CoachService(calculator=calculator)

        coach_req = CoachRequest(
            question=user_question,
            context=building_ctx,
            period_summary=period_summary_for_coach
        )

        try:
            coach_response = coach_service.answer_question(coach_req)
            answer_text = coach_response.answer
            coach_status = coach_response.status
        except Exception:
            answer_text = "AI coach is currently unavailable, but energy metrics and scores are fully operational."
            coach_status = "fallback"

        coach_panel_data = CoachPanel(
            question=user_question,
            answer=answer_text,
            status=coach_status
        )

        est_cost = summary_payload.get('estimated_cost_eur')
        est_co2 = summary_payload.get('estimated_co2_kg')

        return render_template(
            "dashboard.html",
            building_name=building.get_name(),
            summary=summary_payload,
            coach=coach_panel_data,
            building=building,
            meter=meter,
            time_range={
                "preset": preset,
                "start": current_window.start.strftime('%Y-%m-%d %H:%M'),
                "end": current_window.end.strftime('%Y-%m-%d %H:%M')
            },
            latest_reading_time=latest_reading_time,
            estimated_cost_eur=float(est_cost) if est_cost is not None else None,
            estimated_co2_kg=float(est_co2) if est_co2 is not None else None,
            off_hours_energy_kwh=summary_payload.get('off_hours_energy_kwh', None),
            coverage_percent=coverage_percent,
            energy_series=series_list,
            max_energy=max_energy,
            latest_interval_kwh=latest_reading_val,
            sustainability_score=sustainability_score,
            growth_penalty=growth_penalty_val,
            off_hours_penalty=off_hours_penalty_val,
            energy_change_percent=energy_change_percent
        )

    @app.get("/api/latest")
    def api_latest():
        # get latest reading for auto refresh
        db = get_db_connection()
        building = BuildingRepository(db).get_by_id(1)
        meter = MeterRepository(db).get_by_id(101, building) if building else None

        if not building or not meter:
            return jsonify({"latest_interval_kwh": None})

        reading_repo = ReadingRepository(db)
        all_meter_readings = reading_repo.list_for_meter(meter)

        if not all_meter_readings:
            return jsonify({"latest_interval_kwh": None})

        latest_reading = all_meter_readings[-1]
        try:
            val = float(latest_reading.get_energy_kwh()) if hasattr(latest_reading, 'get_energy_kwh') else None
        except Exception:
            val = None

        return jsonify({"latest_interval_kwh": val})

    @app.get("/api/analytics/<int:building_id>/<int:meter_id>")
    def api_analytics(building_id: int, meter_id: int):
        # return json analytics data
        db = get_db_connection()
        building = BuildingRepository(db).get_by_id(building_id)
        meter = MeterRepository(db).get_by_id(meter_id, building) if building else None

        if not building or not meter:
            return {"error": "Building or Meter not found"}, 404

        preset = request.args.get('preset', '24h')

        # sync end time with last reading
        reading_repo = ReadingRepository(db)
        all_meter_readings = reading_repo.list_for_meter(meter)
        if all_meter_readings:
            end_time = all_meter_readings[-1].get_interval()[1]
        else:
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

        readings = reading_repo.list_for_period(meter, window.start, window.end)
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