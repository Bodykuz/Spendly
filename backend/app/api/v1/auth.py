"""/v1/auth routes."""

from __future__ import annotations

from fastapi import APIRouter, status

from app.deps import CurrentUser, DBSession
from app.schemas.auth import (
    AuthResponse,
    RefreshRequest,
    SignInRequest,
    SignUpRequest,
    TokenPair,
    UserOut,
)
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def signup(payload: SignUpRequest, db: DBSession) -> AuthResponse:
    return auth_service.sign_up(db, payload)


@router.post("/signin", response_model=AuthResponse)
def signin(payload: SignInRequest, db: DBSession) -> AuthResponse:
    return auth_service.sign_in(db, payload)


@router.post("/refresh", response_model=TokenPair)
def refresh(payload: RefreshRequest, db: DBSession) -> TokenPair:
    return auth_service.refresh_tokens(db, payload.refresh_token)


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)
