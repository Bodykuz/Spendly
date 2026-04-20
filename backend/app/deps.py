"""Reusable FastAPI dependencies."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.core.errors import NotAuthenticated
from app.core.security import JWTError, decode_token
from app.database import get_db
from app.models.user import User
from app.providers.base import PSD2Provider
from app.providers.factory import get_provider as _get_provider

DBSession = Annotated[Session, Depends(get_db)]


def _extract_bearer(auth_header: str | None) -> str:
    if not auth_header or not auth_header.lower().startswith("bearer "):
        raise NotAuthenticated("Missing bearer token")
    return auth_header[7:].strip()


def get_current_user(
    db: DBSession,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> User:
    token = _extract_bearer(authorization)
    try:
        payload = decode_token(token)
    except JWTError as exc:
        raise NotAuthenticated(str(exc))

    if payload.get("type") != "access":
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
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_provider() -> PSD2Provider:
    return _get_provider()


Provider = Annotated[PSD2Provider, Depends(get_provider)]
