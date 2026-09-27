"""Admin-only endpoints: the user registry and the global audit trail."""

from tests.factories import admin_headers, customer_headers, officer_headers


def test_an_admin_can_list_users(seeded, client):
    response = client.get("/api/users", headers=admin_headers())

    assert response.status_code == 200
    users = response.get_json()["users"]
    # The 5 seeded accounts plus the admin making the request.
    assert len(users) == 6
    assert {u["role"] for u in users} >= {"CUSTOMER", "LOAN_OFFICER", "ADMIN"}
    assert "password_hash" not in str(users)


def test_the_user_list_is_admin_only(seeded, client):
    assert client.get("/api/users", headers=customer_headers(client)).status_code == 403
    assert client.get("/api/users", headers=officer_headers()).status_code == 403
    assert client.get("/api/users").status_code == 401


def test_the_global_audit_trail_is_admin_only(seeded, client):
    assert client.get("/api/audit", headers=customer_headers(client)).status_code == 403
    assert client.get("/api/audit").status_code == 401


def test_the_global_audit_trail_collects_events_across_applications(seeded, client):
    # Submitting a seeded application produces audit entries.
    headers = customer_headers(client)
    product = client.get("/api/loan-products").get_json()["products"][0]
    created = client.post(
        "/api/applications",
        json={
            "product_id": product["id"],
            "amount": "200000.00",
            "tenure": 24,
            "purpose": "Test",
            "financials": {
                "monthly_income": "60000.00",
                "monthly_expenses": "20000.00",
                "existing_emi": "5000.00",
            },
        },
        headers=headers,
    ).get_json()["application"]

    response = client.get("/api/audit", headers=admin_headers())

    assert response.status_code == 200
    assert any(
        entry["application_id"] == created["id"]
        for entry in response.get_json()["audit"]
    )
