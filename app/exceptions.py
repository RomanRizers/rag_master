class ApiError(Exception):
    """Base API error with HTTP status and machine-readable code."""

    status_code = 500
    code = "internal_error"

    def __init__(self, message=None, details=None, status_code=None, code=None):
        super().__init__(message or "Internal server error")
        self.message = message or "Internal server error"
        self.details = details
        if status_code is not None:
            self.status_code = status_code
        if code is not None:
            self.code = code


class ValidationError(ApiError):
    status_code = 400
    code = "validation_error"

    def __init__(self, message="Validation failed", details=None, status_code=None, code=None):
        super().__init__(message=message, details=details, status_code=status_code, code=code)


class VectorizationError(ApiError):
    status_code = 503
    code = "vectorization_error"

    def __init__(self, message="Vectorization failed", details=None, status_code=None, code=None):
        super().__init__(message=message, details=details, status_code=status_code, code=code)


class StorageError(ApiError):
    status_code = 503
    code = "storage_error"

    def __init__(self, message="Storage operation failed", details=None, status_code=None, code=None):
        super().__init__(message=message, details=details, status_code=status_code, code=code)
