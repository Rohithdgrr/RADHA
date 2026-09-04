"""init users, council_sessions, model_responses

Revision ID: 001
Revises: 
Create Date: 2026-09-04
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_login", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lmarena_token", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_created", "users", ["created_at"])

    op.create_table(
        "council_sessions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("user_query", sa.Text(), nullable=False),
        sa.Column("selected_models", sa.JSON(), nullable=False),
        sa.Column("chairman_model", sa.String(length=50), nullable=False),
        sa.Column("mode", sa.String(length=20), nullable=False, server_default="consensus"),
        sa.Column("depth", sa.String(length=20), nullable=False, server_default="detailed"),
        sa.Column("show_reasoning", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("synthesis", sa.Text(), nullable=True),
        sa.Column("agreements", sa.Text(), nullable=True),
        sa.Column("divergences", sa.Text(), nullable=True),
        sa.Column("unique_insights", sa.JSON(), nullable=True),
        sa.Column("deliberation_log", sa.JSON(), nullable=True),
        sa.Column("total_latency", sa.Float(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="running"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_sessions_user_id", "council_sessions", ["user_id"])
    op.create_index("ix_sessions_created", "council_sessions", ["created_at"])
    op.create_index("ix_sessions_status", "council_sessions", ["status"])
    op.create_index("ix_sessions_mode", "council_sessions", ["mode"])

    op.create_table(
        "model_responses",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("session_id", sa.String(length=36), sa.ForeignKey("council_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("model_name", sa.String(length=50), nullable=False),
        sa.Column("reasoning", sa.Text(), nullable=True),
        sa.Column("final_answer", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("latency", sa.Float(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="done"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("critique", sa.Text(), nullable=True),
        sa.Column("critique_score", sa.Float(), nullable=True),
        sa.Column("raw_payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("session_id", "model_name", name="ux_responses_session_model"),
    )
    op.create_index("ix_responses_session", "model_responses", ["session_id"])
    op.create_index("ix_responses_model", "model_responses", ["model_name"])
    op.create_index("ix_responses_status", "model_responses", ["status"])


def downgrade() -> None:
    op.drop_index("ix_responses_status", table_name="model_responses")
    op.drop_index("ix_responses_model", table_name="model_responses")
    op.drop_index("ix_responses_session", table_name="model_responses")
    op.drop_table("model_responses")

    op.drop_index("ix_sessions_mode", table_name="council_sessions")
    op.drop_index("ix_sessions_status", table_name="council_sessions")
    op.drop_index("ix_sessions_created", table_name="council_sessions")
    op.drop_index("ix_sessions_user_id", table_name="council_sessions")
    op.drop_table("council_sessions")

    op.drop_index("ix_users_created", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
