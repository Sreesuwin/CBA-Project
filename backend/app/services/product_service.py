"""Loan product catalogue: listing and admin CRUD.

All product database access goes through this module, so route handlers never
build queries directly (a rule the whole backend follows so the schema can move
underneath without touching the API layer).
"""

from ..extensions import db
from ..models import LoanProduct
from ..utils.errors import ApiError

# Fields a client may set on a product, in a stable order.
EDITABLE_FIELDS = (
    "name",
    "min_amount",
    "max_amount",
    "interest_rate",
    "min_tenure",
    "max_tenure",
    "min_income",
    "active",
)


def list_products(*, active_only: bool = True):
    """The catalogue, ordered by name for a stable UI listing.

    Customers only ever see active products; officers and admins pass
    ``active_only=False`` to see the full catalogue including retired ones.
    """
    statement = db.select(LoanProduct).order_by(LoanProduct.name)
    if active_only:
        statement = statement.where(LoanProduct.active.is_(True))
    return db.session.scalars(statement).all()


def get_product(product_id: int) -> LoanProduct:
    product = db.session.get(LoanProduct, product_id)
    if product is None:
        raise ApiError("Loan product not found.", 404, code="NOT_FOUND")
    return product


def create_product(data) -> LoanProduct:
    name = data["name"].strip()

    if find_by_name(name):
        raise ApiError(
            "A loan product with this name already exists.", 409, code="NAME_TAKEN"
        )

    product = LoanProduct(**{**data, "name": name})
    _assert_ranges_valid(product)

    db.session.add(product)
    db.session.commit()
    return product


def update_product(product: LoanProduct, data) -> LoanProduct:
    """Apply a partial update, re-checking ranges against the merged values."""
    if "name" in data:
        name = data["name"].strip()
        existing = find_by_name(name)
        if existing is not None and existing.id != product.id:
            raise ApiError(
                "A loan product with this name already exists.",
                409,
                code="NAME_TAKEN",
            )
        product.name = name

    for field in EDITABLE_FIELDS:
        if field == "name" or field not in data:
            continue
        setattr(product, field, data[field])

    _assert_ranges_valid(product)

    db.session.commit()
    return product


def find_by_name(name: str):
    return db.session.scalar(db.select(LoanProduct).where(LoanProduct.name == name))


def _assert_ranges_valid(product: LoanProduct) -> None:
    """Guard the invariants even when only one side of a range was edited.

    The schema cannot see the stored value when the client sends a *partial*
    update, so a change to ``max_amount`` alone could still leave it below the
    existing ``min_amount``.
    """
    if product.min_amount > product.max_amount:
        raise ApiError(
            "Maximum amount must be at least the minimum amount.",
            400,
            details={"max_amount": ["Must be at least the minimum amount."]},
        )
    if product.min_tenure > product.max_tenure:
        raise ApiError(
            "Maximum tenure must be at least the minimum tenure.",
            400,
            details={"max_tenure": ["Must be at least the minimum tenure."]},
        )
