"""Bank connection lifecycle (consent, link, reconnect, remove)."""

from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.errors import NotFound, ProviderError
from app.core.logging import logger
from app.models.bank import BankConnection, ConsentStatus
from app.providers.base import PSD2Provider
from app.schemas.bank import LinkBankRequest, LinkBankResponse


def _provider_status_to_enum(s: str) -> ConsentStatus:
    s = (s or "").upper()
    mapping = {
        "CR": ConsentStatus.PENDING,
        "GC": ConsentStatus.PENDING,  # giving consent
        "UA": ConsentStatus.PENDING,  # undergoing auth
        "GA": ConsentStatus.PENDING,  # granting access
        "LN": ConsentStatus.LINKED,
        "SU": ConsentStatus.LINKED,   # suspended but linked
        "EX": ConsentStatus.EXPIRED,
        "RJ": ConsentStatus.REVOKED,
    }
    return mapping.get(s, ConsentStatus.ERROR)


async def list_institutions(provider: PSD2Provider, country: str = "PL"):
    return await provider.list_institutions(country)


async def start_link(
    db: Session,
    provider: PSD2Provider,
    user_id: uuid.UUID,
    data: LinkBankRequest,
) -> LinkBankResponse:
    reference = data.reference or f"u{str(user_id)[:8]}-{secrets.token_hex(6)}"
    try:
        consent = await provider.create_consent(
            institution_id=data.institution_id,
            redirect_uri=str(data.redirect_uri),
            reference=reference,
        )
    except ProviderError:
        raise
    except Exception as exc:
        logger.error("bank_link_failed", error=str(exc))
        raise ProviderError("Failed to initiate bank link.") from exc

    institutions = await provider.list_institutions()
    inst = next((i for i in institutions if i.id == data.institution_id), None)

    connection = BankConnection(
        user_id=user_id,
        provider=provider.name,
        provider_ref=consent.id,
        institution_id=data.institution_id,
        institution_name=inst.name if inst else data.institution_id,
        institution_logo=inst.logo if inst else None,
        institution_country=inst.country if inst else "PL",
        status=ConsentStatus.PENDING,
        consent_expires_at=consent.expires_at,
        redirect_uri=str(data.redirect_uri),
    )
    db.add(connection)
    db.commit()
    db.refresh(connection)

    return LinkBankResponse(
        connection_id=connection.id,
        consent_url=consent.consent_url,
        expires_at=consent.expires_at,
    )


def list_connections(db: Session, user_id: uuid.UUID) -> list[BankConnection]:
    return (
        db.query(BankConnection)
        .filter(BankConnection.user_id == user_id)
        .order_by(BankConnection.created_at.desc())
        .all()
    )


def get_connection(db: Session, user_id: uuid.UUID, connection_id: uuid.UUID) -> BankConnection:
    conn = (
        db.query(BankConnection)
        .filter(BankConnection.id == connection_id, BankConnection.user_id == user_id)
        .first()
    )
    if not conn:
        raise NotFound("Bank connection not found.")
    return conn


async def refresh_consent_status(
    db: Session,
    provider: PSD2Provider,
    connection: BankConnection,
) -> BankConnection:
    remote = await provider.get_consent(connection.provider_ref)
    connection.status = _provider_status_to_enum(remote.status)
    db.commit()
    db.refresh(connection)
    return connection


async def remove_connection(
    db: Session,
    provider: PSD2Provider,
    connection: BankConnection,
) -> None:
    try:
        await provider.revoke_consent(connection.provider_ref)
    except Exception as exc:
        logger.warning("consent_revoke_failed", error=str(exc))
    db.delete(connection)
    db.commit()


async def start_reconnect(
    db: Session,
    provider: PSD2Provider,
    connection: BankConnection,
) -> LinkBankResponse:
    """Create a new consent for the same institution & replace the old ref."""
    reference = f"recon-{str(connection.id)[:8]}-{secrets.token_hex(4)}"
    consent = await provider.create_consent(
        institution_id=connection.institution_id,
        redirect_uri=connection.redirect_uri,
        reference=reference,
    )
    connection.provider_ref = consent.id
    connection.status = ConsentStatus.PENDING
    connection.consent_expires_at = consent.expires_at
    connection.last_synced_at = None
    db.commit()
    db.refresh(connection)
    return LinkBankResponse(
        connection_id=connection.id,
        consent_url=consent.consent_url,
        expires_at=consent.expires_at,
    )


def mark_synced(db: Session, connection: BankConnection) -> None:
    connection.last_synced_at = datetime.now(tz=timezone.utc)
    db.commit()
