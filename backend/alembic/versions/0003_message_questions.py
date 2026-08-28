"""structured clarifying questions on messages

Revision ID: 0003_message_questions
Revises: 0002_timeline_events
Create Date: 2026-08-28
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_message_questions"
down_revision: Union[str, None] = "0002_timeline_events"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Nullable: existing messages simply have no attached questions.
    op.add_column(
        "messages",
        # Generic sa.JSON (not JSONB) to match the model's column type -- we
        # only ever read the whole value back, never query inside it.
        sa.Column("questions", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("messages", "questions")
