"""/v1/budgets."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, status
from sqlalchemy import func

from app.core.errors import Conflict, NotFound
from app.deps import CurrentUser, DBSession
from app.models.budget import Budget
from app.models.category import Category
from app.models.transaction import Transaction
from app.schemas.budget import BudgetCreate, BudgetOut, BudgetUpdate

router = APIRouter(prefix="/budgets", tags=["budgets"])


def _enrich(db, user_id: uuid.UUID, budget: Budget) -> BudgetOut:
    today = date.today()
    month_start = today.replace(day=1)
    spent = (
        db.query(func.coalesce(func.sum(func.abs(Transaction.amount)), 0))
        .filter(
            Transaction.user_id == user_id,
            Transaction.category_id == budget.category_id,
            Transaction.amount < 0,
            Transaction.booking_date >= month_start,
            Transaction.booking_date <= today,
            Transaction.currency == budget.currency,
        )
        .scalar()
    )
    spent = Decimal(spent or 0)
    remaining = budget.amount - spent
    pct = float(spent / budget.amount * 100) if budget.amount else 0.0
    return BudgetOut(
        id=budget.id,
        category_id=budget.category_id,
        amount=budget.amount,
        period=budget.period,
        currency=budget.currency,
        spent=spent,
        remaining=remaining,
        pct_used=pct,
    )


@router.get("", response_model=list[BudgetOut])
def list_budgets(user: CurrentUser, db: DBSession) -> list[BudgetOut]:
    rows = db.query(Budget).filter(Budget.user_id == user.id).all()
    return [_enrich(db, user.id, b) for b in rows]


@router.post("", response_model=BudgetOut, status_code=status.HTTP_201_CREATED)
def create_budget(payload: BudgetCreate, user: CurrentUser, db: DBSession) -> BudgetOut:
    cat = (
        db.query(Category)
        .filter(Category.id == payload.category_id, Category.user_id == user.id)
        .first()
    )
    if not cat:
        raise NotFound("Category not found.")
    existing = (
        db.query(Budget)
        .filter(
            Budget.user_id == user.id,
            Budget.category_id == payload.category_id,
            Budget.period == payload.period,
        )
        .first()
    )
    if existing:
        raise Conflict("Budget already exists for this category & period.")
    budget = Budget(
        user_id=user.id,
        category_id=payload.category_id,
        amount=payload.amount,
        period=payload.period,
        currency=payload.currency,
    )
    db.add(budget)
    db.commit()
    db.refresh(budget)
    return _enrich(db, user.id, budget)


@router.patch("/{budget_id}", response_model=BudgetOut)
def update_budget(
    budget_id: uuid.UUID, payload: BudgetUpdate, user: CurrentUser, db: DBSession
) -> BudgetOut:
    b = db.query(Budget).filter(Budget.id == budget_id, Budget.user_id == user.id).first()
    if not b:
        raise NotFound("Budget not found.")
    if payload.amount is not None:
        b.amount = payload.amount
    db.commit()
    db.refresh(b)
    return _enrich(db, user.id, b)


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_budget(budget_id: uuid.UUID, user: CurrentUser, db: DBSession) -> None:
    b = db.query(Budget).filter(Budget.id == budget_id, Budget.user_id == user.id).first()
    if not b:
        raise NotFound("Budget not found.")
    db.delete(b)
    db.commit()
