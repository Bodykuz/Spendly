# Deployment

This is a reference deployment — any cloud with Postgres + Redis + container
runtime works. Example below uses a managed setup (e.g. AWS RDS + ElastiCache
+ ECS / Fly.io / Railway / Render).

## 1. Prerequisites

- Domain for your backend, e.g. `api.spendly.app`. The PSD2 redirect **must be
  HTTPS** in production (GoCardless rejects http except localhost).
- A GoCardless Bank Account Data account:
  - Sign up at <https://bankaccountdata.gocardless.com/>
  - Create an app → get `Secret ID` and `Secret Key`
  - Whitelist your backend's callback URL: `https://api.spendly.app/callback`
- Managed Postgres 16 + Redis 7

## 2. Environment

Copy `backend/.env.example` and fill:

```
APP_ENV=production
APP_SECRET_KEY=<openssl rand -hex 32>
APP_BASE_URL=https://api.spendly.app
APP_FRONTEND_CALLBACK_SCHEME=spendly
APP_CORS_ORIGINS=https://spendly.app,spendly://callback
DATABASE_URL=postgresql+psycopg2://user:pass@db-host:5432/spendly
REDIS_URL=redis://redis-host:6379/0
CELERY_BROKER_URL=redis://redis-host:6379/1
CELERY_RESULT_BACKEND=redis://redis-host:6379/2
GOCARDLESS_SECRET_ID=...
GOCARDLESS_SECRET_KEY=...
SENTRY_DSN=https://...
```

## 3. Run migrations

```
docker run --rm --env-file .env spendly-backend alembic upgrade head
```

## 4. Services to run

- **api** — `uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4`
- **worker** — `celery -A app.workers.celery_app.celery_app worker -l info`
- **beat** — `celery -A app.workers.celery_app.celery_app beat -l info`

All three run the same Docker image with different commands.

## 5. Reverse proxy

Terminate TLS at your load balancer / ingress. Example Nginx:

```
server {
  listen 443 ssl;
  server_name api.spendly.app;
  ssl_certificate     /etc/letsencrypt/live/api.spendly.app/fullchain.pem;
  ssl_certificate_key /etc/letsencrypt/live/api.spendly.app/privkey.pem;

  location / {
    proxy_pass http://api:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
  }
}
```

## 6. Observability

- Sentry for errors (set `SENTRY_DSN`)
- Structured JSON logs (structlog) — ingest into Datadog / Grafana Loki / ELK
- `/health` returns `{"status":"ok"}` — wire up to your load balancer health check

## 7. Rate limits and provider quotas

- GoCardless: 4 tx-sync calls/account/day + small rate limits on `/token`
- Handled by the provider adapter: access token is cached in Redis,
  429s bubble up as `ProviderError`
- App-level pull-to-refresh is free-throttled to whichever call the user makes

## 8. Zero-downtime deploy

1. Push new image tag
2. Run `alembic upgrade head` as one-off task
3. Rolling update api workers, then Celery worker & beat
4. Monitor Sentry for regressions

## 9. Backup

- Postgres: daily automated snapshots + PITR enabled
- Redis: no backups needed (cache + queue); Celery tasks are idempotent
