from typing import Any, Dict, Optional


class MelloException(Exception):
    """Base exception for the Mello SDK."""

    pass


class MelloAPIException(MelloException):
    """Exception raised for API errors (HTTP 4xx or 5xx)."""

    def __init__(
        self,
        status_code: int,
        error_code: str,
        message: str,
        fields: Optional[Dict[str, str]] = None,
    ):
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
        self.fields = fields or {}
        super().__init__(f"[{status_code}] {error_code}: {message}")


class UnauthorizedException(MelloAPIException):
    """Exception raised for 401 Unauthorized errors."""

    pass


class ForbiddenException(MelloAPIException):
    """Exception raised for 403 Forbidden errors."""

    pass


class NotFoundException(MelloAPIException):
    """Exception raised for 404 Not Found errors."""

    pass


class ValidationErrorException(MelloAPIException):
    """Exception raised when request fails validation validation_error."""

    pass


class RateLimitedException(MelloAPIException):
    """Exception raised for rate limiting errors (typically HTTP 429)."""

    pass


def raise_for_status(
    status_code: int, response_json: Optional[Dict[str, Any]] = None
) -> None:
    """Raises a MelloAPIException mapped from the HTTP response status code and JSON error payload."""
    if status_code < 400:
        return

    error_code = "unknown_error"
    message = "An unexpected error occurred"
    fields = None

    if response_json and isinstance(response_json, dict):
        # The schema defines Error object containing "error" (string error code) and optionally "fields"
        error_code = response_json.get("error", "unknown_error")
        message = str(response_json.get("message") or error_code)
        fields = response_json.get("fields")

    if status_code == 401:
        raise UnauthorizedException(status_code, error_code, message, fields)
    elif status_code == 403:
        raise ForbiddenException(status_code, error_code, message, fields)
    elif status_code == 404:
        raise NotFoundException(status_code, error_code, message, fields)
    elif status_code == 422 or error_code == "validation_error":
        raise ValidationErrorException(status_code, error_code, message, fields)
    elif status_code == 429 or error_code == "rate_limited":
        raise RateLimitedException(status_code, error_code, message, fields)
    else:
        raise MelloAPIException(status_code, error_code, message, fields)
