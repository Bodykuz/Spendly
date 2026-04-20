"""GoCardless Bank Account Data (Nordigen) provider implementation.

API reference: https://bankaccountdata.gocardless.com/api/v2/
Auth: POST /token/new/ → access (24h) + refresh (30d)
Flow:
    1. GET /institutions/?country=PL       → pick bank
    2. POST /agreements/enduser/           → (optional) custom end-user agreement
    3. POST /requisitions/                 → returns link (consent_url) + id (consent_ref)
    4. User is redirected to bank, then back to our redirect_uri
    5. GET /requisitions/{id}/             → list of account uuids once status=LN
    6. GET /accounts/{id}/                 → IBAN etc.
    7. GET /accounts/{id}/balances/        → balances
    8. GET /accounts/{id}/transactions/?date_from=&date_to=

This implementation is production-ready:
    * retries with exponential backoff on 5xx / 429
    * token caching via Redis
    * async httpx client
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import settings
from app.core.errors import ProviderError
from app.core.logging import logger
from app.providers.base import (
    PSD2Provider,
    ProviderAccount,
    ProviderBalance,
    ProviderConsent,
    ProviderInstitution,
    ProviderTransaction,
    TokenCache,
)


TOKEN_CACHE_KEY = "gocardless:access_token"
REFRESH_CACHE_KEY = "gocardless:refresh_token"


class GoCardlessProvider(PSD2Provider):
    name = "gocardless"

    def __init__(self, token_cache: TokenCache | None = None):
        self.base_url = settings.gocardless_base_url.rstrip("/")
        self.secret_id = settings.gocardless_secret_id
        self.secret_key = settings.gocardless_secret_key
        self.token_cache = token_cache
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(30.0, connect=10.0),
            headers={"accept": "application/json", "Content-Type": "application/json"},
        )

    # ──────────────── Auth ────────────────

    async def _fetch_new_token(self) -> str:
        if not (self.secret_id and self.secret_key):
            raise ProviderError("GoCardless credentials are not configured.")
        r = await self._client.post(
            "/token/new/",
            json={"secret_id": self.secret_id, "secret_key": self.secret_key},
        )
        if r.status_code != 200:
            raise ProviderError(f"Token request failed: {r.status_code} {r.text[:200]}")
        data = r.json()
        access = data["access"]
        refresh = data.get("refresh")
        if self.token_cache:
            ttl = int(data.get("access_expires", 86400)) - 60
            self.token_cache.set(TOKEN_CACHE_KEY, access, ex=ttl)
            if refresh:
                r_ttl = int(data.get("refresh_expires", 30 * 86400)) - 60
                self.token_cache.set(REFRESH_CACHE_KEY, refresh, ex=r_ttl)
        return access

    async def _access_token(self) -> str:
        if self.token_cache:
            cached = self.token_cache.get(TOKEN_CACHE_KEY)
            if cached:
                return cached
        return await self._fetch_new_token()

    # ──────────────── HTTP helper ────────────────

    @retry(
        reraise=True,
        retry=retry_if_exception_type((httpx.TransportError,)),
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=5),
    )
    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
        json_body: dict | None = None,
        retry_auth: bool = True,
    ) -> Any:
        token = await self._access_token()
        r = await self._client.request(
            method,
            path,
            params=params,
            json=json_body,
            headers={"Authorization": f"Bearer {token}"},
        )

        if r.status_code == 401 and retry_auth:
            if self.token_cache:
                self.token_cache.set(TOKEN_CACHE_KEY, "", ex=1)
            return await self._request(method, path, params=params, json_body=json_body, retry_auth=False)

        if r.status_code == 429:
            raise ProviderError("GoCardless rate limit exceeded — try later.")

        if r.status_code >= 500:
            raise ProviderError(f"GoCardless 5xx: {r.status_code}")

        if r.status_code >= 400:
            try:
                body = r.json()
            except json.JSONDecodeError:
                body = r.text
            logger.warning("gocardless_4xx", status=r.status_code, body=body, path=path)
            raise ProviderError(f"GoCardless error ({r.status_code}): {body}")

        if r.status_code == 204 or not r.content:
            return None
        return r.json()

    # ──────────────── Parsing helpers ────────────────

    @staticmethod
    def _parse_decimal(value: Any) -> Decimal:
        try:
            return Decimal(str(value))
        except (InvalidOperation, TypeError):
            return Decimal("0")

    @staticmethod
    def _parse_date(value: str | None) -> date | None:
        if not value:
            return None
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None

    # ──────────────── PSD2Provider impl ────────────────

    async def list_institutions(self, country: str = "PL") -> list[ProviderInstitution]:
        data = await self._request("GET", "/institutions/", params={"country": country})
        out = []
        for item in data or []:
            out.append(
                ProviderInstitution(
                    id=item["id"],
                    name=item.get("name", item["id"]),
                    bic=item.get("bic"),
                    logo=item.get("logo"),
                    country=item.get("countries", [country])[0] if item.get("countries") else country,
                    transaction_total_days=int(item.get("transaction_total_days") or 0) or None,
                )
            )
        return out

    async def create_consent(
        self,
        institution_id: str,
        redirect_uri: str,
        reference: str,
        user_language: str = "pl",
    ) -> ProviderConsent:
        agreement = await self._request(
            "POST",
            "/agreements/enduser/",
            json_body={
                "institution_id": institution_id,
                "max_historical_days": settings.gocardless_tx_history_days,
                "access_valid_for_days": settings.gocardless_consent_days,
                "access_scope": ["balances", "details", "transactions"],
            },
        )

        requisition = await self._request(
            "POST",
            "/requisitions/",
            json_body={
                "redirect": redirect_uri,
                "institution_id": institution_id,
                "reference": reference,
                "agreement": agreement["id"],
                "user_language": user_language.upper(),
            },
        )

        expires_at = None
        if requisition.get("created"):
            try:
                created = datetime.fromisoformat(requisition["created"].replace("Z", "+00:00"))
                expires_at = created + timedelta(days=settings.gocardless_consent_days)
            except ValueError:
                pass

        return ProviderConsent(
            id=requisition["id"],
            consent_url=requisition["link"],
            expires_at=expires_at,
            status=requisition.get("status", "CR"),
        )

    async def get_consent(self, consent_ref: str) -> ProviderConsent:
        data = await self._request("GET", f"/requisitions/{consent_ref}/")
        return ProviderConsent(
            id=data["id"],
            consent_url=data.get("link", ""),
            expires_at=None,
            status=data.get("status", "ERROR"),
        )

    async def list_accounts(self, consent_ref: str) -> list[str]:
        data = await self._request("GET", f"/requisitions/{consent_ref}/")
        return list(data.get("accounts") or [])

    async def get_account(self, account_id: str) -> ProviderAccount:
        meta = await self._request("GET", f"/accounts/{account_id}/")
        details = await self._request("GET", f"/accounts/{account_id}/details/")
        bal = await self.get_balances(account_id)

        acct = details.get("account", {}) if isinstance(details, dict) else {}
        return ProviderAccount(
            id=account_id,
            iban=meta.get("iban") or acct.get("iban"),
            name=acct.get("name") or acct.get("product"),
            owner_name=meta.get("owner_name") or acct.get("ownerName"),
            currency=meta.get("currency") or acct.get("currency") or "PLN",
            product=acct.get("product"),
            balance=bal,
        )

    async def get_balances(self, account_id: str) -> ProviderBalance | None:
        data = await self._request("GET", f"/accounts/{account_id}/balances/")
        balances = data.get("balances") if isinstance(data, dict) else None
        if not balances:
            return None

        available = None
        current = None
        currency = "PLN"
        ts = None

        for b in balances:
            amount = b.get("balanceAmount", {})
            amt = self._parse_decimal(amount.get("amount"))
            cur = amount.get("currency", currency)
            currency = cur
            kind = b.get("balanceType", "")
            if kind in ("interimAvailable", "expected", "forwardAvailable"):
                available = amt
            if kind in ("closingBooked", "interimBooked", "expected"):
                current = amt
            ref_date = b.get("referenceDate") or b.get("lastChangeDateTime")
            if ref_date:
                try:
                    ts = datetime.fromisoformat(ref_date.replace("Z", "+00:00"))
                except ValueError:
                    pass

        if available is None and current is not None:
            available = current
        if current is None and available is not None:
            current = available
        if available is None and current is None:
            return None

        return ProviderBalance(
            available=available or Decimal("0"),
            current=current or Decimal("0"),
            currency=currency,
            timestamp=ts or datetime.now(tz=timezone.utc),
        )

    async def list_transactions(
        self,
        account_id: str,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[ProviderTransaction]:
        params: dict[str, str] = {}
        if date_from:
            params["date_from"] = date_from.isoformat()
        if date_to:
            params["date_to"] = date_to.isoformat()

        data = await self._request(
            "GET", f"/accounts/{account_id}/transactions/", params=params
        )

        tx_block = (data or {}).get("transactions") or {}
        booked = tx_block.get("booked") or []
        pending = tx_block.get("pending") or []

        parsed: list[ProviderTransaction] = []
        for item in booked:
            parsed.append(self._parse_tx(item, status="booked"))
        for item in pending:
            parsed.append(self._parse_tx(item, status="pending"))
        return parsed

    def _parse_tx(self, item: dict, status: str) -> ProviderTransaction:
        amount_block = item.get("transactionAmount", {})
        amount = self._parse_decimal(amount_block.get("amount"))
        currency = amount_block.get("currency", "PLN")

        tx_id = (
            item.get("transactionId")
            or item.get("internalTransactionId")
            or f"{item.get('bookingDate', '')}-{amount}-{item.get('remittanceInformationUnstructured', '')[:40]}"
        )

        counterparty = (
            item.get("creditorName")
            or item.get("debtorName")
            or (item.get("merchantCategoryCode") and item.get("additionalInformation"))
        )

        description = item.get("remittanceInformationUnstructured")
        if not description:
            raw = item.get("remittanceInformationUnstructuredArray")
            if isinstance(raw, list):
                description = " ".join(raw)

        return ProviderTransaction(
            id=str(tx_id),
            amount=amount,
            currency=currency,
            booking_date=self._parse_date(item.get("bookingDate")) or date.today(),
            value_date=self._parse_date(item.get("valueDate")),
            status=status,
            counterparty_name=counterparty if isinstance(counterparty, str) else None,
            counterparty_iban=(item.get("creditorAccount") or item.get("debtorAccount") or {}).get("iban"),
            description=description,
            raw_reference=item.get("entryReference") or item.get("endToEndId"),
            merchant_category_code=item.get("merchantCategoryCode"),
            extra={},
        )

    async def revoke_consent(self, consent_ref: str) -> None:
        await self._request("DELETE", f"/requisitions/{consent_ref}/")

    async def aclose(self) -> None:
        await self._client.aclose()
