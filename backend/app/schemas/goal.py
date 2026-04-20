"""Savings goal schemas."""

from __future__ import annotations

import uuid
from datetime import date as date_type
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class GoalCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    target_amount: Decimal = Field(gt=0)
    currency: str = "PLN"
    target_date: date_type | None = None
    icon: str = "target"
    color: str = "#6366F1"


class GoalUpdate(BaseModel):
    name: str | None = None
    target_amount: Decimal | None = Field(default=None, gt=0)
    current_amount: Decimal | None = None
    target_date: date_type | None = None
    icon: str | None = None
    color: str | None = None


class GoalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    target_amount: Decimal
    current_amount: Decimal
    currency: str
    target_date: date_type | None
    icon: str
    color: str
    pct_complete: float = 0.0
