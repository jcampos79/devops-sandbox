"""Password hashing, session tokens, and API key auth."""

import uuid

from app.auth.security import (
    generate_api_key,
    hash_api_key,
    hash_password,
    verify_password,
    verify_session_token,
    create_session_token,
)


def test_password_hash_roundtrip() -> None:
    h = hash_password("correct horse battery staple")
    assert h != "correct horse battery staple"
    assert verify_password("correct horse battery staple", h)
    assert not verify_password("wrong password", h)


def test_session_token_roundtrip() -> None:
    user_id = str(uuid.uuid4())
    token = create_session_token(user_id)
    assert verify_session_token(token) == user_id


def test_session_token_rejects_garbage() -> None:
    assert verify_session_token("not-a-real-token") is None


def test_api_key_generation_and_hash_lookup() -> None:
    plaintext, key_hash = generate_api_key()
    assert plaintext.startswith("sbx_")
    assert hash_api_key(plaintext) == key_hash
    # Different generations never collide in practice
    plaintext2, key_hash2 = generate_api_key()
    assert plaintext != plaintext2
    assert key_hash != key_hash2
