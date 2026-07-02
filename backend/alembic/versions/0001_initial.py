"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-30
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

user_role = sa.Enum("user", "admin", name="user_role")
user_tier = sa.Enum("free", "premium", name="user_tier")
message_role = sa.Enum("user", "assistant", "system", name="message_role")
export_kind = sa.Enum("pdf", "zip", name="export_kind")


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("email", sa.String(320), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255)),
        sa.Column("google_id", sa.String(64), unique=True),
        sa.Column("full_name", sa.String(255)),
        sa.Column("language", sa.String(8), nullable=False, server_default="en"),
        sa.Column("role", user_role, nullable=False, server_default="user"),
        sa.Column("tier", user_tier, nullable=False, server_default="free"),
        sa.Column("token_limit", sa.BigInteger),
        sa.Column("tokens_used", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(255), server_default="New conversation"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_conversations_user_id", "conversations", ["user_id"])

    op.create_table(
        "messages",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("conversation_id", sa.Integer, sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", message_role, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("token_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])

    op.create_table(
        "lawyers",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("source_key", sa.String(64), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("law_firm", sa.String(255)),
        sa.Column("city", sa.String(128)),
        sa.Column("email", sa.String(320)),
        sa.Column("phone", sa.String(64)),
        sa.Column("website", sa.String(512)),
        sa.Column("address", sa.Text),
        sa.Column("photo_url", sa.String(512)),
        sa.Column("profile_url", sa.String(512)),
        sa.Column("languages", sa.String(255)),
        sa.Column("content_hash", sa.String(64)),
        sa.Column("last_synced_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_lawyers_source_key", "lawyers", ["source_key"])
    op.create_index("ix_lawyers_city", "lawyers", ["city"])

    op.create_table(
        "lawyer_specializations",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("lawyer_id", sa.Integer, sa.ForeignKey("lawyers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.UniqueConstraint("lawyer_id", "name", name="uq_lawyer_spec"),
    )
    op.create_index("ix_lawyer_specializations_lawyer_id", "lawyer_specializations", ["lawyer_id"])
    op.create_index("ix_lawyer_specializations_name", "lawyer_specializations", ["name"])

    op.create_table(
        "cases",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("conversation_id", sa.Integer, sa.ForeignKey("conversations.id", ondelete="SET NULL")),
        sa.Column("title", sa.String(255), server_default="Untitled case"),
        sa.Column("case_type", sa.String(64)),
        sa.Column("summary", postgresql.JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_cases_user_id", "cases", ["user_id"])

    op.create_table(
        "documents",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("case_id", sa.Integer, sa.ForeignKey("cases.id", ondelete="SET NULL")),
        sa.Column("filename", sa.String(512), nullable=False),
        sa.Column("stored_path", sa.String(1024), nullable=False),
        sa.Column("size", sa.BigInteger, nullable=False),
        sa.Column("mime", sa.String(128), nullable=False),
        sa.Column("extracted_text", sa.Text),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_documents_user_id", "documents", ["user_id"])

    op.create_table(
        "exports",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("case_id", sa.Integer, sa.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", export_kind),
        sa.Column("filename", sa.String(512), nullable=False),
        sa.Column("stored_path", sa.String(1024), nullable=False),
        sa.Column("size", sa.BigInteger, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_exports_case_id", "exports", ["case_id"])

    op.create_table(
        "token_usage",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("conversation_id", sa.Integer, sa.ForeignKey("conversations.id", ondelete="SET NULL")),
        sa.Column("input_tokens", sa.Integer, server_default="0"),
        sa.Column("output_tokens", sa.Integer, server_default="0"),
        sa.Column("model", sa.String(64), server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_token_usage_user_id", "token_usage", ["user_id"])
    op.create_index("ix_token_usage_created_at", "token_usage", ["created_at"])

    op.create_table(
        "prompt_versions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(128), server_default="francessca-system"),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("is_active", sa.Boolean, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_prompt_versions_is_active", "prompt_versions", ["is_active"])


def downgrade() -> None:
    op.drop_table("prompt_versions")
    op.drop_table("token_usage")
    op.drop_table("exports")
    op.drop_table("documents")
    op.drop_table("cases")
    op.drop_table("lawyer_specializations")
    op.drop_table("lawyers")
    op.drop_table("messages")
    op.drop_table("conversations")
    op.drop_table("users")
    for enum in (export_kind, message_role, user_tier, user_role):
        enum.drop(op.get_bind(), checkfirst=True)
