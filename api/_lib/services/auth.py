"""Authentication and role checks. Every protected route depends on these."""

import logging
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth

from api._lib.errors import ApiError
from api._lib.models.auth import CurrentUser, Role
from api._lib.services.firebase import get_firebase_app

logger = logging.getLogger(__name__)

# auto_error=False: we raise our own 401 in the {"error","code"} shape instead
# of FastAPI's default. Bonus: adds an "Authorize" button to /api/docs.
_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> CurrentUser:
    # Plain `def`, not `async def`: verify_id_token can block on a network
    # call (fetching Google's public keys), so FastAPI runs it in a thread
    # pool instead of freezing every other request.
    if creds is None:
        raise ApiError(401, "UNAUTHENTICATED", "Missing Authorization: Bearer token")

    try:
        decoded = auth.verify_id_token(
            creds.credentials,
            app=get_firebase_app(),
            clock_skew_seconds=10,  # tolerate small clock drift between machines
        )
    # Order matters: ExpiredIdTokenError is a subclass of InvalidIdTokenError,
    # so it must be caught first or it would never be reached.
    except auth.ExpiredIdTokenError:
        raise ApiError(401, "UNAUTHENTICATED", "Token expired, sign in again") from None
    except auth.InvalidIdTokenError as exc:
        logger.info("Rejected ID token: %s", exc)
        raise ApiError(401, "UNAUTHENTICATED", "Invalid token") from None
    except auth.CertificateFetchError:
        logger.exception("Could not fetch Google public keys")
        raise ApiError(
            503, "AUTH_UNAVAILABLE", "Cannot verify sign-in right now"
        ) from None

    # Fail closed: anything other than exactly "admin" (missing, typo, junk)
    # becomes the least-privileged role.
    role: Role = "admin" if decoded.get("role") == "admin" else "viewer"
    return CurrentUser(uid=decoded["uid"], email=decoded.get("email"), role=role)


def require_admin(
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> CurrentUser:
    if user.role != "admin":
        raise ApiError(403, "FORBIDDEN", "Admin role required")
    return user
