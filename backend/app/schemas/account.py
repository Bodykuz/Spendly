"""Account schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class AccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    bank_connection_id: uuid.UUID
    iban: str | None
    name: str | None
    owner_name: str | None
    currency: str
    product: str | None
    balance_available: Decimal
    balance_current: Decimal
    balance_updated_at: datetime | None
