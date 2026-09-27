"""Repayment schedule model (populated for approved loans)."""

from ..extensions import db
from .enums import RepaymentStatus
from .types import BigInt, enum_column


class Repayment(db.Model):
    __tablename__ = "repayments"

    id = db.Column(BigInt, primary_key=True)
    application_id = db.Column(
        BigInt, db.ForeignKey("loan_applications.id"), nullable=False, index=True
    )
    due_date = db.Column(db.Date, nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    status = db.Column(
        enum_column(RepaymentStatus, "repayment_status"),
        nullable=False,
        default=RepaymentStatus.PENDING,
        server_default=RepaymentStatus.PENDING.name,
    )

    application = db.relationship("LoanApplication", back_populates="repayments")

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Repayment app={self.application_id} due={self.due_date}>"
