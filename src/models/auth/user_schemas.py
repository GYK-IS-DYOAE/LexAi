# src/models/auth/user_schemas.py

from pydantic import BaseModel, EmailStr, Field
from uuid import UUID

class RegisterRequest(BaseModel):
    first_name: str = Field(..., min_length=1, example="Zeynep")
    last_name: str = Field(..., min_length=1, example="Kaygusuz")
    email: EmailStr = Field(..., example="zeynep@example.com")
    password: str = Field(..., min_length=6, example="gizli123")

class LoginRequest(BaseModel):
    email: EmailStr = Field(..., example="zeynep@example.com")
    password: str = Field(..., min_length=6, example="gizli123")

class UserResponse(BaseModel):
    id: UUID
    first_name: str
    last_name: str
    email: EmailStr

    class Config:
        orm_mode = True
