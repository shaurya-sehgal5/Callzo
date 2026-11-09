import uuid
from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MonthlyUsage(Base):
    __tablename__ = "monthly_usage"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    account_id: Mapped[str] = mapped_column(
        ForeignKey("accounts.id"),
        nullable=False,
    )

    billing_month: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    total_calls: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    total_duration_seconds: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        nullable=False,
    )

    total_cost_cents: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "account_id",
            "billing_month",
            name="uq_monthly_usage_account_month",
        ),
    )