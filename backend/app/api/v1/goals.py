"""/v1/goals — savings goals."""

from __future__ import annotations

import uuid
from decimal import Decimal

from fastapi import APIRouter, status

from app.core.errors import NotFound
from app.deps import CurrentUser, DBSession
from app.models.goal import Goal
from app.schemas.goal import GoalCreate, GoalOut, GoalUpdate

router = APIRouter(prefix="/goals", tags=["goals"])


def _enrich(goal: Goal) -> GoalOut:
    pct = 0.0
    if goal.target_amount:
        pct = float(min(Decimal("1"), goal.current_amount / goal.target_amount) * 100)
    return GoalOut(
        id=goal.id,
        name=goal.name,
        target_amount=goal.target_amount,
        current_amount=goal.current_amount,
        currency=goal.currency,
        target_date=goal.target_date,
        icon=goal.icon,
        color=goal.color,
        pct_complete=pct,
    )


@router.get("", response_model=list[GoalOut])
def list_goals(user: CurrentUser, db: DBSession) -> list[GoalOut]:
    return [_enrich(g) for g in db.query(Goal).filter(Goal.user_id == user.id).all()]


@router.post("", response_model=GoalOut, status_code=status.HTTP_201_CREATED)
def create_goal(payload: GoalCreate, user: CurrentUser, db: DBSession) -> GoalOut:
    g = Goal(
        user_id=user.id,
        name=payload.name,
        target_amount=payload.target_amount,
        currency=payload.currency,
        target_date=payload.target_date,
        icon=payload.icon,
        color=payload.color,
    )
    db.add(g)
    db.commit()
    db.refresh(g)
    return _enrich(g)


@router.patch("/{goal_id}", response_model=GoalOut)
def update_goal(
    goal_id: uuid.UUID, payload: GoalUpdate, user: CurrentUser, db: DBSession
) -> GoalOut:
    g = db.query(Goal).filter(Goal.id == goal_id, Goal.user_id == user.id).first()
    if not g:
        raise NotFound("Goal not found.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(g, field, value)
    db.commit()
    db.refresh(g)
    return _enrich(g)


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_goal(goal_id: uuid.UUID, user: CurrentUser, db: DBSession) -> None:
    g = db.query(Goal).filter(Goal.id == goal_id, Goal.user_id == user.id).first()
    if not g:
        raise NotFound("Goal not found.")
    db.delete(g)
    db.commit()
