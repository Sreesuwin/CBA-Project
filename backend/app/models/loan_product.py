"""Loan product model - the catalogue admins maintain."""

from ..extensions import db
from .types import BigInt


class LoanProduct(db.Model):
    __tablename__ = "loan_products"

    id = db.Column(BigInt, primary_key=True)
    # Unique so the seed script can key off the product name, and so the admin
    # UI cannot create two products with the same display name.
    name = db.Column(db.String(100), nullable=False, unique=True)
    min_amount = db.Column(db.Numeric(12, 2), nullable=False)
    max_amount = db.Column(db.Numeric(12, 2), nullable=False)
    # Annual percentage rate, e.g. 11.50 == 11.5%
    interest_rate = db.Column(db.Numeric(5, 2), nullable=False)
    min_tenure = db.Column(db.Integer, nullable=False)
    max_tenure = db.Column(db.Integer, nullable=False)
    min_income = db.Column(db.Numeric(12, 2), nullable=False)
    active = db.Column(db.Boolean, nullable=False, default=True, server_default=db.true())

    applications = db.relationship("LoanApplication", back_populates="product")

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<LoanProduct {self.id} {self.name}>"
