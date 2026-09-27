"""Model layer tests.

These guard the guarantees the rest of the backend will rely on once the real
MySQL schema is plugged in: foreign keys are enforced, enums round-trip, and
cascades behave.
"""

from datetime import timedelta
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import (
    ApplicationStatus,
    CreditAssessment,
    DecisionType,
    Customer,
    FinancialDetails,
    LoanApplication,
    LoanDecision,
    LoanProduct,
    Recommendation,
    RiskLevel,
    User,
    UserRole,
)
from app.utils.security import hash_password, verify_password
from app.utils.time import utcnow

# --- helpers ---------------------------------------------------------------


def make_user(email="user@example.test", role=UserRole.CUSTOMER):
    user = User(
        name="Test User",
        email=email,
        password_hash=hash_password("Secret@123"),
        role=role,
    )
    db.session.add(user)
    db.session.flush()
    return user


def make_product(name="Test Product"):
    product = LoanProduct(
        name=name,
        min_amount=Decimal("50000.00"),
        max_amount=Decimal("1000000.00"),
        interest_rate=Decimal("11.50"),
        min_tenure=12,
        max_tenure=60,
        min_income=Decimal("25000.00"),
    )
    db.session.add(product)
    db.session.flush()
    return product


def make_customer(email="customer@example.test"):
    user = make_user(email=email)
    customer = Customer(user_id=user.id, phone="9876500000", employment_type="SALARIED")
    db.session.add(customer)
    db.session.flush()
    return customer


def make_application(customer, product, application_no="LN-2026-0001"):
    application = LoanApplication(
        application_no=application_no,
        customer_id=customer.id,
        product_id=product.id,
        amount=Decimal("500000.00"),
        tenure=48,
        purpose="Test purpose",
    )
    db.session.add(application)
    db.session.flush()
    return application


# --- users -----------------------------------------------------------------


def test_user_defaults_and_enum_roundtrip(app):
    make_user()
    db.session.commit()

    stored = db.session.scalar(db.select(User).where(User.email == "user@example.test"))
    assert stored.role is UserRole.CUSTOMER
    assert stored.is_active is True
    assert stored.created_at is not None
    assert len(stored.password_hash) == 60  # bcrypt output


def test_duplicate_email_is_rejected(app):
    make_user(email="duplicate@example.test")

    with pytest.raises(IntegrityError):
        make_user(email="duplicate@example.test")
    db.session.rollback()


def test_customer_profile_is_one_to_one(app):
    customer = make_customer()

    db.session.add(Customer(user_id=customer.user_id))
    with pytest.raises(IntegrityError):
        db.session.flush()
    db.session.rollback()


def test_missing_user_foreign_key_is_rejected(app):
    """Proves the SQLite FK pragma in extensions.py is active.

    Without it this insert would silently succeed and we would only discover the
    orphan once the real MySQL schema is in place.
    """
    db.session.add(Customer(user_id=999999))

    with pytest.raises(IntegrityError):
        db.session.flush()
    db.session.rollback()


# --- applications ----------------------------------------------------------


def test_application_defaults_to_draft(app):
    application = make_application(make_customer(), make_product())
    db.session.commit()

    stored = db.session.get(LoanApplication, application.id)
    assert stored.status is ApplicationStatus.DRAFT
    assert stored.submitted_at is None
    assert stored.created_at is not None
    assert stored.updated_at is not None


def test_application_number_is_unique(app):
    customer = make_customer()
    product = make_product()
    make_application(customer, product, application_no="LN-2026-0007")

    with pytest.raises(IntegrityError):
        make_application(customer, product, application_no="LN-2026-0007")
    db.session.rollback()


def test_amount_is_stored_as_decimal(app):
    application = make_application(make_customer(), make_product())
    application.amount = Decimal("123456.78")
    db.session.commit()
    db.session.expire_all()

    stored = db.session.get(LoanApplication, application.id)
    assert stored.amount == Decimal("123456.78")


def test_deleting_application_cascades_to_financial_details(app):
    application = make_application(make_customer(), make_product())
    application.financial_details = FinancialDetails(
        monthly_income=Decimal("65000.00"),
        monthly_expenses=Decimal("26000.00"),
        existing_emi=Decimal("8000.00"),
        existing_loans=1,
        employment_years=4,
    )
    db.session.commit()
    application_id = application.id

    db.session.delete(application)
    db.session.commit()

    remaining = db.session.scalar(
        db.select(db.func.count(FinancialDetails.id)).where(
            FinancialDetails.application_id == application_id
        )
    )
    assert remaining == 0


def test_application_keeps_assessment_and_decision_history(app):
    application = make_application(make_customer(), make_product())
    officer = make_user(email="officer@example.test", role=UserRole.LOAN_OFFICER)

    first = CreditAssessment(
        application_id=application.id,
        score=560,
        risk_level=RiskLevel.HIGH,
        recommendation=Recommendation.MANUAL_REVIEW,
        # Deliberately earlier so the ordering assertion is deterministic.
        assessed_at=utcnow() - timedelta(minutes=10),
    )
    first.reasons = ["Stable income", "High existing EMI burden"]
    second = CreditAssessment(
        application_id=application.id,
        score=680,
        risk_level=RiskLevel.MODERATE,
        recommendation=Recommendation.ELIGIBLE,
        assessed_by_id=officer.id,
    )
    second.reasons = ["Low existing EMI burden"]

    db.session.add_all(
        [
            first,
            second,
            LoanDecision(
                application_id=application.id,
                officer_id=officer.id,
                decision=DecisionType.APPROVE,
                remarks="Approved after document review.",
            ),
        ]
    )
    db.session.commit()
    db.session.expire_all()

    stored = db.session.get(LoanApplication, application.id)
    assert len(stored.assessments) == 2
    assert stored.latest_assessment.score == 680
    assert stored.assessments[-1].reasons == ["Low existing EMI burden"]
    assert first.reasons == ["Stable income", "High existing EMI burden"]
    assert stored.decisions[0].officer.role is UserRole.LOAN_OFFICER


# --- security helpers ------------------------------------------------------


def test_password_hash_roundtrip(app):
    hashed = hash_password("Secret@123")

    assert hashed != "Secret@123"
    assert verify_password("Secret@123", hashed) is True
    assert verify_password("wrong-password", hashed) is False


def test_verify_password_tolerates_malformed_hash(app):
    assert verify_password("Secret@123", "not-a-bcrypt-hash") is False
