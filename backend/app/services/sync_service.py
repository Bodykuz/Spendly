"""Transaction & balance sync orchestrator.

Called from:
    * POST /v1/banks/{id}/sync       (on-demand)
    * Celery beat                    (nightly full refresh)
    * After the /callback sets a connection to LINKED
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.core.errors import ProviderError
from app.core.logging import logger
from app.models.account import Account
from app.models.bank import BankConnection, ConsentStatus
from app.models.transaction import Transaction, TransactionStatus
from app.providers.base import PSD2Provider, ProviderTransaction
from app.services.bank_service import _provider_status_to_enum, mark_synced
from app.services.categorization import categorize_transactions


def _hash_tx(account_id: uuid.UUID, tx: ProviderTransaction) -> str:
    payload = (
        f"{account_id}|{tx.id}|{tx.amount}|{tx.currency}|{tx.booking_date}|"
        f"{tx.counterparty_name or ''}|{tx.description or ''}"
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


async def sync_connection(
    db: Session, provider: PSD2Provider, connection: BankConnection, *, full: bool = False
) -> dict:
    """Pull accounts, balances and transactions for a connection."""
    consent = await provider.get_consent(connection.provider_ref)
    connection.status = _provider_status_to_enum(consent.status)
    db.commit()

    if connection.status != ConsentStatus.LINKED:
        logger.info("skip_sync_not_linked", status=connection.status.value)
        return {"accounts": 0, "transactions": 0, "skipped": True}

    remote_ids = await provider.list_accounts(connection.provider_ref)
    accounts_touched = 0
    tx_count = 0

    for provider_acc_id in remote_ids:
        account = _ensure_account(db, connection, provider_acc_id)
        meta = await provider.get_account(provider_acc_id)
        account.iban = meta.iban or account.iban
        account.name = meta.name or account.name
        account.owner_name = meta.owner_name or account.owner_name
        account.currency = meta.currency or account.currency
        account.product = meta.product or account.product

        if meta.balance:
            account.balance_available = meta.balance.available
            account.balance_current = meta.balance.current
            account.balance_updated_at = meta.balance.timestamp or datetime.now(tz=timezone.utc)
            account.currency = meta.balance.currency or account.currency

        date_from = None if full else _last_booking_date(db, account.id)
        if not date_from:
            date_from = (datetime.now(tz=timezone.utc) - timedelta(days=730)).date()

        remote_txs = await provider.list_transactions(
            provider_acc_id,
            date_from=date_from,
            date_to=date.today(),
        )
        tx_count += _upsert_transactions(db, connection.user_id, account, remote_txs)
        accounts_touched += 1

    db.commit()

    new_txs = (
        db.query(Transaction)
        .join(Account, Transaction.account_id == Account.id)
        .join(BankConnection, Account.bank_connection_id == BankConnection.id)
        .filter(
            BankConnection.id == connection.id,
            Transaction.category_id.is_(None),
        )
        .all()
    )
    categorize_transactions(db, new_txs, connection.user_id)
    db.commit()

    mark_synced(db, connection)
    return {"accounts": accounts_touched, "transactions": tx_count, "skipped": False}


def _ensure_account(db: Session, connection: BankConnection, provider_acc_id: str) -> Account:
    account = (
        db.query(Account)
        .filter(
            Account.provider == connection.provider,
            Account.provider_account_id == provider_acc_id,
        )
        .first()
    )
    if account:
        return account
    account = Account(
        bank_connection_id=connection.id,
        provider=connection.provider,
        provider_account_id=provider_acc_id,
        balance_available=Decimal("0"),
        balance_current=Decimal("0"),
    )
    db.add(account)
    db.flush()
    return account


def _last_booking_date(db: Session, account_id: uuid.UUID) -> date | None:
    stmt = (
        select(Transaction.booking_date)
        .where(Transaction.account_id == account_id)
        .order_by(Transaction.booking_date.desc())
        .limit(1)
    )
    row = db.execute(stmt).first()
    if not row:
        return None
    # give a tiny overlap to re-classify pending → booked
    return row[0] - timedelta(days=3)


def _upsert_transactions(
    db: Session,
    user_id: uuid.UUID,
    account: Account,
    remote_txs: list[ProviderTransaction],
) -> int:
    if not remote_txs:
        return 0

    rows = []
    for tx in remote_txs:
        rows.append(
            dict(
                id=uuid.uuid4(),
                user_id=user_id,
                account_id=account.id,
                provider_transaction_id=tx.id,
                internal_hash=_hash_tx(account.id, tx),
                amount=tx.amount,
                currency=tx.currency,
                booking_date=tx.booking_date,
                value_date=tx.value_date,
                status=TransactionStatus.BOOKED if tx.status == "booked" else TransactionStatus.PENDING,
                counterparty_name=tx.counterparty_name,
                counterparty_iban=tx.counterparty_iban,
                description=tx.description,
                raw_reference=tx.raw_reference,
                merchant_category_code=tx.merchant_category_code,
            )
        )

    dialect = db.bind.dialect.name if db.bind else "postgresql"
    insert = pg_insert if dialect == "postgresql" else sqlite_insert
    stmt = insert(Transaction.__table__).values(rows)
    update_set = {
        "amount": stmt.excluded.amount,
        "status": stmt.excluded.status,
        "counterparty_name": stmt.excluded.counterparty_name,
        "description": stmt.excluded.description,
        "updated_at": datetime.now(tz=timezone.utc),
    }
    if dialect == "postgresql":
        stmt = stmt.on_conflict_do_update(
            constraint="uq_tx_account_provider_id", set_=update_set
        )
    else:
        stmt = stmt.on_conflict_do_update(
            index_elements=["account_id", "provider_transaction_id"], set_=update_set
        )
    try:
        db.execute(stmt)
    except Exception as exc:
        logger.error("tx_upsert_failed", error=str(exc), n=len(rows))
        raise ProviderError("Failed to store transactions.") from exc
    return len(rows)
