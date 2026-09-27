"""Loan product endpoints.

    GET    /api/loan-products        public - active products only
    GET    /api/loan-products?all=1  staff  - full catalogue including retired
    POST   /api/loan-products        ADMIN  - add a product
    GET    /api/loan-products/<id>   public - one product
    PUT    /api/loan-products/<id>   ADMIN  - edit a product

Listing is public because the marketing/apply page needs the catalogue before a
customer has signed in. Everything that writes is ADMIN-only.
"""

from flask import Blueprint, request
from flask_jwt_extended import verify_jwt_in_request

from ..middleware.auth import current_user, roles_required
from ..models import UserRole
from ..schemas import (
    LoanProductCreateSchema,
    LoanProductSchema,
    LoanProductUpdateSchema,
)
from ..services import product_service
from ..utils.errors import ApiError

loan_products_bp = Blueprint("loan_products", __name__)

_product_schema = LoanProductSchema()
_create_schema = LoanProductCreateSchema()
_update_schema = LoanProductUpdateSchema()


def _body():
    return request.get_json(silent=True) or {}


@loan_products_bp.get("")
def list_products():
    """Active products for everyone; the full catalogue for signed-in staff.

    ``?all=1`` is ignored for anonymous callers and customers rather than being
    rejected, so the same public URL stays safe to share.
    """
    include_all = request.args.get("all") in {"1", "true", "yes"}

    if include_all:
        verify_jwt_in_request(optional=True)
        user = current_user()
        if user is not None and user.role in {UserRole.ADMIN, UserRole.LOAN_OFFICER}:
            products = product_service.list_products(active_only=False)
            return {"products": _product_schema.dump(products, many=True)}

    products = product_service.list_products(active_only=True)
    return {"products": _product_schema.dump(products, many=True)}


@loan_products_bp.get("/<int:product_id>")
def get_product(product_id):
    product = product_service.get_product(product_id)
    return {"product": _product_schema.dump(product)}


@loan_products_bp.post("")
@roles_required(UserRole.ADMIN)
def create_product():
    data = _create_schema.load(_body())
    product = product_service.create_product(data)
    return {"product": _product_schema.dump(product)}, 201


@loan_products_bp.put("/<int:product_id>")
@roles_required(UserRole.ADMIN)
def update_product(product_id):
    data = _update_schema.load(_body(), partial=True)
    if not data:
        raise ApiError("No fields to update.", 400)

    product = product_service.get_product(product_id)
    product = product_service.update_product(product, data)
    return {"product": _product_schema.dump(product)}
