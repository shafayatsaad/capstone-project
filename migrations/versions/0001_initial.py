"""Initial schema for owners, widgets, submissions, and notification outbox."""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("owners",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("email"))
    op.create_index("ix_owners_email", "owners", ["email"])
    op.create_table("widgets",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("owner_id", sa.String(), sa.ForeignKey("owners.id"), nullable=False),
        sa.Column("type", sa.String(), nullable=False), sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.Text()), sa.Column("fields", sa.JSON()),
        sa.Column("button_text", sa.String()), sa.Column("display_options", sa.JSON()),
        sa.Column("version", sa.Integer(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True)))
    op.create_index("ix_widgets_owner_id", "widgets", ["owner_id"])
    op.create_table("submissions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("widget_id", sa.String(), sa.ForeignKey("widgets.id"), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False), sa.Column("ip_address", sa.String(), nullable=False),
        sa.Column("geo_country", sa.String()), sa.Column("geo_city", sa.String()),
        sa.Column("is_spam", sa.Boolean(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("idempotency_key", sa.String(length=128)),
        sa.UniqueConstraint("widget_id", "idempotency_key", name="uq_submission_widget_idempotency"))
    op.create_index("ix_submissions_widget_id", "submissions", ["widget_id"])
    op.create_index("ix_submissions_created_at", "submissions", ["created_at"])
    op.create_table("notification_jobs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("submission_id", sa.String(), sa.ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("widget_id", sa.String(), nullable=False), sa.Column("status", sa.String(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False), sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_error", sa.Text()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint("submission_id"))
    op.create_index("ix_notification_jobs_submission_id", "notification_jobs", ["submission_id"])
    op.create_index("ix_notification_jobs_status", "notification_jobs", ["status"])
    op.create_index("ix_notification_jobs_next_retry_at", "notification_jobs", ["next_retry_at"])


def downgrade():
    op.drop_table("notification_jobs")
    op.drop_index("ix_submissions_created_at", table_name="submissions")
    op.drop_index("ix_submissions_widget_id", table_name="submissions")
    op.drop_table("submissions")
    op.drop_index("ix_widgets_owner_id", table_name="widgets")
    op.drop_table("widgets")
    op.drop_index("ix_owners_email", table_name="owners")
    op.drop_table("owners")
