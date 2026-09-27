"""Officer decisions: approve, reject or request more information.

The engine *advises* - this module is where a human decides. It enforces the
application state machine (you cannot decide a draft, or re-decide a closed
application), records the outcome against the officer who made it, and, on
approval, seeds the repayment schedule.
"""

from datetime import timedelta
from decimal import Decimal

from ..extensions import db
from ..models import (
    ApplicationStatus,
    DecisionType,
    LoanDecision,
    Repayment,
    RepaymentStatus,
    UserRole,
)
from ..utils.errors import ApiError
from ..utils.time import utcnow
from . import audit_service

# States in which a decision is legal. A draft has not been submitted yet, and
# an approved/rejected application is closed.
DECIDABLE_STATUSES = {
    ApplicationStatus.SUBMITTED,
    ApplicationStatus.UNDER_REVIEW,
    ApplicationStatus.MORE_INFORMATION_REQUIRED,
}

_STATUS_FOR_DECISION = {
    DecisionType.APPROVE: ApplicationStatus.APPROVED,
    DecisionType.REJECT: ApplicationStatus.REJECTED,
    DecisionType.REQUEST_INFO: ApplicationStatus.MORE_INFORMATION_REQUIRED,
}


def record_decision(application, officer, *, decision, remarks=None) -> LoanDecision:
    """Apply a decision to an application and return the recorded row."""
    if officer.role not in {UserRole.LOAN_OFFICER, UserRole.ADMIN}:
        raise ApiError(
            "Only a loan officer can decide an application.", 403, code="FORBIDDEN"
        )

    if application.status not in DECIDABLE_STATUSES:
        raise ApiError(
            "This application cannot be decided in its current state.",
            409,
            code="INVALID_STATE",
            details={"status": application.status.value},
        )

    decision_type = (
        decision if isinstance(decision, DecisionType) else DecisionType(decision)
    )

    if decision_type in {DecisionType.REJECT, DecisionType.REQUEST_INFO} and not (
        remarks or ""
    ).strip():
        raise ApiError(
            "Remarks are required for this decision.",
            400,
            details={"remarks": ["Remarks are required for this decision."]},
        )

    record = LoanDecision(
        application_id=application.id,
        officer_id=officer.id,
        decision=decision_type,
        remarks=(remarks or "").strip() or None,
    )
    db.session.add(record)
    application.status = _STATUS_FOR_DECISION[decision_type]

    if decision_type == DecisionType.APPROVE:
        _schedule_repayments(application)

    audit_service.record(
        application.id,
        officer.id,
        audit_service.ACTION_DECISION,
        {"decision": decision_type.value, "status": application.status.value},
    )
    db.session.commit()
    return record


def _schedule_repayments(application) -> None:
    """Create a monthly repayment row per instalment for an approved loan.

    Replaced wholesale so re-approving cannot duplicate the schedule. The EMI is
    the standard amortising formula; a zero interest rate degenerates to a plain
    principal split.
    """
    for existing in list(application.repayments):
        db.session.delete(existing)

    instalment_count = int(application.tenure)
    if instalment_count <= 0:
        return

    principal = Decimal(application.amount)
    annual_rate = Decimal(application.product.interest_rate)
    emi = _emi(principal, annual_rate, instalment_count)
    start = utcnow().date()

    for index in range(1, instalment_count + 1):
        db.session.add(
            Repayment(
                application_id=application.id,
                due_date=start + timedelta(days=30 * index),
                amount=emi,
                status=RepaymentStatus.PENDING,
            )
        )


def _emi(principal: Decimal, annual_rate: Decimal, months: int) -> Decimal:
    monthly_rate = annual_rate / Decimal(100) / Decimal(12)
    if monthly_rate == 0:
        return (principal / months).quantize(Decimal("0.01"))

    factor = (Decimal(1) + monthly_rate) ** months
    emi = principal * monthly_rate * factor / (factor - Decimal(1))
    return emi.quantize(Decimal("0.01"))
