"""Shapes for auth data (code-style.md: Pydantic models live in /models)."""

from typing import Literal

from pydantic import BaseModel

# Exactly two roles (Agent.md hard rule). Literal makes any other value a type error.
Role = Literal["admin", "viewer"]


class CurrentUser(BaseModel):
    uid: str
    email: str | None
    role: Role
