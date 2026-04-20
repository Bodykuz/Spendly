"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-04-20
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(254), nullable=False, unique=True, index=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(120)),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("is_verified", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("currency", sa.String(3), nullable=False, server_default="PLN"),
        sa.Column("locale", sa.String(10), nullable=False, server_default="pl_PL"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("slug", sa.String(64), nullable=False),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("icon", sa.String(32), nullable=False, server_default="tag"),
        sa.Column("color", sa.String(9), nullable=False, server_default="#6B7280"),
        sa.Column("is_income", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("is_system", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "slug", name="uq_cat_user_slug"),
    )

    consent_status = postgresql.ENUM(
        "pending", "linked", "expired", "revoked", "error",
        name="consent_status", create_type=True,
    )
    consent_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "bank_connections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("provider_ref", sa.String(128), nullable=False),
        sa.Column("institution_id", sa.String(128), nullable=False),
        sa.Column("institution_name", sa.String(128), nullable=False),
        sa.Column("institution_logo", sa.String(512)),
        sa.Column("institution_country", sa.String(2), nullable=False, server_default="PL"),
        sa.Column("status", consent_status, nullable=False, server_default="pending"),
        sa.Column("consent_expires_at", sa.DateTime(timezone=True)),
        sa.Column("last_synced_at", sa.DateTime(timezone=True)),
        sa.Column("redirect_uri", sa.String(512), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("provider", "provider_ref", name="uq_bank_provider_ref"),
    )
    op.create_index("ix_bank_connections_user_id", "bank_connections", ["user_id"])

    op.create_table(
        "accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("bank_connection_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("bank_connections.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("provider_account_id", sa.String(128), nullable=False),
        sa.Column("iban", sa.String(34)),
        sa.Column("name", sa.String(255)),
        sa.Column("owner_name", sa.String(255)),
        sa.Column("currency", sa.String(3), nullable=False, server_default="PLN"),
        sa.Column("product", sa.String(128)),
        sa.Column("balance_available", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("balance_current", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("balance_updated_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("provider", "provider_account_id", name="uq_account_provider"),
    )
    op.create_index("ix_accounts_bank_connection_id", "accounts", ["bank_connection_id"])
    op.create_index("ix_accounts_iban", "accounts", ["iban"])

    tx_status = postgresql.ENUM("booked", "pending", name="transaction_status", create_type=True)
    tx_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("categories.id", ondelete="SET NULL")),
        sa.Column("provider_transaction_id", sa.String(128), nullable=False),
        sa.Column("internal_hash", sa.String(64), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("booking_date", sa.Date, nullable=False),
        sa.Column("value_date", sa.Date),
        sa.Column("status", tx_status, nullable=False, server_default="booked"),
        sa.Column("counterparty_name", sa.String(255)),
        sa.Column("counterparty_iban", sa.String(34)),
        sa.Column("description", sa.Text),
        sa.Column("raw_reference", sa.String(255)),
        sa.Column("merchant_category_code", sa.String(8)),
        sa.Column("is_recurring", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("is_subscription", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("is_salary", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("user_categorized", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("account_id", "provider_transaction_id", name="uq_tx_account_provider_id"),
    )
    op.create_index("ix_transactions_user_id", "transactions", ["user_id"])
    op.create_index("ix_transactions_account_id", "transactions", ["account_id"])
    op.create_index("ix_transactions_category_id", "transactions", ["category_id"])
    op.create_index("ix_transactions_counterparty_name", "transactions", ["counterparty_name"])
    op.create_index("ix_transactions_internal_hash", "transactions", ["internal_hash"])
    op.create_index("ix_tx_account_booking_date", "transactions", ["account_id", "booking_date"])
    op.create_index("ix_tx_user_booking_date", "transactions", ["user_id", "booking_date"])

    op.create_table(
        "budgets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("categories.id", ondelete="CASCADE"), nullable=False),
        sa.Column("period", sa.String(8), nullable=False, server_default="monthly"),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="PLN"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "category_id", "period", name="uq_budget_user_cat_period"),
    )

    op.create_table(
        "goals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("target_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("current_amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(3), nullable=False, server_default="PLN"),
        sa.Column("target_date", sa.Date),
        sa.Column("icon", sa.String(32), nullable=False, server_default="target"),
        sa.Column("color", sa.String(9), nullable=False, server_default="#6366F1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("goals")
    op.drop_table("budgets")
    op.drop_table("transactions")
    op.execute("DROP TYPE IF EXISTS transaction_status")
    op.drop_table("accounts")
    op.drop_table("bank_connections")
    op.execute("DROP TYPE IF EXISTS consent_status")
    op.drop_table("categories")
    op.drop_table("users")
