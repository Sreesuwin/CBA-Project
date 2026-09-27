"""Registration, login and password management.

All database access for accounts goes through this module so the routes stay
thin and the rules stay testable without an HTTP request.
"""

from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..models import Customer, User, UserRole
from ..utils.errors import ApiError
from ..utils.security import hash_password, verify_password

# Computed once per process and only ever used to burn the same amount of CPU as
# a real password check.
_timing_guard_hash = None


def normalize_email(email: str) -> str:
    """Emails are stored and compared lower-cased and trimmed.

    SQLite compares case-sensitively while MySQL's default collation does not,
    so normalising here keeps the two databases behaving identically.
    """
    return (email or "").strip().lower()


def find_by_email(email: str):
    """Case-insensitive lookup, so it behaves the same on every backend."""
    return db.session.scalar(
        db.select(User).where(db.func.lower(User.email) == normalize_email(email))
    )


def register_customer(*, name, email, password, phone=None) -> User:
    """Create a CUSTOMER account with an empty borrower profile."""
    email = normalize_email(email)

    if find_by_email(email):
        raise ApiError(
            "An account with this email already exists.", 409, code="EMAIL_TAKEN"
        )

    try:
        password_hash = hash_password(password)
    except ValueError as exc:  # e.g. a multi-byte password over bcrypt's limit
        raise ApiError(str(exc), 400) from exc

    user = User(
        name=name.strip(),
        email=email,
        password_hash=password_hash,
        # Never taken from the request: self-registration is always a customer.
        role=UserRole.CUSTOMER,
    )
    # Every customer needs a profile row. Application ownership is resolved
    # through customers.user_id, so an account without one could never reach
    # its own applications.
    user.customer = Customer(phone=phone)

    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        # Two concurrent registrations for the same email: the unique index
        # caught what the check above could not.
        db.session.rollback()
        raise ApiError(
            "An account with this email already exists.", 409, code="EMAIL_TAKEN"
        )

    return user


def authenticate(*, email, password) -> User:
    """Return the user for valid credentials, or raise a generic 401."""
    user = find_by_email(email)

    if user is None:
        # Hash anyway, so "no such account" takes about as long as "wrong
        # password" and cannot be distinguished by timing.
        verify_password(password, _timing_guard())
        raise invalid_credentials()

    if not verify_password(password, user.password_hash):
        raise invalid_credentials()

    if not user.is_active:
        # Same error as a wrong password: a disabled account should not be
        # discoverable either.
        raise invalid_credentials()

    return user


def change_password(*, user, current_password, new_password) -> None:
    if not verify_password(current_password, user.password_hash):
        raise ApiError(
            "Current password is incorrect.", 401, code="INVALID_CREDENTIALS"
        )

    if verify_password(new_password, user.password_hash):
        raise ApiError(
            "New password must differ from the current password.", 400
        )

    try:
        user.password_hash = hash_password(new_password)
    except ValueError as exc:
        raise ApiError(str(exc), 400) from exc

    db.session.commit()


def update_profile(*, user, data) -> User:
    """Apply a partial profile update for the signed-in user."""
    if "name" in data:
        user.name = data["name"].strip()

    profile = user.customer
    if profile is None:
        profile = Customer(user_id=user.id)
        db.session.add(profile)
        user.customer = profile

    for field in ("dob", "phone", "address", "employment_type"):
        if field in data:
            setattr(profile, field, data[field])

    db.session.commit()
    return user


def invalid_credentials() -> ApiError:
    """One message for every failure mode.

    Telling the caller which part was wrong would confirm whether an account
    exists (see the security notes in the project doc).
    """
    return ApiError("Invalid email or password.", 401, code="INVALID_CREDENTIALS")


def _timing_guard() -> str:
    global _timing_guard_hash
    if _timing_guard_hash is None:
        _timing_guard_hash = hash_password("timing-guard-placeholder")
    return _timing_guard_hash
