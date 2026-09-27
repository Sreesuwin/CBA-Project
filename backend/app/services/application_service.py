"""Loan applications: create, edit a draft, read, list and submit.

Two rules run through this whole module:

1. **Ownership is resolved from the database, never from the request.** A
   customer's applications are found through ``customers.user_id``; there is no
   path where a client-supplied id lets one customer touch another's data.
2. **Draft writes are lenient, submission is strict.** A customer may save an
   incomplete draft, but ``submit`` re-runs every rule against the product -
   amount and tenure inside range, income above the product minimum, financial
   details present - so nothing can reach an officer unvalidated.
"""

from decimal import Decimal

from ..extensions import db
from ..models import (
    ApplicationStatus,
    CreditAssessment,
    Customer,
    FinancialDetails,
    LoanApplication,
    LoanProduct,
    UserRole,
)
from ..utils.errors import ApiError
from ..utils.ids import next_application_no
from ..utils.time import utcnow
from . import audit_service, credit_service

DRAFT_EDITABLE_STATUSES = {ApplicationStatus.DRAFT}


# --------------------------------------------------------------------------
# Lookups / access control
# --------------------------------------------------------------------------
def customer_for(user) -> Customer:
    """The borrower profile belonging to a signed-in customer."""
    customer = db.session.scalar(db.select(Customer).where(Customer.user_id == user.id))
    if customer is None:
        raise ApiError(
            "You need a customer profile before applying for a loan.",
            403,
            code="NO_CUSTOMER_PROFILE",
        )
    return customer


def get_application(application_id: int, user) -> LoanApplication:
    """Load an application, or raise 404 when the caller may not see it.

    A customer requesting another customer's application gets the *same* 404 as
    a nonexistent id - returning 403 would confirm that the id exists and leak
    information about other borrowers.
    """
    application = db.session.get(LoanApplication, application_id)
    if application is None or not can_view(application, user):
        raise ApiError("Application not found.", 404, code="NOT_FOUND")
    return application


def can_view(application: LoanApplication, user) -> bool:
    if user.role in {UserRole.LOAN_OFFICER, UserRole.ADMIN}:
        return True
    return application.customer is not None and application.customer.user_id == user.id


def list_applications(user, status=None):
    """Customer: own applications. Officer/admin: every application."""
    statement = db.select(LoanApplication).order_by(LoanApplication.created_at.desc())

    if user.role == UserRole.CUSTOMER:
        customer = customer_for(user)
        statement = statement.where(LoanApplication.customer_id == customer.id)

    if status:
        statement = statement.where(LoanApplication.status == status)

    return db.session.scalars(statement).all()


# --------------------------------------------------------------------------
# Create / edit
# --------------------------------------------------------------------------
def create_application(user, *, product_id, amount, tenure, purpose=None, financials=None):
    """Start a DRAFT. Amount/tenure ranges are enforced at submit, not here."""
    customer = customer_for(user)
    product = _active_product(product_id)

    application = LoanApplication(
        application_no=next_application_no(),
        customer_id=customer.id,
        product_id=product.id,
        amount=Decimal(amount),
        tenure=int(tenure),
        purpose=purpose,
        status=ApplicationStatus.DRAFT,
    )
    if financials is not None:
        application.financial_details = _build_financials(financials)

    db.session.add(application)
    db.session.flush()
    audit_service.record(
        application.id,
        user.id,
        audit_service.ACTION_CREATED,
        {"product": product.name, "amount": str(application.amount)},
    )
    db.session.commit()
    return application


def update_application(application: LoanApplication, user, data):
    """Edit a draft. Only its owner may do so, and only while it is a draft."""
    _assert_owner(application, user)
    if application.status not in DRAFT_EDITABLE_STATUSES:
        raise ApiError(
            "Only a draft application can be edited.",
            409,
            code="INVALID_STATE",
            details={"status": application.status.value},
        )

    if "product_id" in data:
        application.product = _active_product(data["product_id"])
    for field in ("amount", "tenure", "purpose"):
        if field in data:
            setattr(application, field, data[field])
    if "amount" in data:
        application.amount = Decimal(data["amount"])

    if "financials" in data and data["financials"] is not None:
        financials = data["financials"]
        if application.financial_details is None:
            application.financial_details = _build_financials(financials)
        else:
            _apply_financials(application.financial_details, financials)

    audit_service.record(
        application.id,
        user.id,
        audit_service.ACTION_UPDATED,
        {"fields": sorted(data.keys())},
    )
    db.session.commit()
    return application


