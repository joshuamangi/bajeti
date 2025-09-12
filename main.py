# This is a simple budget API that helps track categories like rent and petrol and adds limits

from fastapi import FastAPI
from data.db.db import engine, Base
from routers import auth, categories, expenses, users

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Bajeti")

# Add router
app.include_router(categories.router)
app.include_router(expenses.router)
app.include_router(auth.router)
app.include_router(users.router)
