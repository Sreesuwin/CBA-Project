"""Authentication endpoints.

    POST /api/auth/register         create a CUSTOMER account, return a token
    POST /api/auth/login            exchange credentials for a token
    POST /api/auth/change-password  rotate the caller's own password

There is deliberately no /logout: a JWT is valid until it expires, and without a
token blocklist a logout endpoint would be a lie. The client drops the token.
"""

from flask import Blueprint, current_app, request
from flask_jwt_extended import create_access_token, jwt_required

from ..middleware.auth import require_user
from ..schemas import ChangePasswordSchema, LoginSchema, RegisterSchema, UserSchema
from ..services import auth_service

auth_bp = Blueprint("auth", __name__)

_register_schema = RegisterSchema()
_login_schema = LoginSchema()
_change_password_schema = ChangePasswordSchema()
_user_schema = UserSchema()


def issue_token(user):
    """Build the login response. ``sub`` must be a string in flask-jwt-extended."""
    token = create_access_token(identity=str(user.id))
    expires = current_app.config["JWT_ACCESS_TOKEN_EXPIRES"]
    return {
        "access_token": token,
        "token_type": "Bearer",
        "expires_in": int(expires.total_seconds()),
        "user": _user_schema.dump(user),
    }


def _body():
    return request.get_json(silent=True) or {}


@auth_bp.post("/register")
def register():
    data = _register_schema.load(_body())
    user = auth_service.register_customer(**data)
    return issue_token(user), 201


@auth_bp.post("/login")
def login():
    data = _login_schema.load(_body())
    user = auth_service.authenticate(**data)
    return issue_token(user), 200


@auth_bp.post("/change-password")
@jwt_required()
def change_password():
    data = _change_password_schema.load(_body())
    auth_service.change_password(user=require_user(), **data)
    return {"message": "Password updated."}
