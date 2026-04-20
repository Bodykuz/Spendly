"""Transaction schemas."""

from __future__ import annotations

import uuid
from datetime import date as date_type, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.transaction import TransactionStatus


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    name: str
    icon: str
    color: str
    is_income: bool
    is_system: bool


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    account_id: uuid.UUID
    category: CategoryOut | None
    amount: Decimal
    currency: str
    booking_date: date_type
    value_date: date_type | None
    status: TransactionStatus
    counterparty_name: str | None
    description: str | None
    is_recurring: bool
    is_subscription: bool
    is_salary: bool
    notes: str | None


class TransactionPage(BaseModel):
    items: list[TransactionOut]
    total: int
    page: int
    size: int


class RecategorizeRequest(BaseModel):
    category_id: uuid.UUID | None = Field(default=None)


class TransactionFilters(BaseModel):
    start_date: date_type | None = None
    end_date: date_type | None = None
    account_id: uuid.UUID | None = None
    category_id: uuid.UUID | None = None
    min_amount: Decimal | None = None
    max_amount: Decimal | None = None
    search: str | None = None
    only_expenses: bool = False
    only_income: bool = False
