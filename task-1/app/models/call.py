
import uuid
from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Call(Base):
    __tablename__ = "calls"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    account_id: Mapped[str] = mapped_column(
        ForeignKey("accounts.id"), nullable=False
    )
    call_id: Mapped[str] = mapped_column(String(100), nullable=False)

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="unknown"
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    duration_seconds: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    cost_cents: Mapped[int] = mapped_column(
        BigInteger, default=0, nullable=False
    )
    destination_country: Mapped[str | None] = mapped_column(
        String(5), nullable=True
    )

    # Call authorization and cap reservation.
    reserved_cost_cents: Mapped[int] = mapped_column(
        BigInteger, default=0, nullable=False
    )
    reservation_month: Mapped[date | None] = mapped_column(
        Date, nullable=True
    )
    authorization_status: Mapped[str] = mapped_column(
        String(20), default="not_requested", nullable=False
    )
    authorized_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    last_event_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
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
            "call_id",
            name="uq_calls_account_call",
        ),
    )
