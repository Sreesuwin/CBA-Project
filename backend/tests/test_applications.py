"""Application lifecycle tests: ownership, draft editing and submission.

The three things that must never regress: a customer cannot reach another
customer's application, a draft can be saved incomplete but submitted only when
it satisfies the product's rules, and a submitted application cannot be edited.
"""

from tests.factories import (
    bearer,
    customer_headers,
    officer_headers,
    register,
)

PERSONAL = "Personal Loan"
FINANCIALS = {
    "monthly_income": "65000.00",
    "monthly_expenses": "26000.00",
    "existing_emi": "8000.00",
    "existing_loans": 1,
    "employment_years": 4,
}


def product_id(client, name=PERSONAL):
    products = client.get("/api/loan-products").get_json()["products"]
    return next(p["id"] for p in products if p["name"] == name)


def create_draft(client, headers, **overrides):
    payload = {
        "product_id": product_id(client),
        "amount": "500000.00",
        "tenure": 48,
        "purpose": "Home renovation",
        "financials": FINANCIALS,
        **overrides,
    }
    return client.post("/api/applications", json=payload, headers=headers)


def draft_of(client, headers, **overrides):
    response = create_draft(client, headers, **overrides)
    assert response.status_code == 201, response.get_json()
    return response.get_json()["application"]


# --- creation --------------------------------------------------------------

def test_a_customer_can_create_a_draft(seeded, client):
    application = draft_of(client, customer_headers(client))

    assert application["status"] == "DRAFT"
    assert application["application_no"].startswith("LN-")
    assert application["product"]["name"] == PERSONAL
    assert application["amount"] == "500000.00"
    assert application["financial_details"]["monthly_income"] == "65000.00"


def test_creating_needs_authentication(seeded, client):
    response = create_draft(client, {})
    assert response.status_code == 401


def test_staff_cannot_create_an_application(seeded, client):
    """A loan officer has no borrower profile, so there is nothing to own."""
    response = create_draft(client, officer_headers())

    assert response.status_code == 403
    assert response.get_json()["error"]["code"] == "NO_CUSTOMER_PROFILE"


def test_an_unknown_product_is_rejected(seeded, client):
    response = create_draft(client, customer_headers(client), product_id=99999)

    assert response.status_code == 400
    assert "product_id" in response.get_json()["error"]["details"]


def test_the_application_number_is_server_generated(seeded, client):
    headers = customer_headers(client)
    first = draft_of(client, headers)
    second = draft_of(client, headers)

    assert first["application_no"] != second["application_no"]


# --- ownership -------------------------------------------------------------

def test_a_customer_cannot_read_another_customers_application(seeded, client):
    owner = customer_headers(client)
    intruder = customer_headers(client)
    application = draft_of(client, owner)

    response = client.get(f"/api/applications/{application['id']}", headers=intruder)

    assert response.status_code == 404  # not 403: the id must not be confirmed


def test_a_customer_cannot_edit_another_customers_application(seeded, client):
    owner = customer_headers(client)
    intruder = customer_headers(client)
    application = draft_of(client, owner)

    response = client.put(
        f"/api/applications/{application['id']}",
        json={"amount": "900000.00"},
        headers=intruder,
    )

    assert response.status_code == 404


def test_a_customer_cannot_submit_another_customers_application(seeded, client):
    owner = customer_headers(client)
    intruder = customer_headers(client)
    application = draft_of(client, owner)

    response = client.post(
        f"/api/applications/{application['id']}/submit", headers=intruder
    )

    assert response.status_code == 404


def test_a_customer_only_lists_their_own_applications(seeded, client):
    owner = customer_headers(client)
    other = customer_headers(client)
    draft_of(client, owner)
    draft_of(client, owner)

    assert len(client.get("/api/applications", headers=owner).get_json()["applications"]) == 2
    assert client.get("/api/applications", headers=other).get_json()["applications"] == []


def test_an_officer_sees_every_application(seeded, client):
    draft_of(client, customer_headers(client))
    draft_of(client, customer_headers(client))

    response = client.get("/api/applications", headers=officer_headers())

    # The 3 seeded demo applications plus the 2 just created.
    assert len(response.get_json()["applications"]) == 5


# --- draft editing ---------------------------------------------------------

def test_a_draft_can_be_edited(seeded, client):
    headers = customer_headers(client)
    application = draft_of(client, headers)

    response = client.put(
        f"/api/applications/{application['id']}",
        json={"amount": "600000.00", "purpose": "Wedding"},
        headers=headers,
    )

    assert response.status_code == 200
    body = response.get_json()["application"]
    assert body["amount"] == "600000.00"
    assert body["purpose"] == "Wedding"


