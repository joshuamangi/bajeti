from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.gzip import GZipMiddleware
from pathlib import Path
from app import requests
from data.db.db import engine, Base
from routers import auth, categories, expenses, users
from app.config import IS_PRODUCTION, ENVIRONMENT

# Database init
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Bajeti", debug=not IS_PRODUCTION)

# ---Static directory resolution ---
# Figure out where static lives (works in dev + container)
root_dir = Path(__file__).resolve().parent
static_dir = root_dir / "app" / "static"  # inside container (/app/app/static)

if not static_dir.exists():
    static_dir = root_dir / "static"  # fallback if you run directly on host

print(f"📁 Using static directory: {static_dir}")
app.mount("/static", StaticFiles(directory=static_dir), name="static")
# ---End static block ---

# Gzip for prod
if IS_PRODUCTION:
    app.add_middleware(GZipMiddleware, minimum_size=500)

# Routers
app.include_router(categories.router)
app.include_router(expenses.router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(requests.router)
