
"""add call authorization reservations

Revision ID: 2057f1214935
Revises: 7ce83d5eef6a
"""

from alembic import op
import sqlalchemy as sa


revision = "2057f1214935"
down_revision = "7ce83d5eef6a"
branch_labels = None
depends_on = None


def upgrade():
    # Existing calls receive safe default values.
    op.add_column(
        "calls",
        sa.Column(
            "reserved_cost_cents",
            sa.BigInteger(),
            nullable=False,
            server_default="0",
        ),
    )

    op.add_column(
        "calls",
        sa.Column(
            "reservation_month",
            sa.Date(),
            nullable=True,
        ),
    )

    op.add_column(
        "calls",
        sa.Column(
            "authorization_status",
            sa.String(length=20),
            nullable=False,
            server_default="not_requested",
        ),
    )

    op.add_column(
        "calls",
        sa.Column(
            "authorized_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    op.add_column(
        "monthly_usage",
        sa.Column(
            "reserved_cost_cents",
            sa.BigInteger(),
            nullable=False,
            server_default="0",
        ),
    )

    # Defaults are only needed during migration.
    # SQLAlchemy model defaults handle new records.
    op.alter_column(
        "calls",
        "reserved_cost_cents",
        server_default=None,
    )

    op.alter_column(
        "calls",
        "authorization_status",
        server_default=None,
    )

    op.alter_column(
        "monthly_usage",
        "reserved_cost_cents",
        server_default=None,
    )


def downgrade():
    op.drop_column("monthly_usage", "reserved_cost_cents")
    op.drop_column("calls", "authorized_at")
    op.drop_column("calls", "authorization_status")
    op.drop_column("calls", "reservation_month")
    op.drop_column("calls", "reserved_cost_cents")
