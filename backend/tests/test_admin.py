"""Admin endpoints: user management, credit adjustments, and instance
oversight -- require_admin rejects non-admins (spec Section 22)."""

from unittest.mock import patch

from tests.conftest import auth_headers, login, make_user


def test_non_admin_cannot_access_admin_routes(client, db) -> None:
    make_user(db, username="alice", password="pw")
    token = login(client, "alice", "pw")
    resp = client.get("/api/v1/admin/users", headers=auth_headers(token))
    assert resp.status_code == 403


def test_admin_can_list_and_create_users(client, db) -> None:
    make_user(db, username="root", password="pw", is_admin=True)
    token = login(client, "root", "pw")

    create_resp = client.post(
        "/api/v1/admin/users",
        json={"username": "newuser", "password": "pw2", "is_admin": False},
        headers=auth_headers(token),
    )
    assert create_resp.status_code == 201

    list_resp = client.get("/api/v1/admin/users", headers=auth_headers(token))
    usernames = {u["username"] for u in list_resp.json()}
    assert {"root", "newuser"} <= usernames


def test_admin_can_disable_and_enable_user(client, db) -> None:
    admin = make_user(db, username="root", password="pw", is_admin=True)
    target = make_user(db, username="alice", password="pw")
    token = login(client, "root", "pw")

    disable_resp = client.post(f"/api/v1/admin/users/{target.id}/disable", headers=auth_headers(token))
    assert disable_resp.status_code == 200
    assert disable_resp.json()["is_active"] is False

    # Disabled user can no longer log in.
    login_resp = client.post("/api/v1/auth/login", json={"username": "alice", "password": "pw"})
    assert login_resp.status_code == 403

    enable_resp = client.post(f"/api/v1/admin/users/{target.id}/enable", headers=auth_headers(token))
    assert enable_resp.status_code == 200
    assert enable_resp.json()["is_active"] is True


def test_admin_can_grant_and_view_credit_history(client, db) -> None:
    make_user(db, username="root", password="pw", is_admin=True)
    target = make_user(db, username="alice", password="pw")
    token = login(client, "root", "pw")

    grant_resp = client.post(
        f"/api/v1/admin/users/{target.id}/credits",
        json={"amount": 100, "description": "welcome bonus"},
        headers=auth_headers(token),
    )
    assert grant_resp.status_code == 200
    assert grant_resp.json()["amount"] == 100

    history_resp = client.get(
        f"/api/v1/admin/users/{target.id}/credits/history", headers=auth_headers(token)
    )
    assert history_resp.status_code == 200
    assert len(history_resp.json()) == 1


@patch("app.services.instances.k8s")
def test_admin_can_list_and_terminate_any_instance(mock_k8s, client, db) -> None:
    make_user(db, username="root", password="pw", is_admin=True)
    make_user(db, username="alice", password="pw", balance=50)
    admin_token = login(client, "root", "pw")
    alice_token = login(client, "alice", "pw")

    create_resp = client.post(
        "/api/v1/instances",
        json={"distribution": "ubuntu", "duration_minutes": 5},
        headers=auth_headers(alice_token),
    )
    instance_id = create_resp.json()["id"]

    list_resp = client.get("/api/v1/admin/instances", headers=auth_headers(admin_token))
    assert list_resp.status_code == 200
    assert any(i["id"] == instance_id for i in list_resp.json())

    terminate_resp = client.delete(
        f"/api/v1/admin/instances/{instance_id}", headers=auth_headers(admin_token)
    )
    assert terminate_resp.status_code == 200
    assert terminate_resp.json()["status"] == "TERMINATING"
