"""Loan product catalogue tests.

The catalogue is public to read and admin-only to write, and it is what every
application validates against - so both the access rule and the range
invariants matter.
"""

from tests.factories import admin_headers, customer_headers

PRODUCT = {
    "name": "Gold Loan",
    "min_amount": "10000.00",
    "max_amount": "500000.00",
    "interest_rate": "12.75",
    "min_tenure": 6,
    "max_tenure": 36,
    "min_income": "15000.00",
}


# --- reading ---------------------------------------------------------------

def test_anyone_can_list_active_products(seeded, client):
    response = client.get("/api/loan-products")

    assert response.status_code == 200
    products = response.get_json()["products"]
    assert {p["name"] for p in products} == {
        "Personal Loan",
        "Vehicle Loan",
        "Home Loan",
    }
    # Money survives as an exact decimal string, not a float.
    personal = next(p for p in products if p["name"] == "Personal Loan")
    assert personal["min_amount"] == "50000.00"
    assert personal["interest_rate"] == "11.50"
    assert personal["active"] is True


def test_an_unknown_product_is_a_404(seeded, client):
    response = client.get("/api/loan-products/99999")

    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "NOT_FOUND"


# --- writing is admin-only -------------------------------------------------

def test_a_customer_cannot_create_a_product(seeded, client):
    response = client.post(
        "/api/loan-products", json=PRODUCT, headers=customer_headers(client)
    )

    assert response.status_code == 403
    assert response.get_json()["error"]["code"] == "FORBIDDEN"


def test_an_anonymous_create_is_rejected(seeded, client):
    assert client.post("/api/loan-products", json=PRODUCT).status_code == 401


def test_an_admin_can_create_a_product(seeded, client):
    response = client.post(
        "/api/loan-products", json=PRODUCT, headers=admin_headers()
    )

    assert response.status_code == 201
    product = response.get_json()["product"]
    assert product["name"] == "Gold Loan"
    assert product["max_amount"] == "500000.00"
    assert product["active"] is True

    # ...and it is now visible in the public catalogue.
    names = {p["name"] for p in client.get("/api/loan-products").get_json()["products"]}
    assert "Gold Loan" in names


# --- validation ------------------------------------------------------------

def test_an_inverted_amount_range_is_rejected(seeded, client):
    response = client.post(
        "/api/loan-products",
        json={**PRODUCT, "min_amount": "600000.00"},
        headers=admin_headers(),
    )

    assert response.status_code == 400
    assert "max_amount" in response.get_json()["error"]["details"]


def test_an_inverted_tenure_range_is_rejected(seeded, client):
    response = client.post(
        "/api/loan-products",
        json={**PRODUCT, "min_tenure": 48},
        headers=admin_headers(),
    )

    assert response.status_code == 400
    assert "max_tenure" in response.get_json()["error"]["details"]


def test_a_duplicate_name_is_rejected(seeded, client):
    response = client.post(
        "/api/loan-products", json={**PRODUCT, "name": "Personal Loan"},
        headers=admin_headers(),
    )

    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "NAME_TAKEN"


def test_a_negative_interest_rate_is_rejected(seeded, client):
    response = client.post(
        "/api/loan-products", json={**PRODUCT, "interest_rate": "-1"},
        headers=admin_headers(),
    )

    assert response.status_code == 400


# --- updating --------------------------------------------------------------

def test_an_admin_can_update_a_product_partially(seeded, client):
    product_id = _product_id(client, "Personal Loan")

    response = client.put(
        f"/api/loan-products/{product_id}",
        json={"interest_rate": "10.25"},
        headers=admin_headers(),
    )

    assert response.status_code == 200
    assert response.get_json()["product"]["interest_rate"] == "10.25"
    # Fields not sent are untouched.
    assert response.get_json()["product"]["name"] == "Personal Loan"


def test_a_partial_update_cannot_invert_the_stored_range(seeded, client):
    """Lowering only the maximum below the stored minimum must be caught."""
    product_id = _product_id(client, "Personal Loan")

    response = client.put(
        f"/api/loan-products/{product_id}",
        json={"max_amount": "1000.00"},
        headers=admin_headers(),
    )

    assert response.status_code == 400
    assert "max_amount" in response.get_json()["error"]["details"]


def test_an_empty_update_is_rejected(seeded, client):
    product_id = _product_id(client, "Personal Loan")

    response = client.put(
        f"/api/loan-products/{product_id}", json={}, headers=admin_headers()
    )

    assert response.status_code == 400


# --- active/inactive visibility --------------------------------------------

def test_a_deactivated_product_disappears_from_the_public_list(seeded, client):
    product_id = _product_id(client, "Vehicle Loan")
    client.put(
        f"/api/loan-products/{product_id}",
        json={"active": False},
        headers=admin_headers(),
    )

    public_names = {
        p["name"] for p in client.get("/api/loan-products").get_json()["products"]
    }
    assert "Vehicle Loan" not in public_names


def test_staff_can_list_the_full_catalogue_including_inactive(seeded, client):
    product_id = _product_id(client, "Vehicle Loan")
    client.put(
        f"/api/loan-products/{product_id}",
        json={"active": False},
        headers=admin_headers(),
    )

    response = client.get("/api/loan-products?all=1", headers=admin_headers())
    names = {p["name"] for p in response.get_json()["products"]}

    assert "Vehicle Loan" in names


def test_a_customer_asking_for_all_still_only_sees_active(seeded, client):
    headers = admin_headers()
    product_id = _product_id(client, "Vehicle Loan")
    client.put(f"/api/loan-products/{product_id}", json={"active": False}, headers=headers)

    response = client.get("/api/loan-products?all=1", headers=customer_headers(client))
    names = {p["name"] for p in response.get_json()["products"]}

    assert "Vehicle Loan" not in names


def _product_id(client, name):
    """Resolve a seeded product's id from the public catalogue."""
    products = client.get("/api/loan-products").get_json()["products"]
    return next(p["id"] for p in products if p["name"] == name)
