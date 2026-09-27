"""Credit assessment model - the persisted output of the rule engine."""

import json

from ..extensions import db
from ..utils.time import utcnow
from .enums import Recommendation, RiskLevel
from .types import BigInt, enum_column


class CreditAssessment(db.Model):
    __tablename__ = "credit_assessments"

    id = db.Column(BigInt, primary_key=True)
    application_id = db.Column(
        BigInt, db.ForeignKey("loan_applications.id"), nullable=False, index=True
    )
    score = db.Column(db.Integer, nullable=False)
    risk_level = db.Column(enum_column(RiskLevel, "risk_level"), nullable=False)
    recommendation = db.Column(
        enum_column(Recommendation, "recommendation"), nullable=False
    )
    # JSON-encoded list[str]. Text keeps it readable in both SQLite and MySQL
    # without depending on the JSON column type.
    reasons_json = db.Column(db.Text, nullable=False, default="[]")
    assessed_at = db.Column(
        db.DateTime, nullable=False, default=utcnow, server_default=db.func.now()
    )
    # Who triggered the assessment (an officer, or the customer on submit).
    assessed_by_id = db.Column(BigInt, db.ForeignKey("users.id"), nullable=True)

    application = db.relationship("LoanApplication", back_populates="assessments")

    @property
    def reasons(self) -> list:
        """The explanation list behind the score."""
        try:
            value = json.loads(self.reasons_json or "[]")
        except (TypeError, ValueError):
            return []
        return value if isinstance(value, list) else []

    @reasons.setter
    def reasons(self, items) -> None:
        self.reasons_json = json.dumps(list(items or []))

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<CreditAssessment app={self.application_id} score={self.score}>"
