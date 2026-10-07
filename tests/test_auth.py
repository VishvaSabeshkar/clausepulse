"""Unit tests for the auth guard (code-style.md §7: role-check logic is tested).

Firebase is replaced with fakes, so these tests need no keys and no network.
"""

from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient
from firebase_admin import auth as fb_auth

from api._lib.services import auth as auth_service
from api.index import app

WHOAMI = "/api/auth/whoami"
ADMIN_PING = "/api/admin/ping"
BEARER = {"Authorization": "Bearer fake-token"}


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    # Never touch real Firebase: no key file, no network call.
    monkeypatch.setattr(auth_service, "get_firebase_app", lambda: None)
    return TestClient(app)


def fake_verify(result: dict[str, Any] | Exception) -> Callable[..., dict[str, Any]]:
    """Build a stand-in for verify_id_token that returns claims or raises."""

    def _verify(token: str, **kwargs: Any) -> dict[str, Any]:
        if isinstance(result, Exception):
            raise result
        return result

    return _verify


def use_token(monkeypatch: pytest.MonkeyPatch, result: Any) -> None:
    monkeypatch.setattr(fb_auth, "verify_id_token", fake_verify(result))


# ---------- 401: not signed in ----------


def test_missing_token_is_401(client: TestClient) -> None:
    res = client.get(WHOAMI)
    assert res.status_code == 401
    assert res.json() == {
        "error": "Missing Authorization: Bearer token",
        "code": "UNAUTHENTICATED",
    }
    assert res.headers["WWW-Authenticate"] == "Bearer"


def test_invalid_token_is_401(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    use_token(monkeypatch, fb_auth.InvalidIdTokenError("bad signature"))
    res = client.get(WHOAMI, headers=BEARER)
    assert res.status_code == 401
    assert res.json()["error"] == "Invalid token"


def test_expired_token_gets_its_own_message(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Guards the except-order: ExpiredIdTokenError is a subclass of
    # InvalidIdTokenError, so a reordering would silently change this message.
    use_token(monkeypatch, fb_auth.ExpiredIdTokenError("expired", None))
    res = client.get(WHOAMI, headers=BEARER)
    assert res.status_code == 401
    assert res.json()["error"] == "Token expired, sign in again"


# ---------- 503: our problem, not the user's ----------


def test_google_keys_unreachable_is_503(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    use_token(monkeypatch, fb_auth.CertificateFetchError("network down", None))
    res = client.get(WHOAMI, headers=BEARER)
    assert res.status_code == 503
    assert res.json()["code"] == "AUTH_UNAVAILABLE"


# ---------- Role comes from the claim, and fails closed ----------


@pytest.mark.parametrize(
    ("claims", "expected_role"),
    [
        ({}, "viewer"),  # no claim -> viewer (the default)
        ({"role": "admin"}, "admin"),
        ({"role": "Admin"}, "viewer"),  # wrong case -> fail closed
        ({"role": "superuser"}, "viewer"),  # unknown role -> fail closed
    ],
)
def test_role_comes_from_claim(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    claims: dict[str, str],
    expected_role: str,
) -> None:
    use_token(monkeypatch, {"uid": "u1", "email": "t@example.com", **claims})
    res = client.get(WHOAMI, headers=BEARER)
    assert res.status_code == 200
    assert res.json()["role"] == expected_role


# ---------- 403 / 200: the admin gate ----------


def test_viewer_cannot_reach_admin_route(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    use_token(monkeypatch, {"uid": "u1", "email": "v@example.com"})
    res = client.get(ADMIN_PING, headers=BEARER)
    assert res.status_code == 403
    assert res.json() == {"error": "Admin role required", "code": "FORBIDDEN"}


def test_admin_can_reach_admin_route(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    use_token(monkeypatch, {"uid": "u2", "email": "a@example.com", "role": "admin"})
    res = client.get(ADMIN_PING, headers=BEARER)
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "uid": "u2"}
