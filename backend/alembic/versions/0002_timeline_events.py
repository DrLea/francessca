"""timeline events

Revision ID: 0002_timeline_events
Revises: 0001_initial
Create Date: 2026-07-06
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_timeline_events"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# NOTE: generic sa.Enum(..., create_type=False) silently ignores create_type --
# only the Postgres-specific postgresql.ENUM actually honors that flag. Using
# generic sa.Enum here is what caused the original bug (create_table's own
# auto-create ran a second, unguarded CREATE TYPE after our explicit one).
timeline_source_type = postgresql.ENUM(
    "document", "message", "manual", name="timeline_source_type"
)


def upgrade() -> None:
    bind = op.get_bind()

    # Create the enum type ourselves, guarded by checkfirst=True so this is a
    # no-op if it already exists (e.g. left over from an earlier failed run of
    # this same migration). The column below uses create_type=False so
    # create_table() does not also try to auto-create it -- that double
    # attempt is what made "type ... already exists" fail on every retry.
    timeline_source_type.create(bind, checkfirst=True)

    op.create_table(
        "timeline_events",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("conversation_id", sa.Integer, sa.ForeignKey("conversations.id", ondelete="SET NULL")),
        sa.Column("event_date", sa.Date, nullable=True),
        sa.Column("date_label", sa.String(128), server_default=""),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("is_deadline", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column(
            "source_type",
            postgresql.ENUM(
                "document", "message", "manual",
                name="timeline_source_type",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("source_id", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_timeline_events_user_id", "timeline_events", ["user_id"])
    op.create_index("ix_timeline_events_event_date", "timeline_events", ["event_date"])


def downgrade() -> None:
    op.drop_index("ix_timeline_events_event_date", table_name="timeline_events")
    op.drop_index("ix_timeline_events_user_id", table_name="timeline_events")
    op.drop_table("timeline_events")
    timeline_source_type.drop(op.get_bind(), checkfirst=True)
