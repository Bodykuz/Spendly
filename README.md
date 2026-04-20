# Spendly — personal finance app for Poland (PSD2)

Production-ready iOS personal finance app that connects to Polish banks through
a licensed PSD2 AISP (GoCardless Bank Account Data / Nordigen), aggregates
balances and transactions across banks, and derives analytics & insights.

**Stack**

- **iOS**: Swift 5.10 + SwiftUI (iOS 17+), Swift Charts, ASWebAuthenticationSession
- **Backend**: FastAPI (Python 3.11) + SQLAlchemy 2 + Alembic
- **Data**: PostgreSQL 16
- **Queue/Cache**: Redis 7 + Celery (workers + beat)
- **PSD2 Provider**: GoCardless Bank Account Data (swappable via `PSD2Provider` adapter)

## Repository layout

```
Spendly/
├── backend/               FastAPI backend, Celery workers, Alembic migrations
├── ios/Spendly/           SwiftUI app (XcodeGen project)
└── docs/                  Architecture, deployment, App Store release notes
```

## Why GoCardless Bank Account Data?

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md). TL;DR: best free PL coverage
(PKO BP, mBank, ING, Santander, Pekao, Millennium, Alior, BNP Paribas, Credit
Agricole, Inteligo, Nest, Velo, Citi Handlowy…), licensed PSD2 AISP, stable
REST API aligned with Berlin Group, 90-day consent + 24-month history.

## Quick start (backend)

```bash
cd backend
cp .env.example .env                # set GOCARDLESS_SECRET_ID / SECRET_KEY
docker compose up --build
# API: http://localhost:8000   Docs: http://localhost:8000/docs
```

## Quick start (iOS)

```bash
cd ios/Spendly
brew install xcodegen
xcodegen generate
open Spendly.xcodeproj
```

Set `API_BASE_URL` in the **Debug** scheme to your local backend (e.g. a
`ngrok` tunnel for device testing, since the bank's redirect needs a public
HTTPS URL for production).

## Feature checklist (MVP)

- [x] Auth: sign up, sign in, JWT (access + refresh), keychain storage
- [x] Institutions list (PL) via aggregator
- [x] Link bank via ASWebAuthenticationSession + consent redirect
- [x] List / reconnect / remove / sync bank connections
- [x] Accounts & balances (total / per bank)
- [x] Transaction feed with search + filters + categories + recategorization
- [x] Rule-based categorization (PL-market tuned) + default taxonomy
- [x] Dashboard: total balance, monthly income/expense/net, 6-mo cashflow, top categories
- [x] Insights: subscriptions, recurring payments, salary, unusual expenses, budget warnings, savings tips
- [x] Budgets per category (monthly) with progress
- [x] Savings goals with progress
- [x] Celery nightly sync + on-demand sync
- [x] Swappable PSD2 provider via `PSD2Provider` adapter
- [x] Deployment: Dockerfile + docker-compose + Alembic migrations
- [x] Tests: FastAPI unit tests with fake provider + iOS unit tests
- [x] App Store release checklist

## Docs

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — full architecture & data flow
- [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) — production deployment
- [`docs/APPSTORE.md`](docs/APPSTORE.md) — App Store release checklist
