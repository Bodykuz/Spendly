"""Rule-based transaction categorization.

Designed as a pipeline:
    1. Seed system categories per new user
    2. Apply heuristic rules against merchant name / description / MCC
    3. Users can override (sets user_categorized=True, skipped by rules)
"""

from __future__ import annotations

import uuid
from typing import Iterable

from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.transaction import Transaction


# Default category taxonomy (system, duplicated per user so they can rename/delete)
DEFAULT_CATEGORIES: list[dict] = [
    {"slug": "salary",        "name": "Wynagrodzenie",   "icon": "briefcase",   "color": "#10B981", "is_income": True},
    {"slug": "other_income",  "name": "Inne przychody",  "icon": "arrow-down-circle", "color": "#059669", "is_income": True},
    {"slug": "transfer",      "name": "Przelew własny",  "icon": "swap",        "color": "#6B7280", "is_income": False},
    {"slug": "groceries",     "name": "Spożywcze",       "icon": "shopping-cart", "color": "#F59E0B", "is_income": False},
    {"slug": "dining",        "name": "Restauracje",     "icon": "utensils",    "color": "#EF4444", "is_income": False},
    {"slug": "transport",     "name": "Transport",       "icon": "car",         "color": "#3B82F6", "is_income": False},
    {"slug": "fuel",          "name": "Paliwo",          "icon": "fuel",        "color": "#2563EB", "is_income": False},
    {"slug": "housing",       "name": "Mieszkanie",      "icon": "home",        "color": "#8B5CF6", "is_income": False},
    {"slug": "utilities",     "name": "Opłaty / media",  "icon": "bolt",        "color": "#7C3AED", "is_income": False},
    {"slug": "subscriptions", "name": "Subskrypcje",     "icon": "repeat",      "color": "#EC4899", "is_income": False},
    {"slug": "entertainment", "name": "Rozrywka",        "icon": "music",       "color": "#DB2777", "is_income": False},
    {"slug": "shopping",      "name": "Zakupy",          "icon": "bag",         "color": "#F97316", "is_income": False},
    {"slug": "health",        "name": "Zdrowie",         "icon": "heart",       "color": "#14B8A6", "is_income": False},
    {"slug": "travel",        "name": "Podróże",         "icon": "plane",       "color": "#06B6D4", "is_income": False},
    {"slug": "atm",           "name": "Bankomat / gotówka", "icon": "cash",    "color": "#64748B", "is_income": False},
    {"slug": "fees",          "name": "Prowizje / opłaty bankowe", "icon": "receipt", "color": "#475569", "is_income": False},
    {"slug": "taxes",         "name": "Podatki",         "icon": "landmark",    "color": "#0F172A", "is_income": False},
    {"slug": "other",         "name": "Inne",            "icon": "tag",         "color": "#9CA3AF", "is_income": False},
]


# Polish-market-aware keyword rules (lowercase substring → category slug)
RULES: list[tuple[list[str], str]] = [
    # groceries
    (["biedronka", "lidl", "żabka", "zabka", "carrefour", "auchan", "kaufland", "tesco", "netto", "stokrotka", "dino", "aldi", "intermarche", "rossmann"], "groceries"),
    # dining
    (["mcdonald", "kfc", "pizza", "pyszne", "uber eats", "glovo", "bolt food", "wolt", "restauracja", "bistro", "sushi"], "dining"),
    # fuel
    (["orlen", "shell", "bp ", "lotos", "circle k", "moya", "amic"], "fuel"),
    # transport
    (["mpk ", "ztm", "koleo", "intercity", "pkp", "flixbus", "bolt", "uber", "free now", "panek", "traficar"], "transport"),
    # travel
    (["ryanair", "wizz", "lot airlines", "booking.com", "airbnb", "hotel", "expedia", "trivago", "itaka"], "travel"),
    # subscriptions / entertainment
    (["netflix", "spotify", "hbo", "disney+", "disney plus", "apple.com/bill", "apple store", "icloud", "youtube premium", "google one", "tidal", "audible", "prime video", "allegro smart"], "subscriptions"),
    (["kino", "cinema city", "multikino", "steam", "playstation", "nintendo", "xbox"], "entertainment"),
    # utilities / housing
    (["tauron", "pge ", "enea", "orange", "play ", "t-mobile", "plus ", "upc", "netia", "vectra", "inea", "pgnig"], "utilities"),
    (["czynsz", "wspólnota", "spółdzielnia"], "housing"),
    # health
    (["apteka", "medicover", "luxmed", "enel-med", "damian", "cm "], "health"),
    # shopping
    (["allegro", "zalando", "ikea", "h&m", "zara", "mediamarkt", "rtv euro", "x-kom", "morele", "smyk", "cropp", "reserved", "decathlon", "empik"], "shopping"),
    # fees
    (["opłata", "prowizja", "oplata", "fee", "bank charge"], "fees"),
    # taxes / government
    (["urząd skarbowy", "zus ", "us warszawa", "us kraków"], "taxes"),
    # atm
    (["atm", "bankomat", "wypłata gotówki"], "atm"),
    # transfer to self
    (["przelew własny", "przelew wewnetrzny", "internal transfer"], "transfer"),
]

SALARY_HINTS = ["wynagrodzenie", "pensja", "salary", "payroll", "uop", "umowa o prac"]


def seed_default_categories(db: Session, user_id: uuid.UUID) -> None:
    existing = {c.slug for c in db.query(Category.slug).filter(Category.user_id == user_id).all()}
    for c in DEFAULT_CATEGORIES:
        if c["slug"] in existing:
            continue
        db.add(
            Category(
                user_id=user_id,
                slug=c["slug"],
                name=c["name"],
                icon=c["icon"],
                color=c["color"],
                is_income=c["is_income"],
                is_system=True,
            )
        )


def _user_categories(db: Session, user_id: uuid.UUID) -> dict[str, Category]:
    rows = db.query(Category).filter(Category.user_id == user_id).all()
    return {c.slug: c for c in rows}


def _classify(text: str, mcc: str | None, is_credit: bool) -> str:
    t = (text or "").lower()
    if is_credit:
        for kw in SALARY_HINTS:
            if kw in t:
                return "salary"
        return "other_income"

    for keywords, slug in RULES:
        for kw in keywords:
            if kw in t:
                return slug
    return "other"


def categorize_transactions(db: Session, txs: Iterable[Transaction], user_id: uuid.UUID) -> int:
    """Assign category_id for transactions lacking one (unless user_categorized)."""
    cats = _user_categories(db, user_id)
    if not cats:
        seed_default_categories(db, user_id)
        db.flush()
        cats = _user_categories(db, user_id)

    updated = 0
    for tx in txs:
        if tx.user_categorized or tx.category_id is not None:
            continue
        text = " ".join(filter(None, [tx.counterparty_name, tx.description, tx.raw_reference]))
        slug = _classify(text, tx.merchant_category_code, is_credit=tx.amount > 0)
        cat = cats.get(slug) or cats.get("other")
        if cat:
            tx.category_id = cat.id
            if slug == "salary":
                tx.is_salary = True
            updated += 1
    return updated
