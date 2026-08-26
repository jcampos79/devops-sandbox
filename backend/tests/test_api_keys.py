"""API key creation, listing, revocation, and use as an auth method
(spec Section 23)."""

from unittest.mock import patch

from tests.conftest import auth_headers, login, make_user


def test_create_and_use_api_key(client, db) -> None:
    make_user(db, username="alice", password="pw", balance=50)
    session_token = login(client, "alice", "pw")

    create_resp = client.post(
        "/api/v1/me/api-keys", json={"name": "ci-key"}, headers=auth_headers(session_token)
    )
    assert create_resp.status_code == 201
    api_key = create_resp.json()["api_key"]
    assert api_key.startswith("sbx_")

    # The API key authenticates just like a session token.
    me_resp = client.get("/api/v1/me", headers=auth_headers(api_key))
    assert me_resp.status_code == 200
    assert me_resp.json()["username"] == "alice"


def test_api_key_list_does_not_expose_plaintext(client, db) -> None:
    make_user(db, username="alice", password="pw")
    token = login(client, "alice", "pw")
    client.post("/api/v1/me/api-keys", json={"name": "ci-key"}, headers=auth_headers(token))

    list_resp = client.get("/api/v1/me/api-keys", headers=auth_headers(token))
    assert list_resp.status_code == 200
    assert "api_key" not in list_resp.json()[0]
    assert "key_hash" not in list_resp.json()[0]


def test_revoked_api_key_cannot_authenticate(client, db) -> None:
    make_user(db, username="alice", password="pw")
    token = login(client, "alice", "pw")
    create_resp = client.post("/api/v1/me/api-keys", json={"name": "ci-key"}, headers=auth_headers(token))
    key_id = create_resp.json()["id"]
    api_key = create_resp.json()["api_key"]

    revoke_resp = client.delete(f"/api/v1/me/api-keys/{key_id}", headers=auth_headers(token))
    assert revoke_resp.status_code == 204

    me_resp = client.get("/api/v1/me", headers=auth_headers(api_key))
    assert me_resp.status_code == 401


@patch("app.services.instances.k8s")
def test_api_key_used_for_instance_api(mock_k8s, client, db) -> None:
    make_user(db, username="alice", password="pw", balance=50)
    session_token = login(client, "alice", "pw")
    create_resp = client.post(
        "/api/v1/me/api-keys", json={"name": "ci-key"}, headers=auth_headers(session_token)
    )
    api_key = create_resp.json()["api_key"]

    resp = client.post(
        "/api/v1/instances",
        json={"distribution": "ubuntu", "duration_minutes": 5},
        headers=auth_headers(api_key),
    )
    assert resp.status_code == 201
