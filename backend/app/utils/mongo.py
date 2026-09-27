"""MongoDB access for document metadata and audit logs.

MongoDB is deliberately optional. With no ``MONGO_URI`` configured the accessors
return ``None`` and callers treat the write as a no-op, so the core API stays
runnable and testable on a machine that has no MongoDB running.
"""

from flask import current_app
from pymongo import MongoClient
from pymongo.errors import PyMongoError

DOCUMENTS_COLLECTION = "documents"
AUDIT_LOGS_COLLECTION = "audit_logs"

_client = None


def init_mongo(app):
    """Create the client for this app. Never raises - MongoDB is not critical."""
    global _client
    uri = app.config.get("MONGO_URI")
    if not uri:
        _client = None
        return None

    try:
        # MongoClient connects lazily, so this does not require a running server.
        # The timeout stops /api/health/ready from hanging when Mongo is down.
        _client = MongoClient(
            uri, serverSelectionTimeoutMS=app.config.get("MONGO_TIMEOUT_MS", 2000)
        )
    except (PyMongoError, ValueError) as exc:
        app.logger.warning("MongoDB disabled: %s", exc)
        _client = None
    return _client


def get_client():
    return _client


def get_db():
    """The application database, or ``None`` when MongoDB is disabled."""
    if _client is None:
        return None
    return _client[current_app.config["MONGO_DB"]]


def get_collection(name):
    """A collection handle, or ``None`` when MongoDB is disabled."""
    database = get_db()
    return None if database is None else database[name]


def documents():
    return get_collection(DOCUMENTS_COLLECTION)


def audit_logs():
    return get_collection(AUDIT_LOGS_COLLECTION)


def ping():
    """Connection status for the readiness endpoint."""
    if _client is None:
        return {"configured": False, "connected": False}
    try:
        _client.admin.command("ping")
        return {"configured": True, "connected": True}
    except PyMongoError as exc:
        return {"configured": True, "connected": False, "error": str(exc)}


def reset():
    """Close and forget the cached client (used between tests)."""
    global _client
    if _client is not None:
        _client.close()
    _client = None
