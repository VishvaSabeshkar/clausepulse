"""Firebase Admin SDK setup, created once per warm function instance."""

import base64
import json
import logging
import os
import threading

import firebase_admin
from firebase_admin import credentials

from api._lib.errors import ApiError

logger = logging.getLogger(__name__)

_ENV_VAR = "FIREBASE_SERVICE_ACCOUNT_B64"
# Vercel can run several requests at once in one instance; the lock stops
# two threads from both trying to initialise Firebase on a cold start.
_init_lock = threading.Lock()


def _misconfigured() -> ApiError:
    return ApiError(500, "SERVER_MISCONFIGURED", "Server auth is not configured")


def get_firebase_app() -> firebase_admin.App:
    """Return the Firebase app, creating it on first use.

    Lazy on purpose: /api/health keeps working even if the env var is
    missing, so a config mistake shows up as a clear error on auth routes
    instead of crashing the whole function at import time.
    """
    with _init_lock:
        try:
            return firebase_admin.get_app()
        except ValueError:
            pass  # Expected on a cold start: no app exists yet in this instance.

        encoded = os.environ.get(_ENV_VAR)
        if not encoded:
            logger.error("%s is not set", _ENV_VAR)
            raise _misconfigured()

        # Stored as base64 so no tool can mangle the \n characters inside the
        # private key (security.md §4).
        try:
            service_account = json.loads(base64.b64decode(encoded))
            cred = credentials.Certificate(service_account)
        except ValueError:
            # Bad base64, bad JSON and an invalid key file are all ValueError
            # subclasses. Log the details for us; give the client clean JSON.
            logger.exception("%s is set but could not be decoded", _ENV_VAR)
            raise _misconfigured() from None
        return firebase_admin.initialize_app(cred)
