# This is a simple budget API that helps track categories like rent and petrol and adds limits
# I plan to use
from fastapi import FastAPI
from routers import categories

app = FastAPI(title="Bajeti")

# Add router
app.include_router(categories.router)