def test_a_draft_may_be_saved_without_financials(seeded, client):
    headers = customer_headers(client)
    application = draft_of(client, headers, financials=None)

    assert application["financial_details"] is None
    assert application["status"] == "DRAFT"


# --- submission validation -------------------------------------------------

def test_a_draft_without_financials_cannot_be_submitted(seeded, client):
    headers = customer_headers(client)
    application = draft_of(client, headers, financials=None)

    response = client.post(
        f"/api/applications/{application['id']}/submit", headers=headers
    )

    assert response.status_code == 400
    assert "financials" in response.get_json()["error"]["details"]


def test_an_amount_above_the_product_maximum_is_rejected(seeded, client):
    headers = customer_headers(client)
    application = draft_of(client, headers, amount="5000000.00")  # Personal max 1,000,000

    response = client.post(
        f"/api/applications/{application['id']}/submit", headers=headers
    )

    assert response.status_code == 400
    assert "amount" in response.get_json()["error"]["details"]


def test_an_amount_below_the_product_minimum_is_rejected(seeded, client):
    headers = customer_headers(client)
    application = draft_of(client, headers, amount="1000.00")

    response = client.post(
        f"/api/applications/{application['id']}/submit", headers=headers
    )

    assert response.status_code == 400
    assert "amount" in response.get_json()["error"]["details"]


def test_a_tenure_outside_the_product_range_is_rejected(seeded, client):
    headers = customer_headers(client)
    application = draft_of(client, headers, tenure=120)  # Personal max 60

    response = client.post(
        f"/api/applications/{application['id']}/submit", headers=headers
    )

    assert response.status_code == 400
    assert "tenure" in response.get_json()["error"]["details"]


def test_income_below_the_product_minimum_is_rejected(seeded, client):
    headers = customer_headers(client)
    low_income = {**FINANCIALS, "monthly_income": "10000.00"}
    application = draft_of(client, headers, financials=low_income)

    response = client.post(
        f"/api/applications/{application['id']}/submit", headers=headers
    )

    assert response.status_code == 400
    assert "financials" in response.get_json()["error"]["details"]


# --- successful submission -------------------------------------------------

def test_a_valid_application_submits_and_is_scored(seeded, client):
    headers = customer_headers(client)
    application = draft_of(client, headers)

    response = client.post(
        f"/api/applications/{application['id']}/submit", headers=headers
    )

    assert response.status_code == 200
    body = response.get_json()["application"]
    assert body["status"] == "SUBMITTED"
    assert body["submitted_at"] is not None
    # The engine ran on submit, so the officer queue already has a verdict.
    assert body["assessment"]["score"] == 510  # Rahul-shaped financials
    assert body["assessment"]["recommendation"] == "MANUAL_REVIEW"


def test_a_submitted_application_cannot_be_resubmitted(seeded, client):
    headers = customer_headers(client)
    application = draft_of(client, headers)
    client.post(f"/api/applications/{application['id']}/submit", headers=headers)

    response = client.post(
        f"/api/applications/{application['id']}/submit", headers=headers
    )

    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "INVALID_STATE"


def test_a_submitted_application_cannot_be_edited(seeded, client):
    headers = customer_headers(client)
    application = draft_of(client, headers)
    client.post(f"/api/applications/{application['id']}/submit", headers=headers)

    response = client.put(
        f"/api/applications/{application['id']}",
        json={"amount": "600000.00"},
        headers=headers,
    )

    assert response.status_code == 409


def test_the_status_filter_narrows_the_list(seeded, client):
    headers = customer_headers(client)
    draft = draft_of(client, headers)
    submitted = draft_of(client, headers)
    client.post(f"/api/applications/{submitted['id']}/submit", headers=headers)

    drafts = client.get("/api/applications?status=DRAFT", headers=headers).get_json()
    assert {a["id"] for a in drafts["applications"]} == {draft["id"]}

    bad = client.get("/api/applications?status=NONSENSE", headers=headers)
    assert bad.status_code == 400


def test_an_owner_can_rerun_the_assessment(seeded, client):
    headers = customer_headers(client)
    application = draft_of(client, headers)

    response = client.post(
        f"/api/applications/{application['id']}/assess", headers=headers
    )

    assert response.status_code == 200
    assert response.get_json()["application"]["assessment"]["score"] == 510
