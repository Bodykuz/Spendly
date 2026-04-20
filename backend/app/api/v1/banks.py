"""/v1/banks — institutions + connections lifecycle + sync trigger."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, Query, status

from app.deps import CurrentUser, DBSession, Provider
from app.schemas.bank import (
    BankConnectionOut,
    InstitutionOut,
    LinkBankRequest,
    LinkBankResponse,
)
from app.services import bank_service
from app.services.sync_service import sync_connection

router = APIRouter(prefix="/banks", tags=["banks"])


@router.get("/institutions", response_model=list[InstitutionOut])
async def institutions(
    provider: Provider,
    country: str = Query(default="PL", min_length=2, max_length=2),
) -> list[InstitutionOut]:
    items = await bank_service.list_institutions(provider, country.upper())
    return [
        InstitutionOut(
            id=i.id,
            name=i.name,
            bic=i.bic,
            logo=i.logo,
            country=i.country,
            transaction_total_days=i.transaction_total_days,
        )
        for i in items
    ]


@router.post("/link", response_model=LinkBankResponse, status_code=status.HTTP_201_CREATED)
async def link_bank(
    payload: LinkBankRequest,
    user: CurrentUser,
    db: DBSession,
    provider: Provider,
) -> LinkBankResponse:
    return await bank_service.start_link(db, provider, user.id, payload)


@router.get("/connections", response_model=list[BankConnectionOut])
def list_connections(user: CurrentUser, db: DBSession) -> list[BankConnectionOut]:
    conns = bank_service.list_connections(db, user.id)
    return [BankConnectionOut.model_validate(c) for c in conns]


@router.get("/connections/{connection_id}", response_model=BankConnectionOut)
async def get_connection(
    connection_id: uuid.UUID,
    user: CurrentUser,
    db: DBSession,
    provider: Provider,
) -> BankConnectionOut:
    conn = bank_service.get_connection(db, user.id, connection_id)
    conn = await bank_service.refresh_consent_status(db, provider, conn)
    return BankConnectionOut.model_validate(conn)


@router.delete("/connections/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_connection(
    connection_id: uuid.UUID,
    user: CurrentUser,
    db: DBSession,
    provider: Provider,
) -> None:
    conn = bank_service.get_connection(db, user.id, connection_id)
    await bank_service.remove_connection(db, provider, conn)


@router.post("/connections/{connection_id}/reconnect", response_model=LinkBankResponse)
async def reconnect(
    connection_id: uuid.UUID,
    user: CurrentUser,
    db: DBSession,
    provider: Provider,
) -> LinkBankResponse:
    conn = bank_service.get_connection(db, user.id, connection_id)
    return await bank_service.start_reconnect(db, provider, conn)


@router.post("/connections/{connection_id}/sync")
async def sync(
    connection_id: uuid.UUID,
    user: CurrentUser,
    db: DBSession,
    provider: Provider,
    background: BackgroundTasks,
    full: bool = False,
) -> dict:
    conn = bank_service.get_connection(db, user.id, connection_id)
    result = await sync_connection(db, provider, conn, full=full)
    return result
