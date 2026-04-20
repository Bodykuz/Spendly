"""/v1/transactions — search, filter, paginate, recategorize."""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Query
from sqlalchemy import or_

from app.core.errors import NotFound
from app.deps import CurrentUser, DBSession
from app.models.category import Category
from app.models.transaction import Transaction
from app.schemas.transaction import (
    CategoryOut,
    RecategorizeRequest,
    TransactionOut,
    TransactionPage,
)

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("", response_model=TransactionPage)
def list_transactions(
    user: CurrentUser,
    db: DBSession,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    start_date: date | None = None,
    end_date: date | None = None,
    account_id: uuid.UUID | None = None,
    category_id: uuid.UUID | None = None,
    search: str | None = None,
    only_expenses: bool = False,
    only_income: bool = False,
) -> TransactionPage:
    q = db.query(Transaction).filter(Transaction.user_id == user.id)
    if start_date:
        q = q.filter(Transaction.booking_date >= start_date)
    if end_date:
        q = q.filter(Transaction.booking_date <= end_date)
    if account_id:
        q = q.filter(Transaction.account_id == account_id)
    if category_id:
        q = q.filter(Transaction.category_id == category_id)
    if only_expenses:
        q = q.filter(Transaction.amount < 0)
    if only_income:
        q = q.filter(Transaction.amount > 0)
    if search:
        like = f"%{search.lower()}%"
        q = q.filter(
            or_(
                Transaction.counterparty_name.ilike(like),
                Transaction.description.ilike(like),
                Transaction.raw_reference.ilike(like),
            )
        )

    total = q.count()
    items = (
        q.order_by(Transaction.booking_date.desc(), Transaction.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )
    return TransactionPage(
        items=[TransactionOut.model_validate(t) for t in items],
        total=total,
        page=page,
        size=size,
    )


@router.get("/{tx_id}", response_model=TransactionOut)
def get_transaction(tx_id: uuid.UUID, user: CurrentUser, db: DBSession) -> TransactionOut:
    tx = (
        db.query(Transaction)
        .filter(Transaction.id == tx_id, Transaction.user_id == user.id)
        .first()
    )
    if not tx:
        raise NotFound("Transaction not found.")
    return TransactionOut.model_validate(tx)


@router.patch("/{tx_id}/category", response_model=TransactionOut)
def recategorize(
    tx_id: uuid.UUID,
    payload: RecategorizeRequest,
    user: CurrentUser,
    db: DBSession,
) -> TransactionOut:
    tx = (
        db.query(Transaction)
        .filter(Transaction.id == tx_id, Transaction.user_id == user.id)
        .first()
    )
    if not tx:
        raise NotFound("Transaction not found.")
    if payload.category_id:
        cat = (
            db.query(Category)
            .filter(Category.id == payload.category_id, Category.user_id == user.id)
            .first()
        )
        if not cat:
            raise NotFound("Category not found.")
        tx.category_id = cat.id
    else:
        tx.category_id = None
    tx.user_categorized = True
    db.commit()
    db.refresh(tx)
    return TransactionOut.model_validate(tx)


@router.get("/categories/list", response_model=list[CategoryOut])
def list_categories(user: CurrentUser, db: DBSession) -> list[CategoryOut]:
    cats = (
        db.query(Category)
        .filter(Category.user_id == user.id)
        .order_by(Category.is_income.desc(), Category.name.asc())
        .all()
    )
    return [CategoryOut.model_validate(c) for c in cats]
