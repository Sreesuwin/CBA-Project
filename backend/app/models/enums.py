"""Controlled vocabularies used across the domain.

Every status/role/level in the system is a member here, so there is exactly one
place to look when asking "what values are legal?".
"""

import enum


class UserRole(str, enum.Enum):
    CUSTOMER = "CUSTOMER"
    LOAN_OFFICER = "LOAN_OFFICER"
    ADMIN = "ADMIN"


class ApplicationStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    MORE_INFORMATION_REQUIRED = "MORE_INFORMATION_REQUIRED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

    @property
    def is_open(self) -> bool:
        """True while an application can still be worked on."""
        return self in {
            ApplicationStatus.DRAFT,
            ApplicationStatus.SUBMITTED,
            ApplicationStatus.UNDER_REVIEW,
            ApplicationStatus.MORE_INFORMATION_REQUIRED,
        }


class RiskLevel(str, enum.Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"


class Recommendation(str, enum.Enum):
    ELIGIBLE = "ELIGIBLE"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    NOT_RECOMMENDED = "NOT_RECOMMENDED"


class DecisionType(str, enum.Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    REQUEST_INFO = "REQUEST_INFO"


class RepaymentStatus(str, enum.Enum):
    PENDING = "PENDING"
    PAID = "PAID"
    OVERDUE = "OVERDUE"


# Document metadata lives in MongoDB rather than SQL, but the allowed values are
# part of the domain vocabulary and get validated on the way in.
class DocumentType(str, enum.Enum):
    SALARY_SLIP = "SALARY_SLIP"
    BANK_STATEMENT = "BANK_STATEMENT"
    ID_PROOF = "ID_PROOF"
    ADDRESS_PROOF = "ADDRESS_PROOF"
    ITR = "ITR"
    OTHER = "OTHER"


class DocumentStatus(str, enum.Enum):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


class EmploymentType(str, enum.Enum):
    SALARIED = "SALARIED"
    SELF_EMPLOYED = "SELF_EMPLOYED"
    BUSINESS_OWNER = "BUSINESS_OWNER"
    STUDENT = "STUDENT"
    UNEMPLOYED = "UNEMPLOYED"
    RETIRED = "RETIRED"
