"""Document metadata stored in MongoDB.

Only *metadata* is handled here - what was uploaded and where it stands in the
verification workflow - not the file bytes themselves. Storing binaries is out
of scope for the apprenticeship version; the point being demonstrated is the
flexible-schema store alongside the relational one.

Mirrors the blueprint's shape:

    {"application_id": 1, "files": [
        {"type": "SALARY_SLIP", "filename": "salary.pdf",
         "status": "PENDING", "uploaded_at": "..."}]}
"""

from ..models import DocumentStatus
from ..utils import store

COLLECTION = "documents"


def list_for(application_id):
    """The document record for an application, or an empty files list."""
    document = store.documents().find_one({"application_id": int(application_id)})
    if document is None:
        return {"application_id": int(application_id), "files": []}
    return {
        "application_id": document.get("application_id"),
        "files": document.get("files") or [],
    }


def add_file(application_id, doc_type, filename, status=None):
    """Add one file's metadata, creating the application's record if needed.

    A new file starts ``PENDING``; the verification step (an officer marking it
    accepted/rejected) is a later concern.
    """
    application_id = int(application_id)
    document = store.documents().find_one({"application_id": application_id})
    files = list((document or {}).get("files") or [])

    status_value = status or DocumentStatus.PENDING
    entry = {
        "type": doc_type,
        "filename": filename,
        "status": getattr(status_value, "value", status_value),
        "uploaded_at": _now_iso(),
    }
    files.append(entry)

    store.documents().replace_one(
        {"application_id": application_id},
        {"application_id": application_id, "files": files},
        upsert=True,
    )
    return entry


def _now_iso() -> str:
    from ..utils.time import utcnow

    return utcnow().isoformat() + "Z"
