"""/v1/insights — derived insights."""

from __future__ import annotations

from fastapi import APIRouter

from app.deps import CurrentUser, DBSession
from app.schemas.analytics import Insight
from app.services import insights_service

router = APIRouter(prefix="/insights", tags=["insights"])


@router.get("", response_model=list[Insight])
def all_insights(user: CurrentUser, db: DBSession) -> list[Insight]:
    return insights_service.all_insights(db, user.id)
