def test_health_reports_ok(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "ok"
    assert body["database_dialect"] == "sqlite"


def test_ready_checks_datastores(client):
    response = client.get("/api/health/ready")

    assert response.status_code == 200
    checks = response.get_json()["checks"]
    assert checks["database"]["connected"] is True
    # MongoDB is disabled in tests; that must not make the app unhealthy.
    assert checks["mongo"] == {"configured": False, "connected": False}


def test_unknown_route_returns_error_envelope(client):
    response = client.get("/api/does-not-exist")

    assert response.status_code == 404
    body = response.get_json()
    assert body["error"]["code"] == "NOT_FOUND"
    assert body["error"]["status"] == 404
