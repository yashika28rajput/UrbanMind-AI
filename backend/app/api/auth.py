from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.services.dashboard_auth import (
    TOKEN_TTL_SECONDS,
    auth_status,
    authentication_configured,
    create_access_token,
    verify_credentials,
)

router = APIRouter(prefix="/api/v1/auth", tags=["dashboard-authentication"])


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=1, max_length=1024)


@router.get("/config")
async def authentication_configuration() -> dict[str, bool]:
    return auth_status()


@router.post("/login")
async def login(request: LoginRequest) -> dict[str, object]:
    if not authentication_configured():
        raise HTTPException(status_code=503, detail="Dashboard authentication is not configured.")
    if not verify_credentials(request.username, request.password):
        raise HTTPException(status_code=401, detail="Invalid username or password.")
    return {
        "access_token": create_access_token(request.username),
        "token_type": "bearer",
        "expires_in": TOKEN_TTL_SECONDS,
    }


@router.get("/me")
async def current_user(request: Request) -> dict[str, str]:
    subject = getattr(request.state, "authenticated_user", None)
    if subject is None:
        raise HTTPException(status_code=401, detail="Authentication is not enabled or a valid bearer token is missing.")
    return {"username": subject}
