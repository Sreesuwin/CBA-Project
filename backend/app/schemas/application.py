"""Loan application, financial details, decision and document schemas.

The create/update schemas deliberately do **not** accept ``status``,
``application_no`` or ``customer_id``. Those are server-controlled: status only
moves through the submit/decision endpoints, and ownership is resolved from the
token, never from the request body.
"""

from marshmallow import RAISE, Schema, ValidationError, fields, validate, validates_schema

from ..models import DecisionType, DocumentType, Recommendation, RiskLevel
from .fields import enum_value
from .loan_product import LoanProductSchema


class FinancialDetailsSchema(Schema):
    """Applicant financials. Drives the credit engine, so every field is checked.

    ``monthly_income`` must be positive (the engine divides by it); the rest may
    be zero but never negative.
    """

    monthly_income = fields.Decimal(places=2, validate=validate.Range(min=0.01))
    monthly_expenses = fields.Decimal(places=2, validate=validate.Range(min=0))
    existing_emi = fields.Decimal(places=2, validate=validate.Range(min=0))
    existing_loans = fields.Integer(validate=validate.Range(min=0))
    employment_years = fields.Integer(validate=validate.Range(min=0))


class FinancialDetailsInputSchema(Schema):
    """Financials supplied while creating/editing an application.

    Every field is required *when the block is present*: a partial financial
    record would let the engine divide by a missing income.
    """

    class Meta:
        unknown = RAISE

    monthly_income = fields.Decimal(
        required=True, places=2, validate=validate.Range(min=0.01)
    )
    monthly_expenses = fields.Decimal(
        required=True, places=2, validate=validate.Range(min=0)
    )
    existing_emi = fields.Decimal(required=True, places=2, validate=validate.Range(min=0))
    existing_loans = fields.Integer(load_default=0, validate=validate.Range(min=0))
    employment_years = fields.Integer(load_default=0, validate=validate.Range(min=0))


class ApplicationCreateSchema(Schema):
    class Meta:
        unknown = RAISE

    product_id = fields.Integer(required=True, validate=validate.Range(min=1))
    amount = fields.Decimal(required=True, places=2, validate=validate.Range(min=0.01))
    tenure = fields.Integer(required=True, validate=validate.Range(min=1))
    purpose = fields.String(load_default=None, validate=validate.Length(max=255), allow_none=True)
    # Optional at create time: a customer may save a bare draft and add
    # financials later. Submit requires them.
    financials = fields.Nested(FinancialDetailsInputSchema, load_default=None, allow_none=True)


class ApplicationUpdateSchema(Schema):
    """Draft edit. Only a DRAFT application accepts these fields."""

    class Meta:
        unknown = RAISE

    product_id = fields.Integer(validate=validate.Range(min=1))
    amount = fields.Decimal(places=2, validate=validate.Range(min=0.01))
    tenure = fields.Integer(validate=validate.Range(min=1))
    purpose = fields.String(validate=validate.Length(max=255), allow_none=True)
    financials = fields.Nested(FinancialDetailsInputSchema, allow_none=True)


class DecisionSchema(Schema):
    """Officer outcome. ``remarks`` is required for everything but approval."""

    class Meta:
        unknown = RAISE

    decision = fields.String(
        required=True,
        validate=validate.OneOf(
            [member.value for member in DecisionType], error="Unknown decision."
        ),
    )
    remarks = fields.String(
        load_default=None, validate=validate.Length(max=500), allow_none=True
    )

    @validates_schema
    def remarks_required_unless_approved(self, data, **kwargs):
        if data.get("decision") in {
            DecisionType.REJECT.value,
            DecisionType.REQUEST_INFO.value,
        } and not (data.get("remarks") or "").strip():
            raise ValidationError(
                {"remarks": ["Remarks are required for this decision."]}
            )


class DocumentCreateSchema(Schema):
    """Metadata for a document attached to an application.

    Only metadata lives here - the binary file itself is out of scope - so this
    describes what was uploaded rather than carrying its bytes.
    """

    class Meta:
        unknown = RAISE

    type = fields.String(
        required=True,
        validate=validate.OneOf(
            [member.value for member in DocumentType], error="Unknown document type."
        ),
    )
    filename = fields.String(required=True, validate=validate.Length(min=1, max=255))


class ApplicationSchema(Schema):
    """Full application view. Safe to return to the owner or to staff."""

    id = fields.Integer()
    application_no = fields.String()
    status = enum_value("status")
    amount = fields.Decimal(as_string=True)
    tenure = fields.Integer()
    purpose = fields.String(allow_none=True)
    created_at = fields.DateTime()
    updated_at = fields.DateTime()
    submitted_at = fields.DateTime(allow_none=True)

    product_id = fields.Integer()
    customer_id = fields.Integer()
    product = fields.Nested(LoanProductSchema)
    financial_details = fields.Method("get_financials")
    assessment = fields.Method("get_assessment")
    applicant = fields.Method("get_applicant")
    documents = fields.Method("get_documents")
    decision = fields.Method("get_decision")
    officer_remarks = fields.Method("get_officer_remarks")

    def get_financials(self, application):
        details = application.financial_details
        return FinancialDetailsSchema().dump(details) if details else None

    def get_assessment(self, application):
        assessment = application.latest_assessment
        if assessment is None:
            return None
        return {
            "id": assessment.id,
            "score": assessment.score,
            "risk_level": assessment.risk_level.value,
            "recommendation": assessment.recommendation.value,
            "reasons": assessment.reasons,
            "assessed_at": assessment.assessed_at.isoformat()
            if assessment.assessed_at
            else None,
        }

    def get_applicant(self, application):
        customer = application.customer
        if customer is None or customer.user is None:
            return None
        return {
            "customer_id": customer.id,
            "name": customer.user.name,
            "email": customer.user.email,
            "phone": customer.phone,
            "dob": customer.dob.isoformat() if customer.dob else None,
            "address": customer.address,
            "employment_type": customer.employment_type,
        }

    def get_documents(self, application):
        """Document metadata lives in the flexible store, so it is looked up here.

        The response is joined with it rather than left for the client to
        assemble, so one request gives the UI a complete application view.
        """
        from ..services import document_service

        return document_service.list_for(application.id)["files"]

    def get_decision(self, application):
        if not application.decisions:
            return None
        latest = application.decisions[-1]
        return {
            "decision": latest.decision.value,
            "remarks": latest.remarks,
            "decision_date": latest.decision_date.isoformat()
            if latest.decision_date
            else None,
        }

    def get_officer_remarks(self, application):
        if not application.decisions:
            return None
        return application.decisions[-1].remarks


# Re-exported for callers that want to assert on the vocabulary.
__all__ = [
    "ApplicationCreateSchema",
    "ApplicationSchema",
    "ApplicationUpdateSchema",
    "DecisionSchema",
    "DocumentCreateSchema",
    "FinancialDetailsSchema",
    "FinancialDetailsInputSchema",
    "Recommendation",
    "RiskLevel",
]
