"""Request schemas for registration, login, password and profile changes.

These are the API's front door, so unknown fields are rejected outright. A
client sending ``{"role": "ADMIN"}`` to /register fails with a 400 rather than
being silently ignored - the escalation attempt is visible in the logs.
"""

from marshmallow import RAISE, Schema, ValidationError, fields, validate
from marshmallow import validates_schema

from ..models import EmploymentType
from ..utils.security import MAX_PASSWORD_BYTES

EMAIL_MAX = 255
PASSWORD_MIN = 8
NAME_MIN = 2


def password_field():
    """A password meeting the project's minimum complexity rule.

    Between 8 and 72 characters (bcrypt's limit) with at least one letter and
    one digit. Applies to *new* passwords only - never to a login attempt, where
    a strict rule would leak information about the stored password.
    """
    return fields.String(
        required=True,
        validate=[
            validate.Length(
                min=PASSWORD_MIN,
                max=MAX_PASSWORD_BYTES,
                error="Password must be between {min} and {max} characters.",
            ),
            # Note: Regexp uses re.match, which is anchored at the start, so
            # these patterns must lead with .* to search the whole password.
            validate.Regexp(
                r".*[A-Za-z]", error="Password must contain at least one letter."
            ),
            validate.Regexp(
                r".*\d", error="Password must contain at least one digit."
            ),
        ],
    )


class RegisterSchema(Schema):
    """Self-registration. Always creates a CUSTOMER account."""

    class Meta:
        unknown = RAISE

    name = fields.String(required=True, validate=validate.Length(min=NAME_MIN, max=120))
    email = fields.Email(required=True, validate=validate.Length(max=EMAIL_MAX))
    password = password_field()
    # Optional at signup; the customer completes their profile later.
    phone = fields.String(
        load_default=None, validate=validate.Length(max=20), allow_none=True
    )


class LoginSchema(Schema):
    class Meta:
        unknown = RAISE

    email = fields.Email(required=True)
    # required, but deliberately not complexity-checked - see password_field()
    password = fields.String(required=True)


class ChangePasswordSchema(Schema):
    class Meta:
        unknown = RAISE

    current_password = fields.String(required=True)
    new_password = password_field()

    @validates_schema
    def new_password_must_differ(self, data, **kwargs):
        if data.get("current_password") == data.get("new_password"):
            raise ValidationError(
                {"new_password": ["New password must differ from the current one."]}
            )


class ProfileUpdateSchema(Schema):
    """Editable fields on ``/api/users/me``. Send only what changed."""

    class Meta:
        unknown = RAISE

    name = fields.String(validate=validate.Length(min=NAME_MIN, max=120))
    dob = fields.Date(allow_none=True)
    phone = fields.String(validate=validate.Length(max=20), allow_none=True)
    address = fields.String(validate=validate.Length(max=255), allow_none=True)
    employment_type = fields.String(
        validate=validate.OneOf(
            [member.value for member in EmploymentType],
            error="Unknown employment type.",
        ),
        allow_none=True,
    )
