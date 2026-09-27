"""Small factories shared by the endpoint tests.

Kept out of conftest so a test can import exactly what it needs without pulling
in pytest fixtures it does not use.
"""

import itertools

from flask_jwt_extended import create_access_token

from app.extensions import db
from app.models import User, UserRole
from app.utils.security import hash_password

PASSWORD = "Secret@123"

# A test that needs two staff accounts would otherwise collide on the default
# email and trip the unique index.
_counter = itertools.count(1)


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def token_for(user):
    return create_access_token(identity=str(user.id))


def make_user(role, email, name="Staff User", is_active=True):
    """Insert an account directly. Only admins create staff through the API."""
    user = User(
        name=name,
        email=email,
        password_hash=hash_password(PASSWORD),
        role=role,
        is_active=is_active,
    )
    db.session.add(user)
    db.session.commit()
    return user


def register(client, email="customer@example.test", name="Test Customer", password=PASSWORD):
    response = client.post(
        "/api/auth/register",
        json={"name": name, "email": email, "password": password},
    )
    assert response.status_code == 201, response.get_json()
    return response.get_json()["access_token"]


def customer_headers(client, email=None):
    email = email or f"customer{next(_counter)}@example.test"
    return bearer(register(client, email=email))


def officer_headers(email=None):
    email = email or f"officer{next(_counter)}@example.test"
    return bearer(token_for(make_user(UserRole.LOAN_OFFICER, email, name="Officer")))


def admin_headers(email=None):
    email = email or f"admin{next(_counter)}@example.test"
    return bearer(token_for(make_user(UserRole.ADMIN, email, name="Admin")))
