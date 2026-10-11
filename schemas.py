from pydantic import BaseModel, Field, EmailStr, conint, ConfigDict
from typing import Annotated
from datetime import datetime











class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=255, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=8, max_length=128)


class UserResponse(BaseModel):
    id: int
    username: str

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
