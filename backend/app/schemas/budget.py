"""Budget schemas."""

from __future__ import annotations

import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class BudgetCreate(BaseModel):
    category_id: uuid.UUID
    amount: Decimal = Field(gt=0)
    period: str = "monthly"
    currency: str = "PLN"


class BudgetUpdate(BaseModel):
    amount: Decimal | None = Field(default=None, gt=0)


class BudgetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    category_id: uuid.UUID
    amount: Decimal
    period: str
    currency: str
    spent: Decimal = Decimal("0")
    remaining: Decimal = Decimal("0")
    pct_used: float = 0.0
