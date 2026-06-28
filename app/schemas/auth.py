from __future__ import annotations

from pydantic import BaseModel


class LoginIn(BaseModel):
    email: str
    senha: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    papel: str
