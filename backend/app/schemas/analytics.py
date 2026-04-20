"""Analytics & insights schemas."""

from __future__ import annotations

import uuid
from datetime import date as date_type
from decimal import Decimal

from pydantic import BaseModel


class BalanceSummary(BaseModel):
    currency: str
    total_available: Decimal
    total_current: Decimal
    by_bank: list["BankBalance"]


class BankBalance(BaseModel):
    bank_connection_id: uuid.UUID
    institution_name: str
    currency: str
    available: Decimal
    current: Decimal


BalanceSummary.model_rebuild()


class MonthlyCashflow(BaseModel):
    month: str  # YYYY-MM
    income: Decimal
    expense: Decimal  # positive number (absolute)
    net: Decimal


class CashflowResponse(BaseModel):
    currency: str
    months: list[MonthlyCashflow]


class CategorySpend(BaseModel):
    category_id: uuid.UUID | None
    category_name: str
    icon: str
    color: str
    amount: Decimal
    pct_of_total: float


class CategoryBreakdownResponse(BaseModel):
    currency: str
    total: Decimal
    categories: list[CategorySpend]
    start_date: date_type
    end_date: date_type


class DashboardResponse(BaseModel):
    currency: str
    total_balance: Decimal
    month_income: Decimal
    month_expense: Decimal
    month_net: Decimal
    linked_banks: int
    accounts: int
    cashflow: list[MonthlyCashflow]
    top_categories: list[CategorySpend]


class Insight(BaseModel):
    id: str
    kind: str  # recurring, subscription, salary, unusual_expense, budget_warning, savings_tip
    title: str
    body: str
    severity: str  # info | warning | positive
    amount: Decimal | None = None
    currency: str | None = None
    meta: dict = {}
