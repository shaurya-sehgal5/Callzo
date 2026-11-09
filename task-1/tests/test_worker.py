from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import delete, select

from app.db.session import SessionLocal
from app.models import Call, WebhookEvent
from app.workers.event_worker import process_one_event


def create_pending_event():
    event_id = f"evt_worker_{uuid4().hex}"
    call_id = f"call_worker_{uuid4().hex}"

    with SessionLocal.begin() as session:
        session.add(
            WebhookEvent(
                event_id=event_id,
                account_id="acct_001",
                call_id=call_id,
                event_type="call.started",
                event_timestamp=datetime.now(timezone.utc),
                payload={
                    "event_type": "call.started",
                    "duration_seconds": 0,
                    "cost_cents": 0,
                    "destination_country": "US",
                },
                processing_status="pending",
                attempts=0,
            )
        )

    return event_id, call_id


def test_worker_processes_pending_event():
    event_id, call_id = create_pending_event()

    try:
        assert process_one_event(event_id) is True

        with SessionLocal() as session:
            event = session.get(WebhookEvent, event_id)
            call = session.scalar(
                select(Call).where(Call.call_id == call_id)
            )

            assert event.processing_status == "processed"
            assert event.attempts == 1
            assert call is not None
            assert call.status == "started"

    finally:
        with SessionLocal.begin() as session:
            session.execute(
                delete(Call).where(Call.call_id == call_id)
            )
            session.execute(
                delete(WebhookEvent).where(
                    WebhookEvent.event_id == event_id
                )
            )


def test_worker_schedules_retry_after_failure(monkeypatch):
    event_id, _ = create_pending_event()

    def simulate_failure(session, event):
        raise RuntimeError("Simulated processing failure")

    monkeypatch.setattr(
        "app.workers.event_worker.process_event",
        simulate_failure,
    )

    try:
        assert process_one_event(event_id) is True

        with SessionLocal() as session:
            event = session.get(WebhookEvent, event_id)

            assert event.processing_status == "retry"
            assert event.attempts == 1
            assert event.next_retry_at is not None
            assert event.last_error == "Simulated processing failure"

    finally:
        with SessionLocal.begin() as session:
            session.execute(
                delete(WebhookEvent).where(
                    WebhookEvent.event_id == event_id
                )
            )