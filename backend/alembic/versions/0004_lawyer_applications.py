"""lawyer sign-up applications

Revision ID: 0004_lawyer_applications
Revises: 0003_message_questions
Create Date: 2026-08-28
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_lawyer_applications"
down_revision: Union[str, None] = "0003_message_questions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Created explicitly with checkfirst so a retry after a failed run is safe;
# the column below uses create_type=False so create_table does not try to
# create it a second time (see the note in 0002).
application_status = postgresql.ENUM(
    "pending", "approved", "rejected", name="lawyer_application_status"
)


def upgrade() -> None:
    application_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "lawyer_applications",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("law_firm", sa.String(255)),
        sa.Column("city", sa.String(128)),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("phone", sa.String(64)),
        sa.Column("website", sa.String(512)),
        sa.Column("address", sa.Text),
        sa.Column("languages", sa.String(255)),
        sa.Column("specializations", sa.String(512)),
        sa.Column("message", sa.Text),
        sa.Column(
            "status",
            postgresql.ENUM(
                "pending", "approved", "rejected",
                name="lawyer_application_status",
                create_type=False,
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "lawyer_id",
            sa.Integer,
            sa.ForeignKey("lawyers.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_lawyer_applications_status", "lawyer_applications", ["status"]
    )


def downgrade() -> None:
    op.drop_index("ix_lawyer_applications_status", table_name="lawyer_applications")
    op.drop_table("lawyer_applications")
    application_status.drop(op.get_bind(), checkfirst=True)
