# Schemas for phone tokens (iPhone Shortcut)
from pydantic import BaseModel, Field


class ApiTokenIn(BaseModel):
    name: str = Field(default="iPhone", min_length=1, max_length=40)
