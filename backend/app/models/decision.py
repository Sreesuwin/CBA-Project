"""Loan decision model - the officer's recorded outcome."""

from ..extensions import db
from ..utils.time import utcnow
from .enums import DecisionType
from .types import BigInt, enum_column


class LoanDecision(db.Model):
    __tablename__ = "loan_decisions"

    id = db.Column(BigInt, primary_key=True)
    application_id = db.Column(
        BigInt, db.ForeignKey("loan_applications.id"), nullable=False, index=True
    )
    # The role is enforced in the service layer; the FK cannot express "officer".
    officer_id = db.Column(BigInt, db.ForeignKey("users.id"), nullable=False)
    decision = db.Column(enum_column(DecisionType, "decision_type"), nullable=False)
    remarks = db.Column(db.Text, nullable=True)
    decision_date = db.Column(
        db.DateTime, nullable=False, default=utcnow, server_default=db.func.now()
    )

    application = db.relationship("LoanApplication", back_populates="decisions")
    officer = db.relationship("User", back_populates="decisions")

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<LoanDecision app={self.application_id} {self.decision}>"
