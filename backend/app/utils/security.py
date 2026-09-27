"""Password hashing.

Passwords are always stored as a bcrypt hash - never plain text, never a plain
digest (see the security section of the project doc).
"""

import bcrypt

# bcrypt silently truncates beyond 72 bytes, so the API layer rejects longer
# passwords rather than letting two different passwords hash to the same value.
MAX_PASSWORD_BYTES = 72

# Cost factor. Each stored hash records the cost it was built with, so this can
# be raised later without invalidating existing passwords.
DEFAULT_ROUNDS = 12


def _configured_rounds() -> int:
    """Read the cost factor from app config, tolerating no app context."""
    try:
        from flask import current_app

        return int(current_app.config.get("BCRYPT_ROUNDS", DEFAULT_ROUNDS))
    except (ImportError, RuntimeError):
        # CLI or script use - fall back to the secure default.
        return DEFAULT_ROUNDS


def hash_password(plain: str, rounds: int | None = None) -> str:
    """Return a salted bcrypt hash suitable for ``users.password_hash``."""
    if not isinstance(plain, str) or not plain:
        raise ValueError("Password must be a non-empty string.")
    encoded = plain.encode("utf-8")
    if len(encoded) > MAX_PASSWORD_BYTES:
        raise ValueError(f"Password must be at most {MAX_PASSWORD_BYTES} bytes.")
    rounds = rounds or _configured_rounds()
    return bcrypt.hashpw(encoded, bcrypt.gensalt(rounds=rounds)).decode("utf-8")


def verify_password(plain: str, password_hash: str) -> bool:
    """Constant-time check of a candidate password against a stored hash."""
    if not plain or not password_hash:
        return False
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        # Malformed hash (e.g. hand-edited row) - treat as a failed login.
        return False
