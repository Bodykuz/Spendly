from fastapi.testclient import TestClient


def _setup(client: TestClient):
    r = client.post(
        "/v1/auth/signup",
        json={"email": "eve@example.com", "password": "supersecret1"},
    )
    tok = r.json()["tokens"]["access_token"]
    h = {"Authorization": f"Bearer {tok}"}
    r = client.post(
        "/v1/banks/link",
        json={"institution_id": "MBANK_PL", "redirect_uri": "spendly://callback"},
        headers=h,
    )
    conn_id = r.json()["connection_id"]
    client.post(f"/v1/banks/connections/{conn_id}/sync", headers=h)
    return h


def test_dashboard_has_data(client: TestClient) -> None:
    h = _setup(client)
    r = client.get("/v1/analytics/dashboard", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["accounts"] == 1
    assert body["linked_banks"] == 1
    assert float(body["total_balance"]) == 1000.0


def test_cashflow(client: TestClient) -> None:
    h = _setup(client)
    r = client.get("/v1/analytics/cashflow?months=3", headers=h)
    assert r.status_code == 200
    assert r.json()["months"]


def test_insights(client: TestClient) -> None:
    h = _setup(client)
    r = client.get("/v1/insights", headers=h)
    assert r.status_code == 200
    assert isinstance(r.json(), list)
