from fastapi.testclient import TestClient


def test_signup_and_signin_flow(client: TestClient) -> None:
    r = client.post(
        "/v1/auth/signup",
        json={"email": "alice@example.com", "password": "supersecret1", "full_name": "Alice"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["user"]["email"] == "alice@example.com"
    access = body["tokens"]["access_token"]

    r = client.post(
        "/v1/auth/signin",
        json={"email": "alice@example.com", "password": "supersecret1"},
    )
    assert r.status_code == 200
    tokens = r.json()["tokens"]
    assert tokens["access_token"]

    me = client.get("/v1/auth/me", headers={"Authorization": f"Bearer {access}"})
    assert me.status_code == 200
    assert me.json()["email"] == "alice@example.com"


def test_signin_wrong_password(client: TestClient) -> None:
    client.post(
        "/v1/auth/signup",
        json={"email": "bob@example.com", "password": "supersecret1"},
    )
    r = client.post(
        "/v1/auth/signin",
        json={"email": "bob@example.com", "password": "wrong"},
    )
    assert r.status_code == 401


def test_signup_duplicate(client: TestClient) -> None:
    client.post(
        "/v1/auth/signup",
        json={"email": "dup@example.com", "password": "supersecret1"},
    )
    r = client.post(
        "/v1/auth/signup",
        json={"email": "dup@example.com", "password": "supersecret1"},
    )
    assert r.status_code == 409
