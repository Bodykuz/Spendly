"""v1 aggregate router."""

from fastapi import APIRouter

from app.api.v1 import accounts, analytics, auth, banks, budgets, goals, insights, transactions

api_router = APIRouter(prefix="/v1")
api_router.include_router(auth.router)
api_router.include_router(banks.router)
api_router.include_router(accounts.router)
api_router.include_router(transactions.router)
api_router.include_router(analytics.router)
api_router.include_router(insights.router)
api_router.include_router(budgets.router)
api_router.include_router(goals.router)
