"""Auth-related endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends

from api._lib.models.auth import CurrentUser
from api._lib.services.auth import get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/whoami", response_model=CurrentUser)
def whoami(user: Annotated[CurrentUser, Depends(get_current_user)]) -> CurrentUser:
    """Echo who the backend thinks you are. Used to test sign-in and roles."""
    return user
