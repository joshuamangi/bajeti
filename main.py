from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.gzip import GZipMiddleware
from pathlib import Path
from contextlib import asynccontextmanager

from app.routers import requests_router
from core.security_headers import SecurityHeadersMiddleware
from data.db.db import engine, Base
from routers import allocations, auth, budgets, categories, expenses, transfers, users
from app import requests
from app.config import IS_PRODUCTION

# Lifespan for DB setup


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    # Base.metadata.create_all(bind=engine)
    yield
    # Shutdown (optional future cleanup)


def api_docs_urls(is_production: bool) -> dict:
    """The interactive docs and the schema map out the whole API, so production does not serve them."""
    if is_production:
        return {"docs_url": None, "redoc_url": None, "openapi_url": None}
    return {}


app = FastAPI(
    title="Bajeti",
    debug=not IS_PRODUCTION,
    lifespan=lifespan,
    **api_docs_urls(IS_PRODUCTION)
)


# --- Static directory resolution ---
root_dir = Path(__file__).resolve().parent
static_dir = root_dir / "app" / "static"

if not static_dir.exists():
    static_dir = root_dir / "static"

app.mount("/static", StaticFiles(directory=static_dir), name="static")
# --- End static block ---


# Gzip for production
if IS_PRODUCTION:
    app.add_middleware(GZipMiddleware, minimum_size=500)


# Security headers on every response
app.add_middleware(SecurityHeadersMiddleware)


# Routers
app.include_router(categories.router)
app.include_router(expenses.router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(transfers.router)
app.include_router(budgets.router)
app.include_router(allocations.router)
app.include_router(requests_router.router)
