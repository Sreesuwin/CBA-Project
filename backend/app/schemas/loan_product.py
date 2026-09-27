"""Loan product request/response schemas.

The catalogue is small and admin-maintained, so validation is strict: a product
whose amount or tenure range is inverted would make every application against it
unsatisfiable, and the failure would only show up much later at submit time.
"""

from marshmallow import RAISE, Schema, ValidationError, fields, validate, validates_schema

NAME_MAX = 100


class LoanProductSchema(Schema):
    """Response shape for a single product.

    Money is emitted as a string (``"50000.00"``) rather than a float so the
    exact decimal the database stores survives the trip through JSON. The
    frontend converts it to a number for display only.
    """

    id = fields.Integer(dump_only=True)
    name = fields.String(dump_only=True)
    min_amount = fields.Decimal(as_string=True, dump_only=True)
    max_amount = fields.Decimal(as_string=True, dump_only=True)
    interest_rate = fields.Decimal(as_string=True, dump_only=True)
    min_tenure = fields.Integer(dump_only=True)
    max_tenure = fields.Integer(dump_only=True)
    min_income = fields.Decimal(as_string=True, dump_only=True)
    active = fields.Boolean(dump_only=True)


class LoanProductCreateSchema(Schema):
    """Admin create payload. Every field is mandatory."""

    class Meta:
        unknown = RAISE

    name = fields.String(required=True, validate=validate.Length(min=2, max=NAME_MAX))
    min_amount = fields.Decimal(required=True, places=2, validate=validate.Range(min=0))
    max_amount = fields.Decimal(required=True, places=2, validate=validate.Range(min=0))
    interest_rate = fields.Decimal(
        required=True, places=2, validate=validate.Range(min=0, max=100)
    )
    min_tenure = fields.Integer(required=True, validate=validate.Range(min=1))
    max_tenure = fields.Integer(required=True, validate=validate.Range(min=1))
    min_income = fields.Decimal(required=True, places=2, validate=validate.Range(min=0))
    active = fields.Boolean(load_default=True)

    @validates_schema
    def ranges_must_be_ordered(self, data, **kwargs):
        errors = {}
        if "min_amount" in data and "max_amount" in data:
            if data["min_amount"] > data["max_amount"]:
                errors["max_amount"] = ["Maximum amount must be at least the minimum."]
        if "min_tenure" in data and "max_tenure" in data:
            if data["min_tenure"] > data["max_tenure"]:
                errors["max_tenure"] = ["Maximum tenure must be at least the minimum."]
        if errors:
            raise ValidationError(errors)


class LoanProductUpdateSchema(Schema):
    """Admin partial update. Send only the fields that changed."""

    class Meta:
        unknown = RAISE

    name = fields.String(validate=validate.Length(min=2, max=NAME_MAX))
    min_amount = fields.Decimal(places=2, validate=validate.Range(min=0))
    max_amount = fields.Decimal(places=2, validate=validate.Range(min=0))
    interest_rate = fields.Decimal(places=2, validate=validate.Range(min=0, max=100))
    min_tenure = fields.Integer(validate=validate.Range(min=1))
    max_tenure = fields.Integer(validate=validate.Range(min=1))
    min_income = fields.Decimal(places=2, validate=validate.Range(min=0))
    active = fields.Boolean()
