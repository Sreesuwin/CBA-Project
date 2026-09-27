"""Loan application endpoints.

Customer
    POST   /api/applications                     create a draft
    GET    /api/applications                     list own applications
    GET    /api/applications/<id>                read one (own only)
    PUT    /api/applications/<id>                edit a draft
    POST   /api/applications/<id>/submit         validate and submit
    POST   /api/applications/<id>/documents      attach document metadata
    GET    /api/applications/<id>/documents      list document metadata
    GET    /api/applications/<id>/audit          own activity trail

Officer / admin
    GET    /api/applications                     every application (queue)
    POST   /api/applications/<id>/assess         (re)run the credit engine
    POST   /api/applications/<id>/approve
    POST   /api/applications/<id>/reject
    POST   /api/applications/<id>/request-info

Every read and write funnels through ``application_service``, where the
ownership and state-machine rules live. The routes stay thin.
"""

from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from ..extensions import db
from ..middleware.auth import require_user
from ..models import ApplicationStatus, DecisionType
from ..schemas import (
    ApplicationCreateSchema,
    ApplicationSchema,
    ApplicationUpdateSchema,
    DecisionSchema,
    DocumentCreateSchema,
)
from ..services import (
    application_service,
    audit_service,
    decision_service,
    document_service,
)
from ..utils.errors import ApiError

applications_bp = Blueprint("applications", __name__)

_application_schema = ApplicationSchema()
_create_schema = ApplicationCreateSchema()
_update_schema = ApplicationUpdateSchema()
_decision_schema = DecisionSchema()
_document_schema = DocumentCreateSchema()


def _body():
    return request.get_json(silent=True) or {}


def _dump(application):
    return _application_schema.dump(application)


# --------------------------------------------------------------------------
# Reads
# --------------------------------------------------------------------------
@applications_bp.get("")
@jwt_required()
def list_applications():
    user = require_user()
    status = request.args.get("status")
    if status and status not in {member.value for member in ApplicationStatus}:
        raise ApiError(
            "Unknown status filter.",
            400,
            details={"status": ["Unknown application status."]},
        )
    applications = application_service.list_applications(user, status=status)
    return {"applications": [_dump(app) for app in applications]}


@applications_bp.get("/<int:application_id>")
@jwt_required()
def get_application(application_id):
    user = require_user()
    application = application_service.get_application(application_id, user)
    return {"application": _dump(application)}


# --------------------------------------------------------------------------
# Customer writes
# --------------------------------------------------------------------------
@applications_bp.post("")
@jwt_required()
def create_application():
    user = require_user()
    data = _create_schema.load(_body())
    application = application_service.create_application(user, **data)
    return {"application": _dump(application)}, 201


@applications_bp.put("/<int:application_id>")
@jwt_required()
def update_application(application_id):
    user = require_user()
    application = application_service.get_application(application_id, user)
    data = _update_schema.load(_body(), partial=True)
    if not data:
        raise ApiError("No fields to update.", 400)
    application = application_service.update_application(application, user, data)
    return {"application": _dump(application)}


@applications_bp.post("/<int:application_id>/submit")
@jwt_required()
def submit_application(application_id):
    user = require_user()
    application = application_service.get_application(application_id, user)
    application = application_service.submit_application(application, user)
    return {"application": _dump(application)}


# --------------------------------------------------------------------------
# Assessment
# --------------------------------------------------------------------------
@applications_bp.post("/<int:application_id>/assess")
@jwt_required()
def assess_application(application_id):
    user = require_user()
    application = application_service.get_application(application_id, user)
    application_service.run_assessment(application, actor_id=user.id)
    db.session.commit()
    db.session.refresh(application)
    return {"application": _dump(application)}


# --------------------------------------------------------------------------
# Decisions
# --------------------------------------------------------------------------
def _decide(application_id, decision_type):
    user = require_user()
    application = application_service.get_application(application_id, user)
    # Remarks are optional for approval and mandatory otherwise, which the
    # schema already enforces; injecting the decision here keeps three small
    # routes instead of one parameterised URL segment.
    data = _decision_schema.load({**_body(), "decision": decision_type.value})
    record = decision_service.record_decision(
        application, user, decision=decision_type, remarks=data.get("remarks")
    )
    return {
        "application": _dump(application),
        "decision": {
            "id": record.id,
            "decision": record.decision.value,
            "remarks": record.remarks,
            "decision_date": record.decision_date.isoformat()
            if record.decision_date
            else None,
        },
    }


@applications_bp.post("/<int:application_id>/approve")
@jwt_required()
def approve_application(application_id):
    return _decide(application_id, DecisionType.APPROVE)


@applications_bp.post("/<int:application_id>/reject")
@jwt_required()
def reject_application(application_id):
    return _decide(application_id, DecisionType.REJECT)


@applications_bp.post("/<int:application_id>/request-info")
@jwt_required()
def request_info(application_id):
    return _decide(application_id, DecisionType.REQUEST_INFO)


# --------------------------------------------------------------------------
# Documents and audit trail (MongoDB-backed, with an in-memory fallback)
# --------------------------------------------------------------------------
@applications_bp.get("/<int:application_id>/audit")
@jwt_required()
def list_audit(application_id):
    user = require_user()
    application_service.get_application(application_id, user)  # access check
    entries = audit_service.list_for(application_id)
    return {"audit": [audit_service.serialize(entry) for entry in entries]}


@applications_bp.get("/<int:application_id>/documents")
@jwt_required()
def list_documents(application_id):
    user = require_user()
    application_service.get_application(application_id, user)  # access check
    return {"document": document_service.list_for(application_id)}


@applications_bp.post("/<int:application_id>/documents")
@jwt_required()
def add_document(application_id):
    user = require_user()
    application_service.get_application(application_id, user)  # access check
    data = _document_schema.load(_body())
    entry = document_service.add_file(application_id, data["type"], data["filename"])
    audit_service.record(
        application_id,
        user.id,
        audit_service.ACTION_DOCUMENT,
        {"type": data["type"], "filename": data["filename"]},
    )
    return {"document": document_service.list_for(application_id), "added": entry}, 201
