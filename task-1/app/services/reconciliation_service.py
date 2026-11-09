from datetime import date
from sqlalchemy import select

from app.models import Account, MonthlyUsage, WebhookEvent


def reconcile_monthly_usage(session, account_id: str, month: date):
    """
    Rebuild monthly usage from raw webhook events.

    The latest event timestamp for each call determines its final state.
    Only calls whose latest event is call.ended contribute to usage.
    """

    account = session.scalar(
        select(Account)
        .where(Account.id == account_id)
        .with_for_update()
    )

    if account is None:
        raise ValueError(f"Account not found: {account_id}")

    events = session.scalars(
        select(WebhookEvent)
        .where(WebhookEvent.account_id == account_id)
        .order_by(
            WebhookEvent.event_timestamp.asc(),
            WebhookEvent.received_at.asc(),
            WebhookEvent.event_id.asc(),
        )
    ).all()

    # Keep the latest event for each call.
    latest_events = {}

    for event in events:
        latest_events[event.call_id] = event

    total_calls = 0
    total_duration = 0
    total_cost = 0

    for event in latest_events.values():
        if event.event_type != "call.ended":
            continue

        event_month = date(
            event.event_timestamp.year,
            event.event_timestamp.month,
            1,
        )

        if event_month != month:
            continue

        total_calls += 1
        total_duration += event.payload["duration_seconds"]
        total_cost += event.payload["cost_cents"]

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

    usage.total_calls = total_calls
    usage.total_duration_seconds = total_duration
    usage.total_cost_cents = total_cost

    session.flush()

    return usage