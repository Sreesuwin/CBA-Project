"""Response schemas for user data.

Every field here is safe to return to the authenticated owner of the account.
``password_hash`` is simply not part of the schema, so it cannot leak by
accident.
"""

from marshmallow import Schema, fields

from .fields import enum_value


class UserSchema(Schema):
    id = fields.Integer(dump_only=True)
    name = fields.String(dump_only=True)
    email = fields.Email(dump_only=True)
    role = enum_value("role")
    is_active = fields.Boolean(dump_only=True)
    created_at = fields.DateTime(dump_only=True)


class CustomerProfileSchema(Schema):
    """Borrower profile fields. Null when the account has no profile row."""

    dob = fields.Date(allow_none=True)
    phone = fields.String(allow_none=True)
    address = fields.String(allow_none=True)
    employment_type = fields.String(allow_none=True)
