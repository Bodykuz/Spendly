"""Derived insights: recurring, subscriptions, salary, unusual expenses,
budget warnings, savings tips.

All insights are computed on-demand from stored transactions (no extra table
required). The detection uses simple but robust heuristics — pluggable for ML
later.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from statistics import mean, stdev

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.budget import Budget
from app.models.category import Category
from app.models.transaction import Transaction
from app.schemas.analytics import Insight


def _normalise_merchant(s: str | None) -> str:
    if not s:
        return ""
    return " ".join(s.strip().lower().split())[:60]


def detect_recurring_and_subscriptions(
    db: Session, user_id: uuid.UUID, months: int = 6
) -> list[Insight]:
    since = date.today() - timedelta(days=months * 31)
    rows = (
        db.query(Transaction)
        .filter(
            Transaction.user_id == user_id,
            Transaction.amount < 0,
            Transaction.booking_date >= since,
        )
        .all()
    )

    by_merchant: dict[str, list[Transaction]] = defaultdict(list)
    for t in rows:
        key = _normalise_merchant(t.counterparty_name) or _normalise_merchant(t.description)
        if not key:
            continue
        by_merchant[key].append(t)

    insights: list[Insight] = []
    updated_flags: list[Transaction] = []

    for key, txs in by_merchant.items():
        if len(txs) < 3:
            continue
        txs_sorted = sorted(txs, key=lambda x: x.booking_date)
        gaps = [
            (txs_sorted[i + 1].booking_date - txs_sorted[i].booking_date).days
            for i in range(len(txs_sorted) - 1)
        ]
        if not gaps:
            continue
        avg_gap = mean(gaps)
        g_std = stdev(gaps) if len(gaps) > 1 else 0
        is_monthly = 24 <= avg_gap <= 34 and g_std <= 6
        is_weekly = 6 <= avg_gap <= 9 and g_std <= 2
        if not (is_monthly or is_weekly):
            continue

        amounts = [abs(t.amount) for t in txs_sorted]
        amt_avg = sum(amounts) / len(amounts)
        amt_var = max(amounts) - min(amounts)
        if amt_avg == 0 or amt_var / amt_avg > Decimal("0.30"):
            continue

        cadence = "monthly" if is_monthly else "weekly"
        is_subscription = cadence == "monthly" and amt_avg < Decimal("300")
        last = txs_sorted[-1]
        currency = last.currency

        for t in txs_sorted:
            if not t.is_recurring or t.is_subscription != is_subscription:
                t.is_recurring = True
                t.is_subscription = is_subscription
                updated_flags.append(t)

        insights.append(
            Insight(
                id=f"rec-{key[:20]}",
                kind="subscription" if is_subscription else "recurring",
                title=(
                    f"Subskrypcja: {last.counterparty_name or key}"
                    if is_subscription
                    else f"Płatność cykliczna: {last.counterparty_name or key}"
                ),
                body=(
                    f"Średnio {amt_avg:.2f} {currency} co {int(avg_gap)} dni "
                    f"(ostatnia: {last.booking_date.isoformat()})"
                ),
                severity="info",
                amount=Decimal(amt_avg),
                currency=currency,
                meta={"cadence": cadence, "occurrences": len(txs_sorted)},
            )
        )

    if updated_flags:
        db.commit()

    return insights


def detect_salary(db: Session, user_id: uuid.UUID, months: int = 4) -> list[Insight]:
    since = date.today() - timedelta(days=months * 31)
    rows = (
        db.query(Transaction)
        .filter(
            Transaction.user_id == user_id,
            Transaction.amount > 0,
            Transaction.booking_date >= since,
        )
        .all()
    )
    by_source: dict[str, list[Transaction]] = defaultdict(list)
    for t in rows:
        key = _normalise_merchant(t.counterparty_name)
        if not key:
            continue
        by_source[key].append(t)

    out: list[Insight] = []
    for key, txs in by_source.items():
        if len(txs) < 2:
            continue
        txs_sorted = sorted(txs, key=lambda x: x.booking_date)
        gaps = [
            (txs_sorted[i + 1].booking_date - txs_sorted[i].booking_date).days
            for i in range(len(txs_sorted) - 1)
        ]
        if not gaps or not (24 <= mean(gaps) <= 34):
            continue
        amounts = [t.amount for t in txs_sorted]
        if mean(amounts) < Decimal("1500"):  # arbitrary salary floor
            continue
        last = txs_sorted[-1]
        for t in txs_sorted:
            t.is_salary = True
        out.append(
            Insight(
                id=f"salary-{key[:20]}",
                kind="salary",
                title=f"Wynagrodzenie: {last.counterparty_name or key}",
                body=f"Wykryliśmy regularne wpływy ok. {mean(amounts):.2f} {last.currency}/miesiąc.",
                severity="positive",
                amount=Decimal(mean(amounts)),
                currency=last.currency,
                meta={"occurrences": len(txs_sorted)},
            )
        )
    if out:
        db.commit()
    return out


def detect_unusual_expenses(db: Session, user_id: uuid.UUID, months: int = 3) -> list[Insight]:
    since = date.today() - timedelta(days=months * 31)
    rows = (
        db.query(Transaction)
        .filter(
            Transaction.user_id == user_id,
            Transaction.amount < 0,
            Transaction.booking_date >= since,
        )
        .all()
    )
    if not rows:
        return []
    amounts = [abs(t.amount) for t in rows]
    avg = sum(amounts) / len(amounts)
    threshold = max(avg * 5, Decimal("500"))

    recent_cutoff = date.today() - timedelta(days=14)
    out = []
    for t in rows:
        if t.booking_date < recent_cutoff:
            continue
        if abs(t.amount) >= threshold:
            out.append(
                Insight(
                    id=f"big-{t.id}",
                    kind="unusual_expense",
                    title=f"Nietypowo duży wydatek: {t.counterparty_name or 'transakcja'}",
                    body=f"{abs(t.amount):.2f} {t.currency} — {t.booking_date.isoformat()}",
                    severity="warning",
                    amount=abs(t.amount),
                    currency=t.currency,
                    meta={"transaction_id": str(t.id)},
                )
            )
    return out[:10]


def budget_warnings(db: Session, user_id: uuid.UUID) -> list[Insight]:
    today = date.today()
    month_start = today.replace(day=1)

    budgets = (
        db.query(Budget, Category)
        .join(Category, Category.id == Budget.category_id)
        .filter(Budget.user_id == user_id)
        .all()
    )

    out: list[Insight] = []
    for budget, category in budgets:
        spent_row = (
            db.query(func.coalesce(func.sum(func.abs(Transaction.amount)), 0))
            .filter(
                Transaction.user_id == user_id,
                Transaction.category_id == category.id,
                Transaction.amount < 0,
                Transaction.booking_date >= month_start,
                Transaction.booking_date <= today,
                Transaction.currency == budget.currency,
            )
            .scalar()
        )
        spent = Decimal(spent_row or 0)
        if budget.amount <= 0:
            continue
        ratio = spent / budget.amount
        if ratio >= Decimal("1"):
            severity, kind, title = "warning", "budget_warning", f"Budżet „{category.name}” przekroczony"
        elif ratio >= Decimal("0.8"):
            severity, kind, title = "warning", "budget_warning", f"Budżet „{category.name}” zbliża się do końca"
        else:
            continue
        out.append(
            Insight(
                id=f"budget-{budget.id}",
                kind=kind,
                title=title,
                body=f"{spent:.2f} / {budget.amount:.2f} {budget.currency} ({ratio * 100:.0f}%)",
                severity=severity,
                amount=spent,
                currency=budget.currency,
                meta={"budget_id": str(budget.id), "category": category.name},
            )
        )
    return out


def savings_tips(db: Session, user_id: uuid.UUID) -> list[Insight]:
    tips: list[Insight] = []

    subs = (
        db.query(func.coalesce(func.sum(func.abs(Transaction.amount)), 0))
        .filter(
            Transaction.user_id == user_id,
            Transaction.is_subscription.is_(True),
            Transaction.booking_date >= date.today() - timedelta(days=31),
        )
        .scalar()
    )
    subs_amt = Decimal(subs or 0)
    if subs_amt >= Decimal("100"):
        tips.append(
            Insight(
                id="tip-subs",
                kind="savings_tip",
                title="Przegląd subskrypcji",
                body=f"W ostatnim miesiącu wydałeś ok. {subs_amt:.2f} PLN na subskrypcje. "
                f"Sprawdź, czy wszystkie są używane.",
                severity="info",
                amount=subs_amt,
                currency="PLN",
            )
        )
    return tips


def all_insights(db: Session, user_id: uuid.UUID) -> list[Insight]:
    out: list[Insight] = []
    out += detect_salary(db, user_id)
    out += detect_recurring_and_subscriptions(db, user_id)
    out += detect_unusual_expenses(db, user_id)
    out += budget_warnings(db, user_id)
    out += savings_tips(db, user_id)
    return out
