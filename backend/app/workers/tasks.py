"""Background tasks for nightly bank sync and insight detection."""

from __future__ import annotations

import asyncio
import uuid

from app.core.logging import logger
from app.database import session_scope
from app.models.bank import BankConnection, ConsentStatus
from app.models.user import User
from app.providers.factory import get_provider
from app.services.insights_service import (
    detect_recurring_and_subscriptions,
    detect_salary,
)
from app.services.sync_service import sync_connection
from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.tasks.sync_bank_connection", bind=True, max_retries=3)
def sync_bank_connection(self, connection_id: str) -> dict:
    """Sync one bank connection (accounts + transactions)."""
    try:
        with session_scope() as db:
            conn = db.get(BankConnection, uuid.UUID(connection_id))
            if not conn:
                return {"error": "not_found"}
            provider = get_provider()
            result = asyncio.run(sync_connection(db, provider, conn))
            logger.info("sync_done", connection_id=connection_id, **result)
            return result
    except Exception as exc:  # noqa: BLE001
        logger.error("sync_failed", error=str(exc), connection_id=connection_id)
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@celery_app.task(name="app.workers.tasks.sync_all_connections")
def sync_all_connections() -> dict:
    with session_scope() as db:
        conns = (
            db.query(BankConnection)
            .filter(BankConnection.status == ConsentStatus.LINKED)
            .all()
        )
    for c in conns:
        sync_bank_connection.delay(str(c.id))
    return {"queued": len(conns)}


@celery_app.task(name="app.workers.tasks.refresh_insights_all_users")
def refresh_insights_all_users() -> dict:
    with session_scope() as db:
        users = db.query(User.id).all()
        for (uid,) in users:
            detect_recurring_and_subscriptions(db, uid)
            detect_salary(db, uid)
    return {"users": len(users)}
