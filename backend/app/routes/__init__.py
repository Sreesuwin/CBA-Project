"""API blueprints.

Every blueprint is registered in one place so the URL map stays easy to audit.
"""

from .applications import applications_bp
from .audit import audit_bp
from .auth import auth_bp
from .health import health_bp
from .loan_products import loan_products_bp
from .users import users_bp


def register_blueprints(app):
    app.register_blueprint(health_bp, url_prefix="/api/health")
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(users_bp, url_prefix="/api/users")
    app.register_blueprint(loan_products_bp, url_prefix="/api/loan-products")
    app.register_blueprint(applications_bp, url_prefix="/api/applications")
    app.register_blueprint(audit_bp, url_prefix="/api/audit")
