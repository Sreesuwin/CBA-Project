"""Human-readable identifier generation.

Application numbers are always produced here, never accepted from a client.
"""

from datetime import date

from flask import current_app

from ..extensions import db
from ..models import LoanApplication


def next_application_no(prefix: str = None, year: int = None) -> str:
    """Return the next free application number, e.g. ``LN-2026-0004``.

    The sequence is derived from the highest existing number for the year, which
    is fine for a single-instance student project. A production system would use
    a database sequence to avoid races between concurrent submissions.
    """
    prefix = prefix or current_app.config.get("APPLICATION_NO_PREFIX", "LN")
    year = year or date.today().year
    stem = f"{prefix}-{year}-"

    latest = db.session.scalar(
        db.select(db.func.max(LoanApplication.application_no)).where(
            LoanApplication.application_no.like(f"{stem}%")
        )
    )

    sequence = 1
    if latest:
        try:
            sequence = int(str(latest).rsplit("-", 1)[-1]) + 1
        except ValueError:
            sequence = 1

    return f"{stem}{sequence:04d}"
