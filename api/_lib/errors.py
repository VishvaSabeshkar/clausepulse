"""Shared error type so every endpoint returns {"error", "code"} (code-style.md §6)."""

from fastapi import Request
from fastapi.responses import JSONResponse


class ApiError(Exception):
    """Raise this anywhere; the handler below turns it into our JSON shape."""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
    # 401s tell the client which auth scheme we expect (HTTP standard).
    headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message, "code": exc.code},
        headers=headers,
    )
