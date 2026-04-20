# Architecture

## Overview

```
┌────────────────┐   HTTPS/JWT    ┌─────────────────────┐
│  iOS (SwiftUI) │ ─────────────▶ │  FastAPI backend    │
│  Keychain +    │                │  (stateless API)    │
│  ASWebAuth     │◀── redirect ───│                     │
└────────────────┘                └──┬────────┬─────┬───┘
                                     │        │     │
                              ┌──────▼──┐ ┌───▼─┐ ┌─▼────────────┐
                              │Postgres │ │Redis│ │ Celery worker│
                              └─────────┘ └─────┘ │  + beat      │
                                                  └──────┬───────┘
                                                         ▼
                                         ┌─────────────────────────┐
                                         │ PSD2Provider interface  │
                                         │   GoCardlessProvider    │
                                         │   (mockable)            │
                                         └────────────┬────────────┘
                                                      ▼
                                   GoCardless Bank Account Data (PSD2 AISP)
                                                      ▼
                                                 Polish banks
```

## PSD2 provider: GoCardless Bank Account Data

| Reason | Notes |
|---|---|
| **Coverage** | ~30 PL banks incl. all top 10 |
| **License** | Regulated PSD2 AISP (passported EU) |
| **Pricing** | Free for production, unlimited end users |
| **API** | REST, aligned with Berlin Group (balances, details, transactions) |
| **Consent** | Up to 90-day requisitions, 24-month transaction history |
| **Status** | Stable, well-documented |

Swap-out path: implement the `PSD2Provider` interface in
`backend/app/providers/base.py` for Kontomatik / Tink / Salt Edge. Set
`PSD2_PROVIDER=<name>` and wire it in `factory.py`. No changes elsewhere.

## Request flow — linking a bank

```
iOS                    Backend                    GoCardless              User's bank
 │                        │                           │                        │
 │ POST /v1/banks/link    │                           │                        │
 │ (institution_id, redirect=spendly://callback)      │                        │
 │───────────────────────▶│                           │                        │
 │                        │ POST /agreements/enduser/ │                        │
 │                        │──────────────────────────▶│                        │
 │                        │ POST /requisitions/       │                        │
 │                        │──────────────────────────▶│                        │
 │                        │  ◀── consent_url ─────────│                        │
 │◀─ {connection_id,      │                           │                        │
 │    consent_url} ───────│                           │                        │
 │                                                                             │
 │ ASWebAuthenticationSession(consent_url, callbackURLScheme:"spendly")        │
 │────────────────────────────────────────────────────────────────────────────▶│
 │ User authorises in bank, bank redirects to backend's /callback?ref=<id>     │
 │◀──── HTTP 302 → https://api/callback?ref=<id> ──────────────────────────────│
 │                        │                                                    │
 │                        │ GET /requisitions/<id>/  → status LN               │
 │                        │ → status=LINKED in DB                              │
 │                        │ → schedule background sync                         │
 │                        │ → redirect Location: spendly://bank/callback?...   │
 │◀──────── deep link ────│                                                    │
 │                                                                             │
 │ iOS: env.onOpenURL → refresh BanksView                                      │
```

## Data model

- `users` → owns everything
- `bank_connections` → one **consent** (requisition) per institution per user
- `accounts` → bank accounts behind one connection
- `transactions` → canonical schema (signed amount, booking date, status, counterparty)
- `categories` → system seed + user overrides
- `budgets`, `goals`

Indexes tuned for the main queries:

- list transactions by user+booking_date desc
- list transactions by account+booking_date desc
- category breakdown joins

## Security

- JWT access (60 min) + refresh (30 days), signed with HS256
- Passwords hashed with bcrypt
- iOS stores tokens in the Keychain with `kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly`
- **No bank credentials ever touch our servers or the app** — the whole auth flow stays inside the aggregator + bank
- ASWebAuthenticationSession isolates the consent web view from the app
- PSD2 Berlin Group — read-only AISP consent, no payment initiation
- Background worker holds no user tokens; it uses only our DB + GoCardless app-level token (cached in Redis)

## Scaling the sync

- GoCardless imposes 4 syncs/account/day
- Nightly Celery beat queues `sync_bank_connection(id)` for every `LINKED` connection
- On-demand sync endpoint for user-pull-to-refresh — safe because we incrementally fetch from `last_booking_date - 3 days`
- Horizontally scalable Celery workers behind one Redis broker
- Future: partition transactions by user_id if >10M rows
