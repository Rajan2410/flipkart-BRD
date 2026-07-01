from pydantic import BaseModel

from app.models.enums import UserRole


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenPayload(BaseModel):
    sub: str
    role: UserRole
