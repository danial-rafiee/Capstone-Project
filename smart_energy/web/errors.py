from flask import jsonify

class WebAppError(Exception):
    """exception class for Web Subsystem (Subsystem A)"""
    def __init__(self, message: str, code: str = "web_error"):
        super().__init__(message)
        self.message = message
        self.code = code

class WebAppErrorHandler:
    @staticmethod
    def handle(error: WebAppError) -> dict:
        return {
            "error": True,
            "code": error.code,
            "message": str(error)
        }

def register_web_error_handlers(app):
    @app.errorhandler(WebAppError)
    def handle_web_error(error):
        error_response = WebAppErrorHandler().handle(error)
        code = error.code

        if code == "not_found":
            status_code = 404
        elif code == "bad_request":
            status_code = 400
        else:
            status_code = 500

        return jsonify(error_response), status_code