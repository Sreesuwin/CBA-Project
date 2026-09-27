"""User account model."""

from ..extensions import db
from ..utils.time import utcnow
from .enums import UserRole
from .types import BigInt, enum_column


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(BigInt, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), nullable=False, unique=True, index=True)
    # bcrypt output is always 60 chars; 255 leaves room for a future algorithm.
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(
        enum_column(UserRole, "user_role"), nullable=False, default=UserRole.CUSTOMER, index=True
    )
    is_active = db.Column(
        db.Boolean, nullable=False, default=True, server_default=db.true()
    )
    created_at = db.Column(
        db.DateTime, nullable=False, default=utcnow, server_default=db.func.now()
    )

    customer = db.relationship(
        "Customer",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    decisions = db.relationship("LoanDecision", back_populates="officer")

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<User {self.id} {self.email} {self.role}>"
