"""Application factory.

    from app import create_app
    app = create_app()

Kept as a factory (rather than a module-level app) so tests can build an app
against an in-memory database with a different config object.
"""

import os

from flask import Flask
from flask_cors import CORS

from .cli import register_cli
from .config import Config
from .extensions import db, jwt
from .routes import register_blueprints
from .utils.errors import register_error_handlers
from .utils.mongo import init_mongo


def create_app(config_object=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_object or Config)

    # Holds the default SQLite file and any other instance-local state.
    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    jwt.init_app(app)

    CORS(app, resources={r"/api/*": {"origins": app.config["FRONTEND_ORIGIN"]}})
    init_mongo(app)

    register_error_handlers(app)
    register_blueprints(app)
    register_cli(app)

    # Imported for the side effect of registering tables on db.metadata.
    from . import models  # noqa: F401

    return app
