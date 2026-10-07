import platform

from fastapi import FastAPI

from api._lib.errors import ApiError, api_error_handler
from api._lib.routers import admin as admin_router
from api._lib.routers import auth as auth_router

# Docs live under /api because Vercel only sends /api/* requests to this
# function in production. FastAPI's default /docs would be unreachable.
app = FastAPI(
    title="ClausePulse API",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.add_exception_handler(ApiError, api_error_handler)
app.include_router(auth_router.router)
app.include_router(admin_router.router)


@app.get("/api/health")
def health() -> dict[str, str]:
    # Returning the Python version proves which runtime Vercel actually
    # used, so we can confirm the .python-version pin (3.13) took effect.
    return {"status": "ok", "python": platform.python_version()}
