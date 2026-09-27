"""Authentication, JWT and role authorization tests.

Covers the security requirements in the project doc: generic authentication
errors, no self-assigned roles, no password hash in responses, and role checks
that actually fail closed.
"""

from datetime import timedelta

import pytest
from flask_jwt_extended import create_access_token

from app.extensions import db
from app.middleware.auth import roles_required
from app.models import Customer, User, UserRole
from app.utils.security import hash_password

STRONG_PASSWORD = "Secret@123"

# --- helpers ---------------------------------------------------------------


def register(client, email="new.user@example.test", password=STRONG_PASSWORD, **extra):
    payload = {"name": "New User", "email": email, "password": password, **extra}
    return client.post("/api/auth/register", json=payload)


def login(client, email="new.user@example.test", password=STRONG_PASSWORD):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def register_and_token(client, email="new.user@example.test"):
    return register(client, email=email).get_json()["access_token"]


def make_user(role, email="staff@example.test", is_active=True):
    """Insert a staff account directly - only admins create these in the app."""
    user = User(
        name="Staff User",
        email=email,
        password_hash=hash_password(STRONG_PASSWORD),
        role=role,
        is_active=is_active,
    )
    db.session.add(user)
    db.session.commit()
    return user


def token_for(user):
    return create_access_token(identity=str(user.id))


def probe(*roles):
    """A view guarded by roles_required, for testing the decorator itself."""

    @roles_required(*roles)
    def view():
        return {"ok": True}

    return view


@pytest.fixture()
def role_probes(app):
    """Role-gated routes.

    Real admin-only endpoints arrive in later milestones; these exist so the
    authorization rule can be tested on its own.
    """
    app.add_url_rule(
        "/api/_probe/admin", endpoint="probe_admin", view_func=probe("ADMIN")
    )
    app.add_url_rule(
        "/api/_probe/staff",
        endpoint="probe_staff",
        view_func=probe("LOAN_OFFICER", "ADMIN"),
    )
    return app


# --- registration ----------------------------------------------------------


def test_register_creates_a_customer_and_returns_a_token(app, client):
    response = register(client)

    assert response.status_code == 201
    body = response.get_json()
    assert body["token_type"] == "Bearer"
    assert body["expires_in"] == 300  # TestingConfig: 5 minutes
    assert body["user"]["role"] == "CUSTOMER"
    assert body["user"]["email"] == "new.user@example.test"

    stored = db.session.scalar(db.select(User))
    assert stored.role is UserRole.CUSTOMER
    assert stored.password_hash != STRONG_PASSWORD


def test_register_creates_the_borrower_profile(app, client):
    """Application ownership resolves through customers.user_id, so the profile
    row must exist from the moment the account does."""
    register(client, phone="9876500009")

    profile = db.session.scalar(db.select(Customer))
    assert profile is not None
    assert profile.user_id is not None
    assert profile.phone == "9876500009"


def test_register_normalizes_email_case(app, client):
    response = register(client, email="Mixed.Case@Example.Test")

    assert response.status_code == 201
    assert response.get_json()["user"]["email"] == "mixed.case@example.test"
    assert login(client, email="MIXED.CASE@EXAMPLE.TEST").status_code == 200


def test_duplicate_email_is_rejected(app, client):
    register(client)
    response = register(client)

    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "EMAIL_TAKEN"


def test_duplicate_email_is_case_insensitive(app, client):
    register(client, email="dup@example.test")

    assert register(client, email="DUP@example.test").status_code == 409


def test_register_rejects_a_short_password(client):
    response = register(client, password="Ab1")

    assert response.status_code == 400
    assert "password" in response.get_json()["error"]["details"]


def test_register_rejects_a_password_without_a_digit(client):
    assert register(client, password="OnlyLetters").status_code == 400


def test_register_rejects_an_invalid_email(client):
    assert register(client, email="not-an-email").status_code == 400


def test_register_rejects_a_self_assigned_role(app, client):
    """Privilege escalation: a client must not choose its own role."""
    response = register(client, role="ADMIN")

    assert response.status_code == 400
    assert db.session.scalar(db.select(db.func.count(User.id))) == 0


def test_register_requires_a_body(client):
    assert client.post("/api/auth/register", json={}).status_code == 400


# --- login -----------------------------------------------------------------


def test_login_returns_a_working_token(app, client):
    register(client)
    token = login(client).get_json()["access_token"]

    me = client.get("/api/users/me", headers=bearer(token))
    assert me.status_code == 200
    assert me.get_json()["user"]["email"] == "new.user@example.test"


def test_login_with_a_wrong_password_is_generic(client):
    register(client)
    response = login(client, password="Wrong@123")

    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "INVALID_CREDENTIALS"
    assert "access_token" not in response.get_json()


def test_unknown_email_and_wrong_password_are_indistinguishable(client):
    register(client)

    wrong_password = login(client, password="Wrong@123")
    unknown_email = login(client, email="nobody@example.test")

    assert wrong_password.status_code == 401
    assert unknown_email.status_code == 401
    # Identical bodies: the API never reveals whether an account exists.
    assert wrong_password.get_json() == unknown_email.get_json()


def test_an_inactive_account_cannot_log_in(app, client):
    user = make_user(UserRole.CUSTOMER, email="disabled@example.test", is_active=False)

    assert login(client, email=user.email).status_code == 401


