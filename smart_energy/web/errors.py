from flask import jsonify
from smart_energy.analytics.errors import AnalyticsError, AnalyticsErrorHandler


def register_web_error_handlers(app):
    @app.errorhandler(AnalyticsError)
    def handle_analytics_error(error):
        error_response = AnalyticsErrorHandler().handle(error)
        code = error.code

        if code == "no_readings":
            status_code = 404
        elif code == "database_unavailable":
            status_code = 503
        elif code == "validation_error":
            status_code = 400
        else:
            status_code = 500

        return jsonify(error_response), status_code