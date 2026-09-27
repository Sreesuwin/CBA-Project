"""Loan application and its financial details.

``customer_id`` points at ``customers.id``, not ``users.id`` - the doc's starter
schema contradicted its own table list on this point. Ownership checks resolve
the caller through ``customers.user_id``.
"""

from ..extensions import db
from ..utils.time import utcnow
from .enums import ApplicationStatus
from .types import BigInt, enum_column


class LoanApplication(db.Model):
    __tablename__ = "loan_applications"

    id = db.Column(BigInt, primary_key=True)
    # Server-generated, e.g. LN-2026-0001. Never accepted from the client.
    application_no = db.Column(db.String(30), nullable=False, unique=True, index=True)
    customer_id = db.Column(
        BigInt, db.ForeignKey("customers.id"), nullable=False, index=True
    )
    product_id = db.Column(
        BigInt, db.ForeignKey("loan_products.id"), nullable=False, index=True
    )
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    tenure = db.Column(db.Integer, nullable=False)  # months
    purpose = db.Column(db.String(255), nullable=True)
    status = db.Column(
        enum_column(ApplicationStatus, "application_status"),
        nullable=False,
        default=ApplicationStatus.DRAFT,
        server_default=ApplicationStatus.DRAFT.name,
        index=True,  # the officer queue filters on this
    )
    created_at = db.Column(
        db.DateTime, nullable=False, default=utcnow, server_default=db.func.now()
    )
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
        server_default=db.func.now(),
    )
    submitted_at = db.Column(db.DateTime, nullable=True)

    customer = db.relationship("Customer", back_populates="applications")
    product = db.relationship("LoanProduct", back_populates="applications")
    financial_details = db.relationship(
        "FinancialDetails",
        back_populates="application",
        uselist=False,
        cascade="all, delete-orphan",
    )
    # Reassessment history: many assessments per application, newest last.
    assessments = db.relationship(
        "CreditAssessment",
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="CreditAssessment.assessed_at",
    )
    decisions = db.relationship(
        "LoanDecision",
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="LoanDecision.decision_date",
    )
    repayments = db.relationship(
        "Repayment",
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="Repayment.due_date",
    )

    @property
    def latest_assessment(self):
        """Most recent assessment, or None if the application has not been scored."""
        return self.assessments[-1] if self.assessments else None

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<LoanApplication {self.application_no} {self.status}>"


class FinancialDetails(db.Model):
    __tablename__ = "financial_details"

    id = db.Column(BigInt, primary_key=True)
    application_id = db.Column(
        BigInt,
        db.ForeignKey("loan_applications.id"),
        nullable=False,
        unique=True,
        index=True,
    )
    monthly_income = db.Column(db.Numeric(12, 2), nullable=False)
    monthly_expenses = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    existing_emi = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    existing_loans = db.Column(db.Integer, nullable=False, default=0)
    employment_years = db.Column(db.Integer, nullable=False, default=0)

    application = db.relationship("LoanApplication", back_populates="financial_details")

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<FinancialDetails app={self.application_id} income={self.monthly_income}>"
