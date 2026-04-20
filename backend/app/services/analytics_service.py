"""Analytics computations (cashflow, breakdowns, dashboard)."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Iterable

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.bank import BankConnection, ConsentStatus
from app.models.category import Category
from app.models.transaction import Transaction
from app.schemas.analytics import (
    BalanceSummary,
    BankBalance,
    CashflowResponse,
    CategoryBreakdownResponse,
    CategorySpend,
    DashboardResponse,
    MonthlyCashflow,
)


def _month_bounds(d: date) -> tuple[date, date]:
    start = d.replace(day=1)
    if d.month == 12:
        nxt = date(d.year + 1, 1, 1)
    else:
        nxt = date(d.year, d.month + 1, 1)
    return start, nxt - timedelta(days=1)


def balance_summary(db: Session, user_id: uuid.UUID, currency: str = "PLN") -> BalanceSummary:
    rows = (
        db.query(
            BankConnection.id,
            BankConnection.institution_name,
            func.coalesce(func.sum(Account.balance_available), 0),
            func.coalesce(func.sum(Account.balance_current), 0),
        )
        .join(Account, Account.bank_connection_id == BankConnection.id)
        .filter(
            BankConnection.user_id == user_id,
            BankConnection.status == ConsentStatus.LINKED,
            Account.currency == currency,
        )
        .group_by(BankConnection.id)
        .all()
    )
    by_bank = [
        BankBalance(
            bank_connection_id=r[0],
            institution_name=r[1],
            currency=currency,
            available=Decimal(r[2]),
            current=Decimal(r[3]),
        )
        for r in rows
    ]
    return BalanceSummary(
        currency=currency,
        total_available=sum((b.available for b in by_bank), start=Decimal("0")),
        total_current=sum((b.current for b in by_bank), start=Decimal("0")),
        by_bank=by_bank,
    )


def monthly_cashflow(
    db: Session, user_id: uuid.UUID, months: int = 6, currency: str = "PLN"
) -> CashflowResponse:
    today = date.today()
    start, _ = _month_bounds(today.replace(day=1) - timedelta(days=30 * (months - 1)))
    dialect = db.bind.dialect.name if db.bind else "postgresql"
    if dialect == "postgresql":
        month_expr = func.to_char(Transaction.booking_date, "YYYY-MM")
    else:  # SQLite / others
        month_expr = func.strftime("%Y-%m", Transaction.booking_date)

    rows = (
        db.query(
            month_expr.label("month"),
            func.sum(case((Transaction.amount > 0, Transaction.amount), else_=0)).label("income"),
            func.sum(case((Transaction.amount < 0, -Transaction.amount), else_=0)).label("expense"),
        )
        .filter(
            Transaction.user_id == user_id,
            Transaction.currency == currency,
            Transaction.booking_date >= start,
            Transaction.booking_date <= today,
        )
        .group_by("month")
        .order_by("month")
        .all()
    )
    by_month = {r[0]: (Decimal(r[1] or 0), Decimal(r[2] or 0)) for r in rows}

    out: list[MonthlyCashflow] = []
    cur = start
    while cur <= today:
        key = cur.strftime("%Y-%m")
        inc, exp = by_month.get(key, (Decimal("0"), Decimal("0")))
        out.append(MonthlyCashflow(month=key, income=inc, expense=exp, net=inc - exp))
        nxt_m = 1 if cur.month == 12 else cur.month + 1
        nxt_y = cur.year + 1 if cur.month == 12 else cur.year
        cur = date(nxt_y, nxt_m, 1)
    return CashflowResponse(currency=currency, months=out)


def category_breakdown(
    db: Session,
    user_id: uuid.UUID,
    start_date: date,
    end_date: date,
    only_expenses: bool = True,
    currency: str = "PLN",
) -> CategoryBreakdownResponse:
    q = (
        db.query(
            Category.id,
            Category.name,
            Category.icon,
            Category.color,
            func.sum(func.abs(Transaction.amount)).label("amount"),
        )
        .outerjoin(Category, Category.id == Transaction.category_id)
        .filter(
            Transaction.user_id == user_id,
            Transaction.currency == currency,
            Transaction.booking_date >= start_date,
            Transaction.booking_date <= end_date,
        )
    )
    if only_expenses:
        q = q.filter(Transaction.amount < 0)
    rows = q.group_by(Category.id, Category.name, Category.icon, Category.color).all()

    total = sum((Decimal(r[4] or 0) for r in rows), start=Decimal("0"))
    items: list[CategorySpend] = []
    for cid, cname, icon, color, amount in rows:
        amt = Decimal(amount or 0)
        items.append(
            CategorySpend(
                category_id=cid,
                category_name=cname or "Uncategorized",
                icon=icon or "tag",
                color=color or "#9CA3AF",
                amount=amt,
                pct_of_total=float(amt / total * 100) if total else 0.0,
            )
        )
    items.sort(key=lambda x: x.amount, reverse=True)
    return CategoryBreakdownResponse(
        currency=currency, total=total, categories=items, start_date=start_date, end_date=end_date
    )


def dashboard(db: Session, user_id: uuid.UUID, currency: str = "PLN") -> DashboardResponse:
    bs = balance_summary(db, user_id, currency)
    today = date.today()
    m_start, m_end = _month_bounds(today)

    row = (
        db.query(
            func.coalesce(
                func.sum(case((Transaction.amount > 0, Transaction.amount), else_=0)), 0
            ),
            func.coalesce(
                func.sum(case((Transaction.amount < 0, -Transaction.amount), else_=0)), 0
            ),
        )
        .filter(
            Transaction.user_id == user_id,
            Transaction.currency == currency,
            Transaction.booking_date >= m_start,
            Transaction.booking_date <= m_end,
        )
        .first()
    )
    income = Decimal(row[0] or 0)
    expense = Decimal(row[1] or 0)

    cashflow = monthly_cashflow(db, user_id, months=6, currency=currency).months
    breakdown = category_breakdown(db, user_id, m_start, m_end, only_expenses=True, currency=currency)

    n_accounts = (
        db.query(func.count(Account.id))
        .join(BankConnection, Account.bank_connection_id == BankConnection.id)
        .filter(BankConnection.user_id == user_id)
        .scalar()
    )

    return DashboardResponse(
        currency=currency,
        total_balance=bs.total_available,
        month_income=income,
        month_expense=expense,
        month_net=income - expense,
        linked_banks=len(bs.by_bank),
        accounts=int(n_accounts or 0),
        cashflow=cashflow,
        top_categories=breakdown.categories[:5],
    )
