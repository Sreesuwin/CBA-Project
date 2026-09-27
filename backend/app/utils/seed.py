"""Seed the dummy database with demo data.

Idempotent: running it twice inserts nothing the second time, so it is safe to
run on every checkout. Pass ``reset=True`` (``flask seed-db --reset``) to drop
and rebuild the tables first.

All data here is fictional. Never seed real personal or financial information.
"""

from decimal import Decimal

from ..extensions import db
from ..models import (
    ApplicationStatus,
    Customer,
    FinancialDetails,
    LoanApplication,
    LoanProduct,
    User,
    UserRole,
)
from .ids import next_application_no
from .security import hash_password
from .time import utcnow

# Every seeded account shares this password so the demo is easy to drive.
DEMO_PASSWORD = "Password@123"

PRODUCTS = [
    {
        "name": "Personal Loan",
        "min_amount": Decimal("50000.00"),
        "max_amount": Decimal("1000000.00"),
        "interest_rate": Decimal("11.50"),
        "min_tenure": 12,
        "max_tenure": 60,
        "min_income": Decimal("25000.00"),
    },
    {
        "name": "Vehicle Loan",
        "min_amount": Decimal("100000.00"),
        "max_amount": Decimal("2000000.00"),
        "interest_rate": Decimal("9.25"),
        "min_tenure": 12,
        "max_tenure": 84,
        "min_income": Decimal("30000.00"),
    },
    {
        "name": "Home Loan",
        "min_amount": Decimal("500000.00"),
        "max_amount": Decimal("10000000.00"),
        "interest_rate": Decimal("8.50"),
        "min_tenure": 60,
        "max_tenure": 360,
        "min_income": Decimal("40000.00"),
    },
]

# Demo applicants mirror the sample data in the project doc: the three of them
# produce low, moderate and high risk so the officer queue has variety.
DEMO_USERS = [
    {
        "name": "Priya Menon",
        "email": "admin@loanplatform.test",
        "role": UserRole.ADMIN,
    },
    {
        "name": "Vikram Desai",
        "email": "officer@loanplatform.test",
        "role": UserRole.LOAN_OFFICER,
    },
    {
        "name": "Rahul Kumar",
        "email": "rahul.kumar@example.test",
        "role": UserRole.CUSTOMER,
        "customer": {
            "phone": "9876500001",
            "address": "12 MG Road, Bengaluru",
            "employment_type": "SALARIED",
        },
        "application": {
            "product": "Personal Loan",
            "amount": "500000.00",
            "tenure": 48,
            "purpose": "Home renovation",
            "financials": {
                "monthly_income": "65000.00",
                "monthly_expenses": "26000.00",
                "existing_emi": "8000.00",
                "existing_loans": 1,
                "employment_years": 4,
            },
        },
    },
    {
        "name": "Ananya Rao",
        "email": "ananya.rao@example.test",
        "role": UserRole.CUSTOMER,
        "customer": {
            "phone": "9876500002",
            "address": "48 Indiranagar, Bengaluru",
            "employment_type": "SALARIED",
        },
        "application": {
            "product": "Vehicle Loan",
            "amount": "800000.00",
            "tenure": 60,
            "purpose": "New car purchase",
            "financials": {
                "monthly_income": "90000.00",
                "monthly_expenses": "40000.00",
                "existing_emi": "12000.00",
                "existing_loans": 0,
                "employment_years": 7,
            },
        },
    },
    {
        "name": "Arjun Singh",
        "email": "arjun.singh@example.test",
        "role": UserRole.CUSTOMER,
        "customer": {
            "phone": "9876500003",
            "address": "9 Sector 21, Noida",
            "employment_type": "SELF_EMPLOYED",
        },
        "application": {
            "product": "Personal Loan",
            "amount": "200000.00",
            "tenure": 36,
            "purpose": "Debt consolidation",
            "financials": {
                "monthly_income": "28000.00",
                "monthly_expenses": "18000.00",
                "existing_emi": "14000.00",
                "existing_loans": 3,
                "employment_years": 1,
            },
        },
    },
]


def seed_database(reset: bool = False) -> dict:
    """Insert the demo dataset. Returns a count of what was actually created."""
    if reset:
        db.drop_all()
        db.create_all()

    stats = {"products": 0, "users": 0, "customers": 0, "applications": 0}
    products = _seed_products(stats)
    _seed_people(stats, products)
    db.session.commit()
    return stats


def _seed_products(stats):
    products = {}
    for row in PRODUCTS:
        product = db.session.scalar(
            db.select(LoanProduct).where(LoanProduct.name == row["name"])
        )
        if product is None:
            product = LoanProduct(**row)
            db.session.add(product)
            db.session.flush()
            stats["products"] += 1
        products[row["name"]] = product
    return products


def _seed_people(stats, products):
    # bcrypt is intentionally slow, so hash the shared demo password once.
    password_hash = hash_password(DEMO_PASSWORD)

    for row in DEMO_USERS:
        user = db.session.scalar(db.select(User).where(User.email == row["email"]))
        if user is None:
            user = User(
                name=row["name"],
                email=row["email"],
                password_hash=password_hash,
                role=row["role"],
            )
            db.session.add(user)
            db.session.flush()
            stats["users"] += 1

        profile = row.get("customer")
        if not profile:
            continue

        customer = db.session.scalar(
            db.select(Customer).where(Customer.user_id == user.id)
        )
        if customer is None:
            customer = Customer(user_id=user.id, **profile)
            db.session.add(customer)
            db.session.flush()
            stats["customers"] += 1

        _seed_application(stats, customer, products, row.get("application"))


def _seed_application(stats, customer, products, spec):
    if not spec:
        return

    # Each demo customer owns at most one application, so presence means seeded.
    already_seeded = db.session.scalar(
        db.select(LoanApplication.id)
        .where(LoanApplication.customer_id == customer.id)
        .limit(1)
    )
    if already_seeded:
        return

    financials = spec["financials"]
    application = LoanApplication(
        application_no=next_application_no(),
        customer_id=customer.id,
        product_id=products[spec["product"]].id,
        amount=Decimal(spec["amount"]),
        tenure=spec["tenure"],
        purpose=spec["purpose"],
        status=ApplicationStatus.SUBMITTED,
        submitted_at=utcnow(),
        financial_details=FinancialDetails(
            monthly_income=Decimal(financials["monthly_income"]),
            monthly_expenses=Decimal(financials["monthly_expenses"]),
            existing_emi=Decimal(financials["existing_emi"]),
            existing_loans=financials["existing_loans"],
            employment_years=financials["employment_years"],
        ),
    )
    db.session.add(application)
    db.session.flush()
    stats["applications"] += 1
