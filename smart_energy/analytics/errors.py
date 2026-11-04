"""Errors and safe error responses for subsystem B."""

from mysql.connector import Error as MySQLError


class AnalyticsError(Exception):
    """Represent an application error in subsystem B."""

    def __init__(self, message: str, code: str = "analytics_error"):
        super().__init__(message)
        self.code = code


class AnalyticsErrorHandler:
    """Convert subsystem errors into a consistent response structure."""

    def handle(self, error: Exception) -> dict:
        if isinstance(error, AnalyticsError):
            code = error.code
            message = str(error)

        elif isinstance(error, MySQLError):
            code = "database_error"
            message = "The energy database operation failed."

        elif isinstance(error, (ValueError, TypeError)):
            code = "validation_error"
            message = "The energy data or operation is not valid."

        else:
            code = "unexpected_error"
            message = "An unexpected error occurred in the energy subsystem."

        return {
            "error": {
                "code": code,
                "message": message,
            }
        }
