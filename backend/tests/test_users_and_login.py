"""Login endpoint + disabled-user rejection (spec Section 21/51)."""

from tests.conftest import auth_headers, login, make_user


def test_login_success_and_me(client, db) -> None:
    make_user(db, username="alice", password="s3cret!")
    token = login(client, "alice", "s3cret!")
    me = client.get("/api/v1/me", headers=auth_headers(token))
    assert me.status_code == 200
    assert me.json()["username"] == "alice"
    assert me.json()["credit_balance"] == 0


def test_login_wrong_password(client, db) -> None:
    make_user(db, username="bob", password="correct-password")
    resp = client.post("/api/v1/auth/login", json={"username": "bob", "password": "wrong"})
    assert resp.status_code == 401


def test_disabled_user_cannot_log_in(client, db) -> None:
    from app.models import User

    make_user(db, username="carol", password="pw")
    db.query(User).filter(User.username == "carol").update({"is_active": False})
    db.commit()

    resp = client.post("/api/v1/auth/login", json={"username": "carol", "password": "pw"})
    assert resp.status_code == 403


def test_me_requires_auth(client) -> None:
    resp = client.get("/api/v1/me")
    assert resp.status_code == 401
