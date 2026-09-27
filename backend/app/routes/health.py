"""Health endpoints.

``/api/health``      liveness  - is the process serving requests?
``/api/health/ready`` readiness - can it reach its datastores?
"""

from flask import Blueprint, current_app

from ..extensions import db
from ..utils import mongo

health_bp = Blueprint("health", __name__)


@health_bp.get("")
def health():
    return {
        "status": "ok",
        "service": "loan-platform-api",
        "environment": current_app.config.get("ENV", "development"),
        "database_dialect": db.engine.dialect.name,
    }


@health_bp.get("/ready")
def ready():
    database = _check_database()
    mongo_state = mongo.ping()

    # MongoDB only holds audit/document data, so it is reported but not fatal.
    healthy = database["connected"]
    return (
        {
            "status": "ready" if healthy else "degraded",
            "checks": {"database": database, "mongo": mongo_state},
        },
        200 if healthy else 503,
    )


def _check_database():
    try:
        db.session.execute(db.text("SELECT 1"))
        return {"connected": True, "dialect": db.engine.dialect.name}
    except Exception as exc:  # surfaced to the operator, not to end users
        current_app.logger.warning("Database readiness check failed: %s", exc)
        return {"connected": False, "error": str(exc)}
