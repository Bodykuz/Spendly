"""Transaction model.

Canonical transaction schema mapped from Berlin Group / GoCardless:
    * amount signed: negative = debit (expense), positive = credit (income)
    * booking_date: final posted date
    * value_date: economic date
"""

from __future__ import annotations

import enum
import uuid
from datetime import date as date_type
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Date,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDPKMixin

if TYPE_CHECKING:
    from app.models.account import Account
    from app.models.category import Category


class TransactionStatus(str, enum.Enum):
    BOOKED = "booked"
    PENDING = "pending"


class Transaction(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "transactions"
    __table_args__ = (
        UniqueConstraint(
            "account_id", "provider_transaction_id", name="uq_tx_account_provider_id"
        ),
        Index("ix_tx_account_booking_date", "account_id", "booking_date"),
        Index("ix_tx_user_booking_date", "user_id", "booking_date"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    provider_transaction_id: Mapped[str] = mapped_column(String(128), nullable=False)
    internal_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True,
        doc="Deterministic hash for providers that don't give stable IDs.",
    )

    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)

    booking_date: Mapped[date_type] = mapped_column(Date, nullable=False)
    value_date: Mapped[date_type | None] = mapped_column(Date, nullable=True)

    status: Mapped[TransactionStatus] = mapped_column(
        Enum(TransactionStatus, name="transaction_status"),
        default=TransactionStatus.BOOKED,
        nullable=False,
    )

    counterparty_name: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    counterparty_iban: Mapped[str | None] = mapped_column(String(34), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    merchant_category_code: Mapped[str | None] = mapped_column(String(8), nullable=True)

    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_subscription: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_salary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    user_categorized: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    account: Mapped["Account"] = relationship(back_populates="transactions")
    category: Mapped["Category | None"] = relationship()
