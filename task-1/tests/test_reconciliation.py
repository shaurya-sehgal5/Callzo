
from datetime import datetime, timezone, date, timedelta
from uuid import uuid4

from app.db.session import SessionLocal
from app.models import WebhookEvent
from app.services.reconciliation_service import reconcile_monthly_usage


def test_reconciliation_rebuilds_usage_from_raw_events():
    now = datetime.now(timezone.utc)
    month = date(now.year, now.month, 1)

    call_id = f"reconcile_{uuid4().hex}"
    started_id = f"evt_{uuid4().hex}"
    ended_id = f"evt_{uuid4().hex}"

    with SessionLocal() as session:
        with session.begin_nested():
            started_event = WebhookEvent(
                event_id=started_id,
                account_id="acct_001",
                call_id=call_id,
                event_type="call.started",
                event_timestamp=now,
                payload={
                    "event_type": "call.started",
                    "duration_seconds": 0,
                    "cost_cents": 0,
                    "destination_country": "US",
                },
                processing_status="pending",
                attempts=0,
            )

            ended_event = WebhookEvent(
                event_id=ended_id,
                account_id="acct_001",
                call_id=call_id,
                event_type="call.ended",
                event_timestamp=now + timedelta(seconds=1),
                payload={
                    "event_type": "call.ended",
                    "duration_seconds": 600,
                    "cost_cents": 20,
                    "destination_country": "US",
                },
                processing_status="pending",
                attempts=0,
            )

            session.add_all([started_event, ended_event])
            session.flush()

            result = reconcile_monthly_usage(
                session,
                "acct_001",
                month,
            )

            first_totals = (
                result.total_calls,
                result.total_duration_seconds,
                result.total_cost_cents,
            )

            assert result.total_calls >= 1
            assert result.total_duration_seconds >= 600
            assert result.total_cost_cents >= 20

            # Running reconciliation again must not double-count.
            result = reconcile_monthly_usage(
                session,
                "acct_001",
                month,
            )

            second_totals = (
                result.total_calls,
                result.total_duration_seconds,
                result.total_cost_cents,
            )

            assert first_totals == second_totals