# --- token handling --------------------------------------------------------


def test_me_requires_a_token(client):
    response = client.get("/api/users/me")

    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "UNAUTHENTICATED"


def test_me_rejects_a_malformed_token(client):
    response = client.get("/api/users/me", headers=bearer("not-a-real-token"))

    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "INVALID_TOKEN"


def test_an_expired_token_is_reported_as_such(app, client):
    user = make_user(UserRole.CUSTOMER)
    expired = create_access_token(
        identity=str(user.id), expires_delta=timedelta(seconds=-1)
    )

    response = client.get("/api/users/me", headers=bearer(expired))

    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "TOKEN_EXPIRED"


def test_a_token_for_a_deleted_user_is_rejected(app, client):
    user = make_user(UserRole.CUSTOMER)
    token = token_for(user)

    db.session.delete(user)
    db.session.commit()

    assert client.get("/api/users/me", headers=bearer(token)).status_code == 401


def test_deactivating_an_account_invalidates_its_existing_token(app, client):
    user = make_user(UserRole.CUSTOMER)
    token = token_for(user)
    assert client.get("/api/users/me", headers=bearer(token)).status_code == 200

    user.is_active = False
    db.session.commit()

    # is_active is re-read from the database rather than trusted from the token.
    assert client.get("/api/users/me", headers=bearer(token)).status_code == 401


def test_me_never_exposes_the_password_hash(client):
    token = register_and_token(client)
    body = client.get("/api/users/me", headers=bearer(token)).get_json()

    assert "password_hash" not in str(body)


# --- role authorization ----------------------------------------------------


def test_roles_required_blocks_a_customer(role_probes, client):
    token = register_and_token(client)
    response = client.get("/api/_probe/admin", headers=bearer(token))

    assert response.status_code == 403
    assert response.get_json()["error"]["code"] == "FORBIDDEN"


def test_roles_required_allows_the_matching_role(role_probes, client):
    admin = make_user(UserRole.ADMIN, email="admin@example.test")

    assert client.get("/api/_probe/admin", headers=bearer(token_for(admin))).status_code == 200


def test_roles_required_accepts_any_listed_role(role_probes, client):
    officer = make_user(UserRole.LOAN_OFFICER)
    token = token_for(officer)

    assert client.get("/api/_probe/staff", headers=bearer(token)).status_code == 200
    assert client.get("/api/_probe/admin", headers=bearer(token)).status_code == 403


def test_roles_required_still_requires_authentication(role_probes, client):
    response = client.get("/api/_probe/admin")

    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "UNAUTHENTICATED"


# --- password change -------------------------------------------------------


def change_password(client, token, current, new):
    return client.post(
        "/api/auth/change-password",
        headers=bearer(token),
        json={"current_password": current, "new_password": new},
    )


def test_change_password_rotates_the_credential(client):
    token = register_and_token(client)

    assert change_password(client, token, STRONG_PASSWORD, "NewSecret@456").status_code == 200
    assert login(client).status_code == 401
    assert login(client, password="NewSecret@456").status_code == 200


def test_change_password_requires_the_current_password(client):
    token = register_and_token(client)

    assert change_password(client, token, "Wrong@123", "NewSecret@456").status_code == 401
    assert login(client).status_code == 200  # unchanged


def test_change_password_rejects_reusing_the_same_password(client):
    token = register_and_token(client)

    response = change_password(client, token, STRONG_PASSWORD, STRONG_PASSWORD)
    assert response.status_code == 400


def test_change_password_enforces_complexity(client):
    token = register_and_token(client)

    assert change_password(client, token, STRONG_PASSWORD, "short").status_code == 400


def test_change_password_requires_authentication(client):
    response = client.post(
        "/api/auth/change-password",
        json={"current_password": STRONG_PASSWORD, "new_password": "NewSecret@456"},
    )

    assert response.status_code == 401


# --- profile management ----------------------------------------------------


def test_update_profile_changes_name_and_profile(app, client):
    token = register_and_token(client)

    response = client.put(
        "/api/users/me",
        headers=bearer(token),
        json={
            "name": "Renamed User",
            "phone": "9876500001",
            "employment_type": "SALARIED",
            "dob": "1994-03-12",
        },
    )

    assert response.status_code == 200
    body = response.get_json()["user"]
    assert body["name"] == "Renamed User"
    assert body["profile"]["phone"] == "9876500001"
    assert body["profile"]["employment_type"] == "SALARIED"
    assert body["profile"]["dob"] == "1994-03-12"


def test_update_profile_rejects_an_unknown_employment_type(client):
    token = register_and_token(client)

    response = client.put(
        "/api/users/me", headers=bearer(token), json={"employment_type": "ASTRONAUT"}
    )

    assert response.status_code == 400


def test_update_profile_rejects_an_empty_payload(client):
    token = register_and_token(client)

    assert client.put("/api/users/me", headers=bearer(token), json={}).status_code == 400


def test_update_profile_cannot_change_role_or_email(app, client):
    token = register_and_token(client)

    response = client.put(
        "/api/users/me", headers=bearer(token), json={"role": "ADMIN"}
    )

    assert response.status_code == 400  # unknown field, rejected outright
    stored = db.session.scalar(
        db.select(User).where(User.email == "new.user@example.test")
    )
    assert stored.role is UserRole.CUSTOMER
