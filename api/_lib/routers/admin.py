"""Admin-only endpoints. Real ones (audit log, pipeline run) come in later phases."""

from typing import Annotated

from fastapi import APIRouter, Depends

from api._lib.models.auth import CurrentUser
from api._lib.services.auth import require_admin

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/ping")
def admin_ping(user: Annotated[CurrentUser, Depends(require_admin)]) -> dict[str, str]:
    """Proves the admin gate works: viewers get 403, admins get 200."""
    return {"status": "ok", "uid": user.uid}
