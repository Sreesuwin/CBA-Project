"""Document metadata and audit trail tests.

Both live in the flexible store (MongoDB when available, in-memory otherwise).
The tests run against the in-memory fallback, which is the path a machine
without MongoDB actually exercises.
"""

from tests.factories import customer_headers, officer_headers

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


def _application(client, headers):
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
    return created["id"]


# --- documents -------------------------------------------------------------

def test_document_metadata_starts_empty(seeded, client):
    headers = customer_headers(client)
    application_id = _application(client, headers)

    response = client.get(f"/api/applications/{application_id}/documents", headers=headers)

    assert response.status_code == 200
    assert response.get_json()["document"]["files"] == []


def test_a_customer_can_attach_document_metadata(seeded, client):
    headers = customer_headers(client)
    application_id = _application(client, headers)

    response = client.post(
        f"/api/applications/{application_id}/documents",
        json={"type": "SALARY_SLIP", "filename": "salary.pdf"},
        headers=headers,
    )

    assert response.status_code == 201
    files = response.get_json()["document"]["files"]
    assert len(files) == 1
    assert files[0]["type"] == "SALARY_SLIP"
    assert files[0]["filename"] == "salary.pdf"
    assert files[0]["status"] == "PENDING"  # verification is a later step


def test_a_second_document_is_appended(seeded, client):
    headers = customer_headers(client)
    application_id = _application(client, headers)
    for kind, name in [("SALARY_SLIP", "salary.pdf"), ("ID_PROOF", "aadhaar.pdf")]:
        client.post(
            f"/api/applications/{application_id}/documents",
            json={"type": kind, "filename": name},
            headers=headers,
        )

    files = client.get(
        f"/api/applications/{application_id}/documents", headers=headers
    ).get_json()["document"]["files"]

    assert [f["filename"] for f in files] == ["salary.pdf", "aadhaar.pdf"]


def test_an_unknown_document_type_is_rejected(seeded, client):
    headers = customer_headers(client)
    application_id = _application(client, headers)

    response = client.post(
        f"/api/applications/{application_id}/documents",
        json={"type": "PASSPORT", "filename": "x.pdf"},
        headers=headers,
    )

    assert response.status_code == 400


# --- audit -----------------------------------------------------------------

def test_the_audit_trail_records_the_application_events(seeded, client):
    headers = customer_headers(client)
    application_id = _application(client, headers)
    client.post(f"/api/applications/{application_id}/submit", headers=headers)
    client.post(f"/api/applications/{application_id}/approve", json={}, headers=officer_headers())

    response = client.get(f"/api/applications/{application_id}/audit", headers=headers)

    assert response.status_code == 200
    actions = [entry["action"] for entry in response.get_json()["audit"]]
    assert "APPLICATION_CREATED" in actions
    assert "APPLICATION_SUBMITTED" in actions
    assert "CREDIT_ASSESSED" in actions
    assert "DECISION_RECORDED" in actions
    # Oldest first, each carrying the actor who caused it.
    assert response.get_json()["audit"][0]["actor_id"] is not None


def test_an_intruder_cannot_read_another_customers_trail(seeded, client):
    owner = customer_headers(client)
    intruder = customer_headers(client)
    application_id = _application(client, owner)

    response = client.get(f"/api/applications/{application_id}/audit", headers=intruder)

    assert response.status_code == 404


def test_an_intruder_cannot_read_another_customers_documents(seeded, client):
    owner = customer_headers(client)
    intruder = customer_headers(client)
    application_id = _application(client, owner)

    response = client.get(
        f"/api/applications/{application_id}/documents", headers=intruder
    )

    assert response.status_code == 404
