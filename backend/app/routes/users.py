"""Endpoints for the signed-in account.

    GET /api/users/me   own account plus borrower profile
    PUT /api/users/me   update own name and profile fields

A customer can only ever reach their own record here - there is no user id in
the URL to tamper with.
"""

from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from ..extensions import db

from ..middleware.auth import require_user, roles_required
from ..models import User, UserRole
from ..schemas import CustomerProfileSchema, ProfileUpdateSchema, UserSchema
from ..services import auth_service
from ..utils.errors import ApiError

users_bp = Blueprint("users", __name__)

_user_schema = UserSchema()
_profile_schema = CustomerProfileSchema()
_profile_update_schema = ProfileUpdateSchema()


def _serialize(user):
    return {
        **_user_schema.dump(user),
        "profile": _profile_schema.dump(user.customer) if user.customer else None,
    }


@users_bp.get("")
@roles_required(UserRole.ADMIN)
def list_users():
    """Admin view of every account - the user-management screen."""
    users = db.session.scalars(db.select(User).order_by(User.created_at)).all()
    return {"users": [_user_schema.dump(user) for user in users]}


@users_bp.get("/me")
@jwt_required()
def get_me():
    return {"user": _serialize(require_user())}


@users_bp.put("/me")
@jwt_required()
def update_me():
    user = require_user()
    data = _profile_update_schema.load(request.get_json(silent=True) or {}, partial=True)

    if not data:
        raise ApiError("No fields to update.", 400)

    return {"user": _serialize(auth_service.update_profile(user=user, data=data))}
