"""Customer profile model.

Profile fields that only ever apply to borrowers live here, keeping ``users``
lean for officers and admins.
"""

from ..extensions import db
from ..utils.time import utcnow
from .types import BigInt


class Customer(db.Model):
    __tablename__ = "customers"

    id = db.Column(BigInt, primary_key=True)
    # one-to-one with users; a login can own at most one customer profile
    user_id = db.Column(
        BigInt, db.ForeignKey("users.id"), nullable=False, unique=True, index=True
    )
    dob = db.Column(db.Date, nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    address = db.Column(db.String(255), nullable=True)
    employment_type = db.Column(db.String(40), nullable=True)
    created_at = db.Column(
        db.DateTime, nullable=False, default=utcnow, server_default=db.func.now()
    )

    user = db.relationship("User", back_populates="customer")
    applications = db.relationship(
        "LoanApplication",
        back_populates="customer",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Customer {self.id} user={self.user_id}>"
