"""Tests for Firebase setup: a bad or missing key must fail cleanly, not crash."""

import firebase_admin
import pytest

from api._lib.errors import ApiError
from api._lib.services import firebase as firebase_service

ENV_VAR = "FIREBASE_SERVICE_ACCOUNT_B64"


@pytest.fixture(autouse=True)
def no_existing_app(monkeypatch: pytest.MonkeyPatch) -> None:
    # Pretend no Firebase app exists yet, like a cold start.
    def _no_app() -> None:
        raise ValueError("no app")

    monkeypatch.setattr(firebase_admin, "get_app", _no_app)


def test_missing_key_is_clean_500(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(ENV_VAR, raising=False)
    with pytest.raises(ApiError) as exc:
        firebase_service.get_firebase_app()
    assert exc.value.status_code == 500
    assert exc.value.code == "SERVER_MISCONFIGURED"


@pytest.mark.parametrize(
    "bad_value",
    [
        "not-base64!!",  # not valid base64 at all
        "aGVsbG8=",  # valid base64, but decodes to "hello" (not JSON)
        "e30=",  # valid base64 of "{}" (JSON, but not a key file)
    ],
)
def test_bad_key_is_clean_500(monkeypatch: pytest.MonkeyPatch, bad_value: str) -> None:
    monkeypatch.setenv(ENV_VAR, bad_value)
    with pytest.raises(ApiError) as exc:
        firebase_service.get_firebase_app()
    assert exc.value.code == "SERVER_MISCONFIGURED"
