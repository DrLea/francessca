"""deck alignment: flat subscriptions, lawyer verification, reports,
partners, per-case consent, data consent, deadline reminders

Revision ID: 0006_deck_alignment
Revises: 0005_lawyer_portal
Create Date: 2026-11-08
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006_deck_alignment"
down_revision: Union[str, None] = "0005_lawyer_portal"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TS = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "partners",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False, server_default="university"),
        sa.Column("city", sa.String(128)),
        sa.Column("contact_name", sa.String(255)),
        sa.Column("contact_email", sa.String(320)),
        sa.Column("monthly_fee", sa.Numeric(10, 2), nullable=False, server_default="500"),
        sa.Column("status", sa.String(16), nullable=False, server_default="trial"),
        sa.Column("paid_until", sa.Date),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", TS, server_default=sa.func.now(), nullable=False),
    )

    # --- lawyers: subscription + verification ----------------------------
    with op.batch_alter_table("lawyers") as b:
        b.add_column(sa.Column("trial_ends_at", TS))
        b.add_column(sa.Column("paid_until", sa.Date))
        b.add_column(sa.Column("brak_register_id", sa.String(64)))
        b.add_column(sa.Column("chamber", sa.String(128)))
        b.add_column(sa.Column("admission_date", sa.Date))
        b.add_column(sa.Column("brak_checked_at", TS))
        b.add_column(sa.Column("bea_code_hash", sa.String(128)))
        b.add_column(sa.Column("bea_code_sent_at", TS))
        b.add_column(sa.Column("bea_verified_at", TS))
        b.add_column(
            sa.Column(
                "id_check_status", sa.String(16), nullable=False, server_default="not_started"
            )
        )
        b.add_column(sa.Column("id_checked_at", TS))
        b.add_column(sa.Column("verified_until", sa.Date))
        b.add_column(sa.Column("suspended_at", TS))
        b.add_column(sa.Column("suspension_reason", sa.Text))
        b.add_column(sa.Column("partner_id", sa.Integer))
        b.create_foreign_key(
            "fk_lawyers_partner_id", "partners", ["partner_id"], ["id"], ondelete="SET NULL"
        )
        b.create_index("ix_lawyers_partner_id", ["partner_id"])
        # Per-order allowances are gone: firms pay a flat fee.
        b.drop_column("extra_orders")

    # Lawyers already approved before this change get a fresh 3-month trial.
    op.execute(
        "UPDATE lawyers SET trial_ends_at = CURRENT_TIMESTAMP + INTERVAL '90 days' "
        "WHERE user_id IS NOT NULL AND is_published"
        if op.get_bind().dialect.name == "postgresql"
        else "UPDATE lawyers SET trial_ends_at = datetime('now', '+90 days') "
        "WHERE user_id IS NOT NULL AND is_published = 1"
    )

    op.create_table(
        "lawyer_reports",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "lawyer_id", sa.Integer,
            sa.ForeignKey("lawyers.id", ondelete="CASCADE"), nullable=False, index=True,
        ),
        sa.Column(
            "reporter_id", sa.Integer,
            sa.ForeignKey("users.id", ondelete="SET NULL"), index=True,
        ),
        sa.Column("order_id", sa.Integer, sa.ForeignKey("orders.id", ondelete="SET NULL")),
        sa.Column("reason", sa.String(24), nullable=False),
        sa.Column("details", sa.Text),
        sa.Column("status", sa.String(16), nullable=False, server_default="open", index=True),
        sa.Column("admin_note", sa.Text),
        sa.Column("created_at", TS, server_default=sa.func.now(), nullable=False),
    )

    with op.batch_alter_table("orders") as b:
        b.add_column(sa.Column("consent_at", TS))
        b.add_column(sa.Column("consent_withdrawn_at", TS))
    # Orders sent before consent was recorded were sent deliberately by the
    # client; record that moment as their consent.
    op.execute("UPDATE orders SET consent_at = created_at WHERE consent_at IS NULL")

    with op.batch_alter_table("users") as b:
        b.add_column(sa.Column("data_consent_at", TS))
    # Existing accounts signed up under the old terms; they are asked again
    # in the app (data_consent_at stays NULL until they confirm).

    with op.batch_alter_table("timeline_events") as b:
        b.add_column(sa.Column("reminded_7d_at", TS))
        b.add_column(sa.Column("reminded_1d_at", TS))


def downgrade() -> None:
    with op.batch_alter_table("timeline_events") as b:
        b.drop_column("reminded_1d_at")
        b.drop_column("reminded_7d_at")
    with op.batch_alter_table("users") as b:
        b.drop_column("data_consent_at")
    with op.batch_alter_table("orders") as b:
        b.drop_column("consent_withdrawn_at")
        b.drop_column("consent_at")
    op.drop_table("lawyer_reports")
    with op.batch_alter_table("lawyers") as b:
        b.add_column(sa.Column("extra_orders", sa.Integer, nullable=False, server_default="0"))
        b.drop_index("ix_lawyers_partner_id")
        b.drop_constraint("fk_lawyers_partner_id", type_="foreignkey")
        for col in (
            "partner_id", "suspension_reason", "suspended_at", "verified_until",
            "id_checked_at", "id_check_status", "bea_verified_at", "bea_code_sent_at",
            "bea_code_hash", "brak_checked_at", "admission_date", "chamber",
            "brak_register_id", "paid_until", "trial_ends_at",
        ):
            b.drop_column(col)
    op.drop_table("partners")
