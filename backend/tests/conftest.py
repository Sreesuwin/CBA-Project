"""Shared pytest fixtures.

Tests run against an in-memory SQLite database created fresh per test, so they
never touch the development database. The document/audit store is likewise reset
between tests so the in-memory fallback cannot leak state across cases.
"""

import pytest

from app import create_app
from app.config import TestingConfig
from app.extensions import db as _db
from app.utils import mongo, store


@pytest.fixture()
def app():
    application = create_app(TestingConfig)
    with application.app_context():
        _db.create_all()
        yield application
        _db.session.remove()
        _db.drop_all()
    store.reset()
    mongo.reset()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def seeded(app):
    """The full demo dataset, as a fresh checkout would have it."""
    from app.utils.seed import seed_database

    seed_database()
    return app
