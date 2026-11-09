from datetime import date, datetime, timezone
from sqlalchemy import func, select

from app.models import Account, Call, MonthlyUsage


def get_billing_month(timestamp: datetime) -> date:
    timestamp = timestamp.astimezone(timezone.utc)
    return date(timestamp.year, timestamp.month, 1)


def get_next_month(month: date) -> date:
    if month.month == 12:
        return date(month.year + 1, 1, 1)
    return date(month.year, month.month + 1, 1)


def recalculate_monthly_usage(session, account_id: str, month: date):
    """Rebuild one account's monthly totals from completed calls."""

    account = session.scalar(
        select(Account)
        .where(Account.id == account_id)
        .with_for_update()
    )
    if account is None:
        raise ValueError(f"Account not found: {account_id}")

    next_month = get_next_month(month)

    totals = session.execute(
        select(
            func.count(Call.id),
            func.coalesce(func.sum(Call.duration_seconds), 0),
            func.coalesce(func.sum(Call.cost_cents), 0),
        ).where(
            Call.account_id == account_id,
            Call.status == "ended",
            Call.ended_at >= datetime(
                month.year, month.month, 1, tzinfo=timezone.utc
            ),
            Call.ended_at < datetime(
                next_month.year, next_month.month, 1, tzinfo=timezone.utc
            ),
        )
    ).one()

    usage = session.scalar(
        select(MonthlyUsage)
        .where(
            MonthlyUsage.account_id == account_id,
            MonthlyUsage.billing_month == month,
        )
        .with_for_update()
    )

    if usage is None:
        usage = MonthlyUsage(
            account_id=account_id,
            billing_month=month,
        )
        session.add(usage)

    usage.total_calls = totals[0]
    usage.total_duration_seconds = totals[1]
    usage.total_cost_cents = totals[2]

    session.flush()
    return usage



def check_monthly_cap(
    session,
    account_id: str,
    month: date,
    requested_cost_cents: int,
):
    """Check actual usage plus existing reservations."""

    if requested_cost_cents < 1:
        raise ValueError("Requested cost must be at least 1 cent")

    account = session.scalar(
        select(Account)
        .where(Account.id == account_id)
        .with_for_update()
    )

    if account is None:
        raise ValueError(f"Account not found: {account_id}")

    usage = session.scalar(
        select(MonthlyUsage)
        .where(
            MonthlyUsage.account_id == account_id,
            MonthlyUsage.billing_month == month,
        )
        .with_for_update()
    )

    used = usage.total_cost_cents if usage else 0
    reserved = usage.reserved_cost_cents if usage else 0
    cap = account.monthly_cap_cents

    remaining = max(0, cap - used - reserved)
    projected = used + reserved + requested_cost_cents

    return {
        "allowed": projected <= cap,
        "monthly_cap_cents": cap,
        "used_cents": used,
        "reserved_cents": reserved,
        "remaining_cents": remaining,
        "requested_cost_cents": requested_cost_cents,
        "projected_cost_cents": projected,
    }
