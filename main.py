# This is a simple budget API that helps track categories like rent and petrol and adds limits

from fastapi import FastAPI
from routers import auth, categories, expenses, users

app = FastAPI(title="Bajeti")

# Add router
app.include_router(categories.router)
app.include_router(expenses.router)
app.include_router(auth.router)
app.include_router(users.router)
