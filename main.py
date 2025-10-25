# This is a simple budget API that helps track categories like rent and petrol and adds limits

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.gzip import GZipMiddleware
from app import requests
from data.db.db import engine, Base
from routers import auth, categories, expenses, users
from app.config import STATIC_DIR, IS_PRODUCTION, ENVIRONMENT

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Bajeti", debug=not IS_PRODUCTION)

# Serve minified static if in production
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Gzip middleware for production (smaller payloads)
if IS_PRODUCTION:
    app.add_middleware(GZipMiddleware, minimum_size=500)

# Add router
app.include_router(categories.router)
app.include_router(expenses.router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(requests.router)
