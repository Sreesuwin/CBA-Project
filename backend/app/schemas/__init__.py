"""Marshmallow schemas - the API's request and response boundary.

Validation lives here rather than in route handlers, and the services repeat
the checks that matter, so a malformed request can never skip a rule.
"""

from .application import (
    ApplicationCreateSchema,
    ApplicationSchema,
    ApplicationUpdateSchema,
    DecisionSchema,
    DocumentCreateSchema,
    FinancialDetailsSchema,
)
from .auth import ChangePasswordSchema, LoginSchema, ProfileUpdateSchema, RegisterSchema
from .loan_product import (
    LoanProductCreateSchema,
    LoanProductSchema,
    LoanProductUpdateSchema,
)
from .user import CustomerProfileSchema, UserSchema

__all__ = [
    "ApplicationCreateSchema",
    "ApplicationSchema",
    "ApplicationUpdateSchema",
    "ChangePasswordSchema",
    "CustomerProfileSchema",
    "DecisionSchema",
    "DocumentCreateSchema",
    "FinancialDetailsSchema",
    "LoanProductCreateSchema",
    "LoanProductSchema",
    "LoanProductUpdateSchema",
    "LoginSchema",
    "ProfileUpdateSchema",
    "RegisterSchema",
    "UserSchema",
]