# --------------------------------------------------------------------------
# Submit
# --------------------------------------------------------------------------
def submit_application(application: LoanApplication, user):
    """Validate in full and move the application to SUBMITTED, then score it."""
    _assert_owner(application, user)

    resubmittable = {
        ApplicationStatus.DRAFT,
        ApplicationStatus.MORE_INFORMATION_REQUIRED,
    }
    if application.status not in resubmittable:
        raise ApiError(
            "This application is not in a state that can be submitted.",
            409,
            code="INVALID_STATE",
            details={"status": application.status.value},
        )

    _validate_for_submission(application)

    application.status = ApplicationStatus.SUBMITTED
    application.submitted_at = utcnow()

    # Score immediately so the officer's queue already has a recommendation.
    assessment = run_assessment(application, actor_id=user.id)

    audit_service.record(
        application.id,
        user.id,
        audit_service.ACTION_SUBMITTED,
        {"status": application.status.value, "score": assessment.score},
    )
    db.session.commit()
    return application


def _validate_for_submission(application: LoanApplication) -> None:
    product = application.product
    details = application.financial_details
    errors = {}

    amount = Decimal(application.amount)
    if amount < Decimal(product.min_amount):
        errors["amount"] = [f"Amount must be at least {product.min_amount}."]
    elif amount > Decimal(product.max_amount):
        errors["amount"] = [f"Amount must be at most {product.max_amount}."]

    if application.tenure < product.min_tenure:
        errors["tenure"] = [f"Tenure must be at least {product.min_tenure} months."]
    elif application.tenure > product.max_tenure:
        errors["tenure"] = [f"Tenure must be at most {product.max_tenure} months."]

    if details is None:
        errors["financials"] = ["Financial details are required before submitting."]
    elif details.monthly_income is None or Decimal(details.monthly_income) <= 0:
        errors["financials"] = ["Monthly income must be greater than zero."]
    elif Decimal(details.monthly_income) < Decimal(product.min_income):
        errors["financials"] = [
            f"Monthly income must be at least {product.min_income} for this product."
        ]

    if not (application.purpose or "").strip():
        errors["purpose"] = ["Please state the purpose of the loan."]

    if errors:
        raise ApiError("Application is not ready to submit.", 400, details=errors)


# --------------------------------------------------------------------------
# Assessment
# --------------------------------------------------------------------------
def run_assessment(application: LoanApplication, actor_id=None) -> CreditAssessment:
    """Score the application and persist a new assessment row (kept as history)."""
    details = application.financial_details
    if details is None:
        raise ApiError(
            "Financial details are required before an assessment can be run.", 400
        )

    result = credit_service.assess(details)
    assessment = CreditAssessment(
        application_id=application.id,
        score=result["score"],
        risk_level=result["risk"],
        recommendation=result["recommendation"],
        assessed_by_id=actor_id,
    )
    assessment.reasons = result["reasons"]
    db.session.add(assessment)
    db.session.flush()

    audit_service.record(
        application.id,
        actor_id,
        audit_service.ACTION_ASSESSED,
        {"score": result["score"], "risk": result["risk"].value},
    )
    return assessment


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def _active_product(product_id) -> LoanProduct:
    product = db.session.get(LoanProduct, int(product_id))
    if product is None or not product.active:
        raise ApiError(
            "Unknown or inactive loan product.",
            400,
            details={"product_id": ["Select a valid, active loan product."]},
        )
    return product


def _build_financials(data) -> FinancialDetails:
    return FinancialDetails(
        monthly_income=Decimal(data["monthly_income"]),
        monthly_expenses=Decimal(data.get("monthly_expenses", 0)),
        existing_emi=Decimal(data.get("existing_emi", 0)),
        existing_loans=int(data.get("existing_loans", 0)),
        employment_years=int(data.get("employment_years", 0)),
    )


def _apply_financials(details: FinancialDetails, data) -> None:
    details.monthly_income = Decimal(data["monthly_income"])
    details.monthly_expenses = Decimal(data.get("monthly_expenses", 0))
    details.existing_emi = Decimal(data.get("existing_emi", 0))
    details.existing_loans = int(data.get("existing_loans", 0))
    details.employment_years = int(data.get("employment_years", 0))


def _assert_owner(application: LoanApplication, user) -> None:
    """Only the owning customer may mutate an application."""
    if user.role != UserRole.CUSTOMER:
        raise ApiError(
            "Only the applicant can change their application.", 403, code="FORBIDDEN"
        )
    if application.customer is None or application.customer.user_id != user.id:
        # 404 rather than 403, so a guessed id reveals nothing.
        raise ApiError("Application not found.", 404, code="NOT_FOUND")
