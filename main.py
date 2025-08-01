# This is a simple budget API that helps track categories like rent and petrol and adds limits
# I plan to use
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Bajeti")

class Category(BaseModel):
    name: str
    limit_amount: float

@app.get("/")
def read_root():
    return {"message": "Welcome to the budget app"}

@app.post("/categories")
def create_category(category: Category):
    return {"message": "Category added", "data": category}