"""Seed script tests.

The seed must be safely re-runnable - it is what a fresh checkout runs to get a
working demo.
"""

from app.extensions import db
from app.models import (
    ApplicationStatus,
    Customer,
    LoanApplication,
    LoanProduct,
    User,
    UserRole,
)
from app.utils.security import verify_password
from app.utils.seed import DEMO_PASSWORD, seed_database

EXPECTED = {"products": 3, "users": 5, "customers": 3, "applications": 3}
EMPTY = {"products": 0, "users": 0, "customers": 0, "applications": 0}


def test_seed_creates_the_demo_dataset(app):
    assert seed_database() == EXPECTED


def test_seed_is_idempotent(app):
    seed_database()

    assert seed_database() == EMPTY

    assert db.session.scalar(db.select(db.func.count(LoanProduct.id))) == 3
    assert db.session.scalar(db.select(db.func.count(User.id))) == 5
    assert db.session.scalar(db.select(db.func.count(Customer.id))) == 3
    assert db.session.scalar(db.select(db.func.count(LoanApplication.id))) == 3


def test_seeded_accounts_share_the_demo_password(app):
    seed_database()

    customer = db.session.scalar(
        db.select(User).where(User.email == "rahul.kumar@example.test")
    )
    assert verify_password(DEMO_PASSWORD, customer.password_hash) is True
    assert verify_password("not-the-password", customer.password_hash) is False


def test_seeded_roles_are_one_admin_one_officer_three_customers(app):
    seed_database()

    roles = db.session.scalars(db.select(User.role)).all()
    assert roles.count(UserRole.ADMIN) == 1
    assert roles.count(UserRole.LOAN_OFFICER) == 1
    assert roles.count(UserRole.CUSTOMER) == 3


def test_seeded_applications_are_reviewable(app):
    """The officer queue needs submitted applications with financial details."""
    seed_database()

    applications = db.session.scalars(db.select(LoanApplication)).all()

    assert len(applications) == 3
    assert {application.status for application in applications} == {
        ApplicationStatus.SUBMITTED
    }
    for application in applications:
        assert application.application_no.startswith("LN-")
        assert application.financial_details is not None
        # Ownership chain the API will walk: application -> customer -> user
        assert application.customer.user.role is UserRole.CUSTOMER
        assert application.product.active is True


def test_seeded_amounts_fit_their_product_limits(app):
    """Seed data must satisfy the product rules the submit endpoint enforces."""
    seed_database()

    for application in db.session.scalars(db.select(LoanApplication)).all():
        product = application.product
        assert product.min_amount <= application.amount <= product.max_amount
        assert product.min_tenure <= application.tenure <= product.max_tenure
        assert application.financial_details.monthly_income >= product.min_income
