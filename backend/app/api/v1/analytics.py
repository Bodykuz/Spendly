"""/v1/analytics — dashboard, balances, cashflow, breakdown."""

from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Query

from app.deps import CurrentUser, DBSession
from app.schemas.analytics import (
    BalanceSummary,
    CashflowResponse,
    CategoryBreakdownResponse,
    DashboardResponse,
)
from app.services import analytics_service

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/dashboard", response_model=DashboardResponse)
def dashboard(
    user: CurrentUser,
    db: DBSession,
    currency: str = Query(default="PLN", min_length=3, max_length=3),
) -> DashboardResponse:
    return analytics_service.dashboard(db, user.id, currency.upper())


@router.get("/balance", response_model=BalanceSummary)
def balance(
    user: CurrentUser,
    db: DBSession,
    currency: str = Query(default="PLN"),
) -> BalanceSummary:
    return analytics_service.balance_summary(db, user.id, currency.upper())


@router.get("/cashflow", response_model=CashflowResponse)
def cashflow(
    user: CurrentUser,
    db: DBSession,
    months: int = Query(default=6, ge=1, le=24),
    currency: str = Query(default="PLN"),
) -> CashflowResponse:
    return analytics_service.monthly_cashflow(db, user.id, months, currency.upper())


@router.get("/categories", response_model=CategoryBreakdownResponse)
def categories(
    user: CurrentUser,
    db: DBSession,
    start_date: date | None = None,
    end_date: date | None = None,
    only_expenses: bool = True,
    currency: str = Query(default="PLN"),
) -> CategoryBreakdownResponse:
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date.replace(day=1)
    return analytics_service.category_breakdown(
        db, user.id, start_date, end_date, only_expenses, currency.upper()
    )
