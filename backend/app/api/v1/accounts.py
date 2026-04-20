"""/v1/accounts — linked bank accounts for the current user."""

from __future__ import annotations

from fastapi import APIRouter

from app.deps import CurrentUser, DBSession
from app.models.account import Account
from app.models.bank import BankConnection
from app.schemas.account import AccountOut

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("", response_model=list[AccountOut])
def list_accounts(user: CurrentUser, db: DBSession) -> list[AccountOut]:
    rows = (
        db.query(Account)
        .join(BankConnection, Account.bank_connection_id == BankConnection.id)
        .filter(BankConnection.user_id == user.id)
        .all()
    )
    return [AccountOut.model_validate(a) for a in rows]
