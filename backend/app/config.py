"""Application configuration.

Everything environment-specific lives here so that moving from the dummy
SQLite database to the real MySQL schema is a change to ``DATABASE_URL`` only.
"""

import os
from datetime import timedelta

from dotenv import load_dotenv
from sqlalchemy.pool import StaticPool

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
load_dotenv(os.path.join(BASE_DIR, ".env"))


def _normalize_db_url(url: str) -> str:
    """Add the driver to shorthand URLs so SQLAlchemy knows what to load.

    A bare ``mysql://`` URL defaults to MySQLdb, which we do not install.
    """
    if url.startswith("mysql://"):
        return url.replace("mysql://", "mysql+pymysql://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg2://", 1)
    return url


class Config:
    ENV = os.getenv("FLASK_ENV", "development")
    DEBUG = ENV == "development"

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-secret-change-me")
    # Keep these at 32+ bytes: PyJWT warns below that for HS256.
    JWT_SECRET_KEY = os.getenv(
        "JWT_SECRET_KEY", "dev-only-jwt-secret-change-me-not-for-production"
    )
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        minutes=int(os.getenv("JWT_ACCESS_TOKEN_MINUTES", "60"))
    )

    # bcrypt cost factor. Each hash records the cost it was created with, so
    # raising this later still verifies existing passwords.
    BCRYPT_ROUNDS = int(os.getenv("BCRYPT_ROUNDS", "12"))

    # --- Database -----------------------------------------------------------
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///loan_platform.db")
    SQLALCHEMY_DATABASE_URI = _normalize_db_url(DATABASE_URL)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    # --- MongoDB ------------------------------------------------------------
    # An empty MONGO_URI disables MongoDB entirely (writes become no-ops).
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
    MONGO_DB = os.getenv("MONGO_DB", "loan_platform")
    MONGO_TIMEOUT_MS = int(os.getenv("MONGO_TIMEOUT_MS", "2000"))

    # --- Misc ---------------------------------------------------------------
    FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
    # Application numbers look like LN-2026-0001
    APPLICATION_NO_PREFIX = os.getenv("APPLICATION_NO_PREFIX", "LN")
    JSON_SORT_KEYS = False


class TestingConfig(Config):
    TESTING = True
    ENV = "testing"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    # StaticPool keeps the whole test suite on one in-memory SQLite connection;
    # otherwise every new connection would get its own empty database.
    SQLALCHEMY_ENGINE_OPTIONS = {
        "poolclass": StaticPool,
        "connect_args": {"check_same_thread": False},
    }
    MONGO_URI = None
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=5)
    # Set explicitly rather than inherited from .env, so the suite never depends
    # on (or warns about) a local secret file.
    SECRET_KEY = "testing-secret-key-of-at-least-32-bytes-long"
    JWT_SECRET_KEY = "testing-jwt-secret-key-of-at-least-32-bytes-long"
    # The minimum bcrypt accepts. Keeps the suite fast - hundreds of logins at
    # production cost would dominate the runtime.
    BCRYPT_ROUNDS = 4
