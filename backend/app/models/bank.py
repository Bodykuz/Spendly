"""Bank connection (PSD2 consent / requisition) model."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List

from sqlalchemy import DateTime, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDPKMixin

if TYPE_CHECKING:
    from app.models.account import Account
    from app.models.user import User


class ConsentStatus(str, enum.Enum):
    PENDING = "pending"        # requisition created, user not yet redirected
    LINKED = "linked"          # consent granted, accounts fetched
    EXPIRED = "expired"        # consent past its end date or provider says expired
    REVOKED = "revoked"        # user removed consent
    ERROR = "error"            # provider error


class BankConnection(Base, UUIDPKMixin, TimestampMixin):
    """One bank consent per user per institution.

    GoCardless calls this a "requisition" — we abstract as BankConnection so the
    provider can be swapped later.
    """

    __tablename__ = "bank_connections"
    __table_args__ = (
        UniqueConstraint("provider", "provider_ref", name="uq_bank_provider_ref"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_ref: Mapped[str] = mapped_column(String(128), nullable=False)

    institution_id: Mapped[str] = mapped_column(String(128), nullable=False)
    institution_name: Mapped[str] = mapped_column(String(128), nullable=False)
    institution_logo: Mapped[str | None] = mapped_column(String(512), nullable=True)
    institution_country: Mapped[str] = mapped_column(String(2), default="PL", nullable=False)

    status: Mapped[ConsentStatus] = mapped_column(
        Enum(ConsentStatus, name="consent_status"),
        default=ConsentStatus.PENDING,
        nullable=False,
    )
    consent_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    redirect_uri: Mapped[str] = mapped_column(String(512), nullable=False)

    user: Mapped["User"] = relationship(back_populates="bank_connections")
    accounts: Mapped[List["Account"]] = relationship(
        back_populates="bank_connection", cascade="all, delete-orphan"
    )
