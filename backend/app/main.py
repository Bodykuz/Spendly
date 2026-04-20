"""FastAPI application entrypoint."""

from __future__ import annotations

import asyncio
from typing import Any

import sentry_sdk
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from app.api.v1.router import api_router
from app.config import settings
from app.core.errors import AppError
from app.core.logging import configure_logging, logger
from app.database import SessionLocal
from app.models.bank import BankConnection
from app.providers.factory import get_provider
from app.services.bank_service import _provider_status_to_enum
from app.services.sync_service import sync_connection

configure_logging()

if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        traces_sample_rate=0.1,
        profiles_sample_rate=0.1,
        environment=settings.app_env,
    )


app = FastAPI(
    title="Spendly API",
    version="0.1.0",
    description="Personal finance aggregator for Polish banks (PSD2 AISP).",
    docs_url="/docs" if settings.app_debug else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppError)
async def _app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})


@app.exception_handler(HTTPException)
async def _http_exc_handler(_: Request, exc: HTTPException) -> JSONResponse:
    payload: Any = exc.detail
    if isinstance(payload, str):
        payload = {"code": "error", "message": payload}
    return JSONResponse(status_code=exc.status_code, content={"error": payload})


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok", "env": settings.app_env}


@app.get("/", tags=["meta"])
def root() -> dict:
    return {"app": settings.app_name, "version": "0.1.0"}


# ─────────────────────────────────────────────────────────────
# Bank consent callback
#
# The PSD2 provider redirects the user back here after they've
# authenticated in their bank. We:
#   1. Find the BankConnection by ?ref=  (our reference)
#   2. Refresh the consent status from the provider
#   3. If LINKED → kick off sync in the background
#   4. Redirect the user into the mobile app via the custom URL scheme
# ─────────────────────────────────────────────────────────────
@app.get("/callback", tags=["meta"], include_in_schema=False)
async def bank_callback(
    ref: str | None = None,
    error: str | None = None,
    details: str | None = None,
) -> Any:
    provider = get_provider()
    db = SessionLocal()
    scheme = settings.app_frontend_callback_scheme
    try:
        conn: BankConnection | None = None
        if ref:
            conn = (
                db.query(BankConnection)
                .filter(BankConnection.provider_ref == ref)
                .first()
            )

        if conn:
            try:
                remote = await provider.get_consent(conn.provider_ref)
                conn.status = _provider_status_to_enum(remote.status)
                db.commit()
                if conn.status.value == "linked":
                    asyncio.create_task(_background_sync(conn.id))
            except Exception as exc:
                logger.warning("callback_status_refresh_failed", error=str(exc))

        status_val = conn.status.value if conn else "error"
        deep_link = f"{scheme}://bank/callback?status={status_val}"
        if conn:
            deep_link += f"&connection_id={conn.id}"
        if error:
            deep_link += f"&error={error}"

        return HTMLResponse(
            f"""
            <!doctype html><html><head>
            <meta charset="utf-8"/>
            <meta name="viewport" content="width=device-width,initial-scale=1"/>
            <title>Spendly</title></head>
            <body style="font-family:-apple-system,Helvetica,Arial,sans-serif;padding:24px;text-align:center;">
              <h2>Łączymy Twój bank ze Spendly…</h2>
              <p>Jeśli aplikacja nie otworzy się automatycznie, kliknij poniżej.</p>
              <p><a href="{deep_link}">Otwórz w Spendly</a></p>
              <script>window.location.replace({deep_link!r});</script>
            </body></html>
            """
        )
    finally:
        db.close()


async def _background_sync(connection_id) -> None:
    db = SessionLocal()
    try:
        conn = db.get(BankConnection, connection_id)
        if conn:
            await sync_connection(db, get_provider(), conn)
    except Exception as exc:
        logger.error("background_sync_failed", error=str(exc))
    finally:
        db.close()


app.include_router(api_router)
