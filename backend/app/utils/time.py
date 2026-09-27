"""Small time helpers.

Stored timestamps are naive UTC so that SQLite and MySQL agree on what a
``DATETIME`` column contains.
"""

from datetime import datetime, timezone


def utcnow() -> datetime:
    """Current UTC time as a naive datetime."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
