"""Append-only audit trail.

Every significant application event (created, updated, submitted, assessed,
decided, documents changed) is recorded here. The collection is write-mostly:
entries are never edited or deleted, so the history of an application can be
reconstructed even after its status has changed many times.

The store falls back to an in-memory collection when MongoDB is unavailable, so
auditing never breaks the request it is describing.
"""

from ..utils import store

# Canonical action names. Keeping them here means the frontend and the tests
# refer to the same vocabulary instead of retyping strings.
ACTION_CREATED = "APPLICATION_CREATED"
ACTION_UPDATED = "APPLICATION_UPDATED"
ACTION_SUBMITTED = "APPLICATION_SUBMITTED"
ACTION_ASSESSED = "CREDIT_ASSESSED"
ACTION_DECISION = "DECISION_RECORDED"
ACTION_DOCUMENT = "DOCUMENT_ADDED"


def record(application_id, actor_id, action, metadata=None, timestamp=None) -> dict:
    """Append one audit entry. Returns the stored document.

    ``timestamp`` is injectable so tests can assert on an exact value rather
    than on "something close to now".
    """
    entry = {
        "application_id": int(application_id),
        "actor_id": int(actor_id) if actor_id is not None else None,
        "action": action,
        "metadata": metadata or {},
        "timestamp": timestamp or _now_iso(),
    }
    return store.audit_logs().insert_one(entry)


def list_for(application_id):
    """Audit entries for one application, oldest first."""
    entries = list(store.audit_logs().find({"application_id": int(application_id)}))
    entries.sort(key=lambda item: item.get("timestamp") or "")
    return entries


def list_all(limit=200):
    """Every audit entry, newest first - the admin activity screen."""
    entries = list(store.audit_logs().find({}))
    entries.sort(key=lambda item: item.get("timestamp") or "", reverse=True)
    return entries[:limit]


def serialize(entry):
    """Convert a stored entry into a JSON-safe dict."""
    return {
        "id": str(entry.get("_id")) if entry.get("_id") is not None else None,
        "application_id": entry.get("application_id"),
        "actor_id": entry.get("actor_id"),
        "action": entry.get("action"),
        "metadata": entry.get("metadata") or {},
        "timestamp": entry.get("timestamp"),
    }


def _now_iso() -> str:
    from ..utils.time import utcnow

    return utcnow().isoformat() + "Z"
