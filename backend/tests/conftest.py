"""Pytest config — uses the app's own SQLite engine + provider mocking."""

from __future__ import annotations

import os
from collections.abc import Generator
from datetime import date
from decimal import Decimal

import pytest

os.environ["APP_SECRET_KEY"] = "test-secret-please-change"
os.environ["DATABASE_URL"] = "sqlite:///./_test.sqlite3"

# Clear the settings cache if already imported
from app.config import get_settings  # noqa: E402

get_settings.cache_clear()

from fastapi.testclient import TestClient  # noqa: E402

from app import main  # noqa: E402  — triggers model imports
from app.database import Base, SessionLocal, engine, get_db  # noqa: E402
from app.deps import get_provider  # noqa: E402
from app.providers.base import (  # noqa: E402
    PSD2Provider,
    ProviderAccount,
    ProviderBalance,
    ProviderConsent,
    ProviderInstitution,
    ProviderTransaction,
)


class FakeProvider(PSD2Provider):
    name = "fake"

    async def list_institutions(self, country: str = "PL"):
        return [
            ProviderInstitution(id="PKO_PL", name="PKO BP", country="PL"),
            ProviderInstitution(id="MBANK_PL", name="mBank", country="PL"),
        ]

    async def create_consent(self, institution_id, redirect_uri, reference, user_language="pl"):
        return ProviderConsent(
            id="req-1", consent_url="https://example.com/auth", expires_at=None, status="CR"
        )

    async def get_consent(self, consent_ref):
        return ProviderConsent(id=consent_ref, consent_url="", expires_at=None, status="LN")

    async def list_accounts(self, consent_ref):
        return ["acc-1"]

    async def get_account(self, account_id):
        return ProviderAccount(
            id=account_id,
            iban="PL61109010140000071219812874",
            name="Konto osobiste",
            owner_name="Jan Kowalski",
            currency="PLN",
            product="current",
            balance=ProviderBalance(
                available=Decimal("1000"),
                current=Decimal("1000"),
                currency="PLN",
                timestamp=None,
            ),
        )

    async def get_balances(self, account_id):
        return ProviderBalance(
            available=Decimal("1000"), current=Decimal("1000"), currency="PLN", timestamp=None
        )

    async def list_transactions(self, account_id, date_from=None, date_to=None):
        return [
            ProviderTransaction(
                id="t1",
                amount=Decimal("-42.50"),
                currency="PLN",
                booking_date=date.today(),
                value_date=date.today(),
                status="booked",
                counterparty_name="Biedronka",
                counterparty_iban=None,
                description="Zakupy",
                raw_reference=None,
                merchant_category_code=None,
            ),
            ProviderTransaction(
                id="t2",
                amount=Decimal("5000"),
                currency="PLN",
                booking_date=date.today(),
                value_date=date.today(),
                status="booked",
                counterparty_name="ACME Sp. z o.o.",
                counterparty_iban=None,
                description="Wynagrodzenie",
                raw_reference=None,
                merchant_category_code=None,
            ),
        ]

    async def revoke_consent(self, consent_ref):
        return None


@pytest.fixture(autouse=True)
def _fresh_schema() -> Generator[None, None, None]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session() -> Generator:
    with SessionLocal() as session:
        yield session


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    main.app.dependency_overrides[get_db] = get_db  # identity — uses engine directly
    main.app.dependency_overrides[get_provider] = lambda: FakeProvider()

    with TestClient(main.app) as c:
        yield c

    main.app.dependency_overrides.clear()
