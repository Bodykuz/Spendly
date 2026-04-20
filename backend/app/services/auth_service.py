"""Authentication business logic."""

from __future__ import annotations

import uuid
from datetime import timedelta

from sqlalchemy.orm import Session

from app.config import settings
from app.core.errors import Conflict, InvalidCredentials, NotAuthenticated
from app.core.security import (
    JWTError,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.auth import AuthResponse, SignInRequest, SignUpRequest, TokenPair, UserOut
from app.services.categorization import seed_default_categories


def _build_tokens(user_id: uuid.UUID) -> TokenPair:
    return TokenPair(
        access_token=create_access_token(str(user_id)),
        refresh_token=create_refresh_token(str(user_id)),
        expires_in=settings.access_token_expire_minutes * 60,
    )


def sign_up(db: Session, data: SignUpRequest) -> AuthResponse:
    normalized_email = data.email.lower().strip()
    existing = db.query(User).filter(User.email == normalized_email).first()
    if existing:
        raise Conflict("An account with this email already exists.")

    user = User(
        email=normalized_email,
        password_hash=hash_password(data.password),
        full_name=(data.full_name or "").strip() or None,
    )
    db.add(user)
    db.flush()
    seed_default_categories(db, user.id)
    db.commit()
    db.refresh(user)

    return AuthResponse(user=UserOut.model_validate(user), tokens=_build_tokens(user.id))


def sign_in(db: Session, data: SignInRequest) -> AuthResponse:
    user = db.query(User).filter(User.email == data.email.lower().strip()).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise InvalidCredentials("Invalid email or password.")
    if not user.is_active:
        raise InvalidCredentials("Account disabled.")
    return AuthResponse(user=UserOut.model_validate(user), tokens=_build_tokens(user.id))


def refresh_tokens(db: Session, refresh_token: str) -> TokenPair:
    try:
        payload = decode_token(refresh_token)
    except JWTError as exc:
        raise NotAuthenticated(str(exc))
    if payload.get("type") != "refresh":
        raise NotAuthenticated("Invalid token type")
    sub = payload.get("sub")
    if not sub:
        raise NotAuthenticated("Invalid token")

    try:
        user_id = uuid.UUID(sub)
    except ValueError as exc:
        raise NotAuthenticated("Invalid user id") from exc

    user = db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()
    if not user:
        raise NotAuthenticated("User not found")

    return _build_tokens(user.id)
