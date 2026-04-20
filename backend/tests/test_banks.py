from fastapi.testclient import TestClient


def _auth(client: TestClient, email: str = "carol@example.com") -> str:
    r = client.post(
        "/v1/auth/signup",
        json={"email": email, "password": "supersecret1", "full_name": "Carol"},
    )
    return r.json()["tokens"]["access_token"]


def test_list_institutions(client: TestClient) -> None:
    tok = _auth(client)
    r = client.get("/v1/banks/institutions?country=PL", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    assert any(i["id"] == "PKO_PL" for i in r.json())


def test_link_bank_and_sync(client: TestClient) -> None:
    tok = _auth(client, "dave@example.com")
    h = {"Authorization": f"Bearer {tok}"}

    r = client.post(
        "/v1/banks/link",
        json={"institution_id": "PKO_PL", "redirect_uri": "spendly://callback"},
        headers=h,
    )
    assert r.status_code == 201
    conn_id = r.json()["connection_id"]

    r = client.post(f"/v1/banks/connections/{conn_id}/sync", headers=h)
    assert r.status_code == 200
    assert r.json()["accounts"] >= 1

    accts = client.get("/v1/accounts", headers=h).json()
    assert len(accts) == 1
    assert accts[0]["iban"] == "PL61109010140000071219812874"

    txs = client.get("/v1/transactions", headers=h).json()
    assert txs["total"] == 2
