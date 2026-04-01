from app.exceptions import ApiError
from app.responses import error_response


def register_error_handlers(app):
    @app.errorhandler(ApiError)
    def handle_api_error(error):
        return error_response(
            code=error.code,
            message=error.message,
            details=error.details,
            status=error.status_code,
        )

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        return error_response(
            code="internal_error",
            message="Internal server error",
            details={"type": error.__class__.__name__},
            status=500,
        )
