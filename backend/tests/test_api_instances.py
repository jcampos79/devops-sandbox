"""REST API tests for instance CRUD (spec Section 24/25/26/37): create,
list, get, delete, invalid duration, invalid distribution, insufficient
credits, and cross-user access rejection."""

from unittest.mock import patch

from tests.conftest import auth_headers, login, make_user


@patch("app.services.instances.k8s")
def test_create_list_get_delete_instance(mock_k8s, client, db) -> None:
    make_user(db, username="alice", password="pw", balance=50)
    token = login(client, "alice", "pw")

    create_resp = client.post(
        "/api/v1/instances",
        json={"distribution": "ubuntu", "duration_minutes": 10},
        headers=auth_headers(token),
    )
    assert create_resp.status_code == 201, create_resp.text
    instance = create_resp.json()
    assert instance["status"] == "RUNNING"
    assert instance["credits_charged"] == 10

    list_resp = client.get("/api/v1/instances", headers=auth_headers(token))
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    get_resp = client.get(f"/api/v1/instances/{instance['id']}", headers=auth_headers(token))
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == instance["id"]

    delete_resp = client.delete(f"/api/v1/instances/{instance['id']}", headers=auth_headers(token))
    assert delete_resp.status_code == 200
    assert delete_resp.json()["status"] == "TERMINATING"
    mock_k8s.delete_namespace.assert_called_once()


@patch("app.services.instances.k8s")
def test_create_instance_duration_over_30_rejected(mock_k8s, client, db) -> None:
    make_user(db, username="alice", password="pw", balance=100)
    token = login(client, "alice", "pw")
    resp = client.post(
        "/api/v1/instances",
        json={"distribution": "ubuntu", "duration_minutes": 60},
        headers=auth_headers(token),
    )
    assert resp.status_code == 422  # rejected server-side by schema validation (spec Section 13)
    mock_k8s.create_sandbox_namespace.assert_not_called()


def test_create_instance_invalid_distribution_rejected(client, db) -> None:
    make_user(db, username="alice", password="pw", balance=100)
    token = login(client, "alice", "pw")
    resp = client.post(
        "/api/v1/instances",
        json={"distribution": "windows-xp", "duration_minutes": 10},
        headers=auth_headers(token),
    )
    assert resp.status_code == 422  # rejected by pydantic enum validation


@patch("app.services.instances.k8s")
def test_create_instance_insufficient_credits_returns_402(mock_k8s, client, db) -> None:
    make_user(db, username="alice", password="pw", balance=5)
    token = login(client, "alice", "pw")
    resp = client.post(
        "/api/v1/instances",
        json={"distribution": "ubuntu", "duration_minutes": 10},
        headers=auth_headers(token),
    )
    assert resp.status_code == 402
    body = resp.json()
    assert body["error"] == "insufficient_credits"
    assert "10 credits" in body["message"]
    assert "5" in body["message"]


def test_instances_require_auth(client) -> None:
    assert client.get("/api/v1/instances").status_code == 401
    assert client.post("/api/v1/instances", json={"distribution": "ubuntu", "duration_minutes": 5}).status_code == 401


@patch("app.services.instances.k8s")
def test_user_cannot_access_another_users_instance(mock_k8s, client, db) -> None:
    make_user(db, username="alice", password="pw", balance=50)
    make_user(db, username="bob", password="pw", balance=50)
    alice_token = login(client, "alice", "pw")
    bob_token = login(client, "bob", "pw")

    create_resp = client.post(
        "/api/v1/instances",
        json={"distribution": "ubuntu", "duration_minutes": 5},
        headers=auth_headers(alice_token),
    )
    instance_id = create_resp.json()["id"]

    get_resp = client.get(f"/api/v1/instances/{instance_id}", headers=auth_headers(bob_token))
    assert get_resp.status_code == 404  # not 403 -- existence isn't revealed

    delete_resp = client.delete(f"/api/v1/instances/{instance_id}", headers=auth_headers(bob_token))
    assert delete_resp.status_code == 404


def test_invalid_api_key_rejected(client) -> None:
    resp = client.get("/api/v1/instances", headers=auth_headers("sbx_not-a-real-key"))
    assert resp.status_code == 401
