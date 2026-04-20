"""Bank / institution / connection schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field

from app.models.bank import ConsentStatus


class InstitutionOut(BaseModel):
    id: str
    name: str
    bic: str | None = None
    logo: str | None = None
    country: str = "PL"
    transaction_total_days: int | None = None


class LinkBankRequest(BaseModel):
    institution_id: str = Field(..., description="Provider's institution id")
    redirect_uri: AnyHttpUrl | str = Field(
        ..., description="Mobile deep link the bank will redirect back to (e.g. spendly://callback)"
    )
    reference: str | None = Field(
        default=None, description="Optional client-set reference to correlate callbacks"
    )


class LinkBankResponse(BaseModel):
    connection_id: uuid.UUID
    consent_url: str
    expires_at: datetime | None


class BankConnectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    institution_id: str
    institution_name: str
    institution_logo: str | None
    institution_country: str
    status: ConsentStatus
    consent_expires_at: datetime | None
    last_synced_at: datetime | None
    created_at: datetime
