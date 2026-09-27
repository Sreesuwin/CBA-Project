"""Authentication and role-based authorization.

Register this on any route that must not be reachable anonymously, and on any
route restricted to particular roles:

    @jwt_required()
    def view():
        user = require_user()          # the signed-in, active user

    @roles_required(UserRole.ADMIN)
    def admin_view():
        ...
"""

from functools import wraps

from flask import g
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request

from ..extensions import db
from ..models import User, UserRole
from ..utils.errors import ApiError


# Sentinel so "no identity cached yet" is distinguishable from a cached ``None``
# (an anonymous request).
_MISSING = object()


def load_user(identity):
    """Resolve a JWT identity to a user, or None if it no longer exists."""
    try:
        user_id = int(identity)
    except (TypeError, ValueError):
        return None
    return db.session.get(User, user_id)


def current_user():
    """The signed-in user, or None.

    Cached on ``g``, but keyed by the JWT identity. ``g`` lives for the whole
    app context, and a test client (or a server reusing an app context) can
    serve several requests within one context - so an unkeyed cache would return
    the *previous* request's user. Re-loading whenever the identity changes
    keeps the convenience of caching without that leak.
    """
    identity = get_jwt_identity()
    if g.get("current_user_identity", _MISSING) != identity:
        g.current_user = load_user(identity) if identity is not None else None
        g.current_user_identity = identity
    return g.current_user


def require_user() -> User:
    """The signed-in, active user. Raises 401 for anything else."""
    user = current_user()
    # is_active is re-read from the database rather than trusted from the token,
    # so disabling an account takes effect immediately instead of when the
    # token happens to expire.
    if user is None or not user.is_active:
        raise ApiError(
            "Authentication required. Please sign in.", 401, code="UNAUTHENTICATED"
        )
    return user


def roles_required(*roles):
    """Restrict a route to the given roles. Implies authentication.

    Fails closed: a route decorated with no roles is reachable by no one.
    """
    allowed = {
        role if isinstance(role, UserRole) else UserRole(role) for role in roles
    }

    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            user = require_user()
            if user.role not in allowed:
                raise ApiError(
                    "You do not have permission to perform this action.",
                    403,
                    code="FORBIDDEN",
                )
            return view(*args, **kwargs)

        return wrapper

    return decorator


def login_required(view):
    """Require authentication without restricting the role."""

    @wraps(view)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        require_user()
        return view(*args, **kwargs)

    return wrapper
