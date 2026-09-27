"""SQLAlchemy models.

Importing this package registers every table on ``db.metadata``, which is what
``db.create_all()`` walks. Keep the imports even though they look unused.
"""

from .application import FinancialDetails, LoanApplication
from .assessment import CreditAssessment
from .customer import Customer
from .decision import LoanDecision
from .enums import (
    ApplicationStatus,
    DecisionType,
    DocumentStatus,
    DocumentType,
    EmploymentType,
    Recommendation,
    RepaymentStatus,
    RiskLevel,
    UserRole,
)
from .loan_product import LoanProduct
from .repayment import Repayment
from .user import User

__all__ = [
    "CreditAssessment",
    "Customer",
    "FinancialDetails",
    "LoanApplication",
    "LoanDecision",
    "LoanProduct",
    "Repayment",
    "User",
    # enums
    "ApplicationStatus",
    "DecisionType",
    "DocumentStatus",
    "DocumentType",
    "EmploymentType",
    "Recommendation",
    "RepaymentStatus",
    "RiskLevel",
    "UserRole",
]
