"""lawyer portal: lawyer accounts, orders, feedback, reviews

Revision ID: 0005_lawyer_portal
Revises: 0004_lawyer_applications
Create Date: 2026-10-07
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_lawyer_portal"
down_revision: Union[str, None] = "0004_lawyer_applications"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

JSONType = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    # A new enum value cannot be used in the transaction that adds it, and
    # before Postgres 12 could not be added inside one at all — so it gets
    # its own autocommit block. IF NOT EXISTS makes a retry safe.
    if op.get_bind().dialect.name == "postgresql":
        with op.get_context().autocommit_block():
            op.execute("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'lawyer'")

    # --- lawyers: account link, publish flag, richer profile -----------
    op.add_column(
        "lawyers",
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="SET NULL")),
    )
    op.create_unique_constraint("uq_lawyers_user_id", "lawyers", ["user_id"])
    op.add_column(
        "lawyers",
        sa.Column("is_published", sa.Boolean, nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_lawyers_is_published", "lawyers", ["is_published"])
    op.add_column("lawyers", sa.Column("bio", sa.Text))
    op.add_column("lawyers", sa.Column("years_experience", sa.Integer))
    op.add_column("lawyers", sa.Column("consultation_fee", sa.String(128)))
    op.add_column("lawyers", sa.Column("office_hours", sa.String(255)))
    op.add_column(
        "lawyers",
        sa.Column("extra_orders", sa.Integer, nullable=False, server_default="0"),
    )
    op.add_column("lawyers", sa.Column("rating_avg", sa.Float))
    op.add_column(
        "lawyers",
        sa.Column("rating_count", sa.Integer, nullable=False, server_default="0"),
    )

    op.add_column(
        "lawyer_applications",
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="SET NULL")),
    )

    # --- orders ---------------------------------------------------------
    op.create_table(
        "orders",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "client_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "lawyer_id",
            sa.Integer,
            sa.ForeignKey("lawyers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("case_id", sa.Integer, sa.ForeignKey("cases.id", ondelete="SET NULL")),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("message", sa.Text),
        sa.Column("case_title", sa.String(255)),
        sa.Column("case_type", sa.String(64)),
        sa.Column("case_summary", JSONType),
        sa.Column("quality_score", sa.Integer, nullable=False, server_default="0"),
        sa.Column("quality_breakdown", JSONType),
        sa.Column("is_free", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("deal_value", sa.Numeric(12, 2)),
        sa.Column("responded_at", sa.DateTime(timezone=True)),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_orders_client_id", "orders", ["client_id"])
    op.create_index("ix_orders_lawyer_id", "orders", ["lawyer_id"])
    op.create_index("ix_orders_status", "orders", ["status"])

    # --- lawyer feedback ------------------------------------------------
    op.create_table(
        "lawyer_feedback",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "lawyer_id",
            sa.Integer,
            sa.ForeignKey("lawyers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("order_id", sa.Integer, sa.ForeignKey("orders.id", ondelete="SET NULL")),
        sa.Column("category", sa.String(24), nullable=False, server_default="lead_quality"),
        sa.Column("rating", sa.Integer),
        sa.Column("comment", sa.Text, nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="new"),
        sa.Column("admin_note", sa.Text),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_lawyer_feedback_lawyer_id", "lawyer_feedback", ["lawyer_id"])
    op.create_index("ix_lawyer_feedback_status", "lawyer_feedback", ["status"])

    # --- client reviews -------------------------------------------------
    op.create_table(
        "lawyer_reviews",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "order_id",
            sa.Integer,
            sa.ForeignKey("orders.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "lawyer_id",
            sa.Integer,
            sa.ForeignKey("lawyers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("client_id", sa.Integer, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("rating", sa.Integer, nullable=False),
        sa.Column("comment", sa.Text),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_lawyer_reviews_lawyer_id", "lawyer_reviews", ["lawyer_id"])


def downgrade() -> None:
    op.drop_table("lawyer_reviews")
    op.drop_table("lawyer_feedback")
    op.drop_table("orders")
    op.drop_column("lawyer_applications", "user_id")
    for column in (
        "rating_count",
        "rating_avg",
        "extra_orders",
        "office_hours",
        "consultation_fee",
        "years_experience",
        "bio",
    ):
        op.drop_column("lawyers", column)
    op.drop_index("ix_lawyers_is_published", table_name="lawyers")
    op.drop_column("lawyers", "is_published")
    op.drop_constraint("uq_lawyers_user_id", "lawyers", type_="unique")
    op.drop_column("lawyers", "user_id")
    # The 'lawyer' value stays on user_role: Postgres cannot drop an enum
    # value, and leaving it is harmless.
