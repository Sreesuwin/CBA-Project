"""Uniform JSON error responses.

Every failure leaves the API in the same shape so the React client only needs
one error-handling path:

    {"error": {"status": 400, "code": "VALIDATION_ERROR",
               "message": "...", "details": {...}}}
"""

import logging

from flask import current_app, jsonify
from marshmallow import ValidationError
from werkzeug.exceptions import HTTPException

from ..extensions import jwt

logger = logging.getLogger(__name__)

_CODE_BY_STATUS = {
    400: "VALIDATION_ERROR",
    401: "UNAUTHENTICATED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    422: "UNPROCESSABLE_ENTITY",
    500: "INTERNAL_ERROR",
}


class ApiError(Exception):
    """Raise from routes/services to return a structured error response."""

    def __init__(self, message, status_code=400, details=None, code=None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        self.code = code

    def to_dict(self):
        return {
            "status": self.status_code,
            "code": self.code or _CODE_BY_STATUS.get(self.status_code, "ERROR"),
            "message": self.message,
            "details": self.details,
        }


def _respond(status, message, details=None, code=None):
    payload = {
        "error": {
            "status": status,
            "code": code or _CODE_BY_STATUS.get(status, "ERROR"),
            "message": message,
            "details": details or {},
        }
    }
    return jsonify(payload), status


def register_error_handlers(app):
    _register_jwt_error_handlers()

    @app.errorhandler(ApiError)
    def handle_api_error(exc):
        return _respond(exc.status_code, exc.message, exc.details, exc.code)

    @app.errorhandler(ValidationError)
    def handle_marshmallow_error(exc):
        return _respond(400, "Request validation failed.", exc.messages)

    @app.errorhandler(HTTPException)
    def handle_http_error(exc):
        return _respond(exc.code or 500, exc.description or "Request failed.")

    @app.errorhandler(Exception)
    def handle_unexpected_error(exc):
        logger.exception("Unhandled error while serving a request")
        details = {"exception": repr(exc)} if current_app.config.get("DEBUG") else {}
        return _respond(500, "An unexpected error occurred.", details)


def _register_jwt_error_handlers():
    """Give flask-jwt-extended the same envelope as everything else.

    Without these it returns its own ``{"msg": ...}`` shape, and reports a
    malformed token as 422 instead of 401.
    """

    @jwt.unauthorized_loader
    def missing_token(reason):
        return _respond(
            401,
            "Authentication required. Please sign in.",
            {"reason": reason},
            code="UNAUTHENTICATED",
        )

    @jwt.invalid_token_loader
    def invalid_token(reason):
        return _respond(
            401,
            "Invalid authentication token.",
            {"reason": reason},
            code="INVALID_TOKEN",
        )

    @jwt.expired_token_loader
    def expired_token(_jwt_header, _jwt_payload):
        return _respond(
            401,
            "Session expired. Please sign in again.",
            code="TOKEN_EXPIRED",
        )
