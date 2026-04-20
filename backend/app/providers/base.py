"""Abstract PSD2 provider interface.

All provider-specific logic (GoCardless, Kontomatik, Tink, Salt Edge...) must
implement this interface. The rest of the application only depends on the
abstractions here, so providers are fully swappable.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Protocol


# ─── Data transfer objects ────────────────────────────────────────────────


@dataclass(frozen=True)
class ProviderInstitution:
    id: str
    name: str
    bic: str | None = None
    logo: str | None = None
    country: str = "PL"
    transaction_total_days: int | None = None


@dataclass(frozen=True)
class ProviderConsent:
    id: str
    consent_url: str
    expires_at: datetime | None
    status: str


@dataclass(frozen=True)
class ProviderBalance:
    available: Decimal
    current: Decimal
    currency: str
    timestamp: datetime | None


@dataclass(frozen=True)
class ProviderAccount:
    id: str
    iban: str | None
    name: str | None
    owner_name: str | None
    currency: str
    product: str | None
    balance: ProviderBalance | None


@dataclass(frozen=True)
class ProviderTransaction:
    id: str
    amount: Decimal
    currency: str
    booking_date: date
    value_date: date | None
    status: str  # booked | pending
    counterparty_name: str | None
    counterparty_iban: str | None
    description: str | None
    raw_reference: str | None
    merchant_category_code: str | None
    extra: dict = field(default_factory=dict)


# ─── Interface ────────────────────────────────────────────────────────────


class PSD2Provider(ABC):
    """Provider adapter contract.

    Methods must be async. Implementations are free to cache/rate-limit.
    """

    name: str

    @abstractmethod
    async def list_institutions(self, country: str = "PL") -> list[ProviderInstitution]: ...

    @abstractmethod
    async def create_consent(
        self,
        institution_id: str,
        redirect_uri: str,
        reference: str,
        user_language: str = "pl",
    ) -> ProviderConsent: ...

    @abstractmethod
    async def get_consent(self, consent_ref: str) -> ProviderConsent: ...

    @abstractmethod
    async def list_accounts(self, consent_ref: str) -> list[str]:
        """Return provider account IDs linked to a consent."""

    @abstractmethod
    async def get_account(self, account_id: str) -> ProviderAccount: ...

    @abstractmethod
    async def get_balances(self, account_id: str) -> ProviderBalance | None: ...

    @abstractmethod
    async def list_transactions(
        self,
        account_id: str,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[ProviderTransaction]: ...

    @abstractmethod
    async def revoke_consent(self, consent_ref: str) -> None: ...


class TokenCache(Protocol):
    def get(self, key: str) -> str | None: ...
    def set(self, key: str, value: str, ex: int | None = None) -> None: ...
