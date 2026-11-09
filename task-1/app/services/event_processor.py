
from datetime import datetime, timezone

from sqlalchemy import select

from app.models import Call, MonthlyUsage, WebhookEvent
from app.services.usage_service import (
    get_billing_month,
    recalculate_monthly_usage,
)


def process_event(session, webhook_event: WebhookEvent) -> Call:
    """
    Process a webhook event and update its corresponding call.

    Handles:
    - Started, ended and failed events
    - Out-of-order and late events
    - Monthly usage recalculation
    - Call authorization reservation release
    - Idempotent event processing
    """

    event = webhook_event.payload

    # Find the existing call and lock it.
    call = session.scalar(
        select(Call)
        .where(
            Call.account_id == webhook_event.account_id,
            Call.call_id == webhook_event.call_id,
        )
        .with_for_update()
    )

    # Create the call if this is its first event.
    if call is None:
        call = Call(
            account_id=webhook_event.account_id,
            call_id=webhook_event.call_id,
            status="unknown",
            duration_seconds=0,
            cost_cents=0,
        )
        session.add(call)
        session.flush()

    # Remember the previous billing month in case a late event
    # changes the call's end timestamp.
    previous_month = (
        get_billing_month(call.ended_at)
        if call.ended_at else None
    )

    event_type = webhook_event.event_type
    event_timestamp = webhook_event.event_timestamp

    # Handle call.started.
    if event_type == "call.started":
        if (
            call.started_at is None
            or event_timestamp < call.started_at
        ):
            call.started_at = event_timestamp

    # Handle call.ended.
    elif event_type == "call.ended":
        if (
            call.ended_at is None
            or event_timestamp > call.ended_at
        ):
            call.ended_at = event_timestamp
            call.duration_seconds = event["duration_seconds"]
            call.cost_cents = event["cost_cents"]
            call.destination_country = event["destination_country"]

    # Handle call.failed.
    elif event_type == "call.failed":
        pass

    # Update the call's status only when the event is newer
    # than the previously processed event.
    if (
        call.last_event_at is None
        or event_timestamp >= call.last_event_at
    ):
        call.last_event_at = event_timestamp

        if event_type == "call.started":
            call.status = "started"

        elif event_type == "call.ended":
            call.status = "ended"

        elif event_type == "call.failed":
            call.status = "failed"

    # Release the estimated cost reservation when a call ends
    # or fails. The reservation is zeroed to prevent double release.
    if event_type in ("call.ended", "call.failed"):
        if (
            call.reserved_cost_cents > 0
            and call.reservation_month is not None
        ):
            reserved_usage = session.scalar(
                select(MonthlyUsage)
                .where(
                    MonthlyUsage.account_id == call.account_id,
                    MonthlyUsage.billing_month == call.reservation_month,
                )
                .with_for_update()
            )

            if reserved_usage is not None:
                reserved_usage.reserved_cost_cents = max(
                    0,
                    reserved_usage.reserved_cost_cents
                    - call.reserved_cost_cents,
                )

            call.reserved_cost_cents = 0

            call.authorization_status = (
                "settled"
                if event_type == "call.ended"
                else "released"
            )

    # Determine the new billing month.
    current_month = (
        get_billing_month(call.ended_at)
        if call.ended_at else None
    )

    # Recalculate both months if a late event changes the month.
    affected_months = {
        month
        for month in (previous_month, current_month)
        if month is not None
    }

    for month in affected_months:
        recalculate_monthly_usage(
            session,
            webhook_event.account_id,
            month,
        )

    # Mark the webhook event as successfully processed.
    webhook_event.processing_status = "processed"
    webhook_event.processed_at = datetime.now(timezone.utc)
    webhook_event.last_error = None

    session.flush()

    return call
