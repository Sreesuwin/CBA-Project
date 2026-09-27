"""Officer decision tests: approve, reject, request-info and the state machine.

The engine advises; the officer decides. These tests pin the rules that keep
that true: only staff may decide, only a reviewable application may be decided,
and approving seeds a repayment schedule.
"""

from app.extensions import db
from app.models import ApplicationStatus, LoanApplication, Repayment
from tests.factories import admin_headers, customer_headers, officer_headers

FINANCIALS = {
    "monthly_income": "65000.00",
    "monthly_expenses": "26000.00",
    "existing_emi": "8000.00",
    "existing_loans": 1,
    "employment_years": 4,
}


def _product_id(client, name="Personal Loan"):
    products = client.get("/api/loan-products").get_json()["products"]
    return next(p["id"] for p in products if p["name"] == name)


def submitted_application(client, headers):
    """Create and submit one application, returning its id."""
    created = client.post(
        "/api/applications",
        json={
            "product_id": _product_id(client),
            "amount": "500000.00",
            "tenure": 48,
            "purpose": "Home renovation",
            "financials": FINANCIALS,
        },
        headers=headers,
    ).get_json()["application"]
    client.post(f"/api/applications/{created['id']}/submit", headers=headers)
    return created["id"]


# --- approval --------------------------------------------------------------

def test_an_officer_can_approve_a_submitted_application(seeded, client):
    application_id = submitted_application(client, customer_headers(client))

    response = client.post(
        f"/api/applications/{application_id}/approve",
        json={"remarks": "Looks good"},
        headers=officer_headers(),
    )

    assert response.status_code == 200
    assert response.get_json()["application"]["status"] == "APPROVED"
    assert response.get_json()["decision"]["decision"] == "APPROVE"


def test_approval_creates_a_repayment_per_month(seeded, client):
    application_id = submitted_application(client, customer_headers(client))

    client.post(
        f"/api/applications/{application_id}/approve",
        json={},
        headers=officer_headers(),
    )

    instalments = db.session.scalars(
        db.select(Repayment).where(Repayment.application_id == application_id)
    ).all()
    assert len(instalments) == 48  # the application tenure
    assert all(str(row.amount) != "" for row in instalments)


def test_an_admin_can_also_decide(seeded, client):
    application_id = submitted_application(client, customer_headers(client))

    response = client.post(
        f"/api/applications/{application_id}/approve", json={}, headers=admin_headers()
    )

    assert response.status_code == 200


# --- rejection / request-info ----------------------------------------------

def test_rejecting_requires_remarks(seeded, client):
    application_id = submitted_application(client, customer_headers(client))

    response = client.post(
        f"/api/applications/{application_id}/reject", json={}, headers=officer_headers()
    )

    assert response.status_code == 400
    assert "remarks" in response.get_json()["error"]["details"]


def test_an_officer_can_reject_with_remarks(seeded, client):
    application_id = submitted_application(client, customer_headers(client))

    response = client.post(
        f"/api/applications/{application_id}/reject",
        json={"remarks": "Insufficient income"},
        headers=officer_headers(),
    )

    assert response.status_code == 200
    assert response.get_json()["application"]["status"] == "REJECTED"
    assert response.get_json()["decision"]["remarks"] == "Insufficient income"


def test_requesting_information_opens_the_application_for_resubmission(seeded, client):
    headers = customer_headers(client)
    application_id = submitted_application(client, headers)

    requested = client.post(
        f"/api/applications/{application_id}/request-info",
        json={"remarks": "Please upload bank statements"},
        headers=officer_headers(),
    )
    assert requested.get_json()["application"]["status"] == "MORE_INFORMATION_REQUIRED"

    resubmitted = client.post(
        f"/api/applications/{application_id}/submit", headers=headers
    )
    assert resubmitted.status_code == 200
    assert resubmitted.get_json()["application"]["status"] == "SUBMITTED"


# --- state machine / authorization -----------------------------------------

def test_a_draft_cannot_be_decided(seeded, client):
    created = client.post(
        "/api/applications",
        json={
            "product_id": _product_id(client),
            "amount": "500000.00",
            "tenure": 48,
            "purpose": "Later",
            "financials": FINANCIALS,
        },
        headers=customer_headers(client),
    ).get_json()["application"]

    response = client.post(
        f"/api/applications/{created['id']}/approve", json={}, headers=officer_headers()
    )

    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "INVALID_STATE"


def test_an_approved_application_cannot_be_decided_again(seeded, client):
    application_id = submitted_application(client, customer_headers(client))
    client.post(f"/api/applications/{application_id}/approve", json={}, headers=officer_headers())

    response = client.post(
        f"/api/applications/{application_id}/reject",
        json={"remarks": "changed my mind"},
        headers=officer_headers(),
    )

    assert response.status_code == 409


def test_a_customer_cannot_decide(seeded, client):
    headers = customer_headers(client)
    application_id = submitted_application(client, headers)

    response = client.post(
        f"/api/applications/{application_id}/approve", json={}, headers=headers
    )

    assert response.status_code == 403
    assert response.get_json()["error"]["code"] == "FORBIDDEN"


def test_an_unknown_decision_verb_is_a_404(seeded, client):
    application_id = submitted_application(client, customer_headers(client))

    response = client.post(
        f"/api/applications/{application_id}/maybe", json={}, headers=officer_headers()
    )

    assert response.status_code == 404


def test_a_missing_application_is_a_404(seeded, client):
    response = client.post(
        "/api/applications/99999/approve", json={}, headers=officer_headers()
    )

    assert response.status_code == 404
