"""System-wide audit log (ADMIN only).

The per-application trail lives under ``/api/applications/<id>/audit`` for the
people involved in that application. This endpoint is the administrative view
across every application.
"""

from flask import Blueprint

from ..middleware.auth import roles_required
from ..models import UserRole
from ..services import audit_service

audit_bp = Blueprint("audit", __name__)


@audit_bp.get("")
@roles_required(UserRole.ADMIN)
def list_audit():
    entries = audit_service.list_all()
    return {"audit": [audit_service.serialize(entry) for entry in entries]}
