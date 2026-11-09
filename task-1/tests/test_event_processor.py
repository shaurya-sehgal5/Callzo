from datetime import datetime, timezone, timedelta
from uuid import uuid4

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import Call, WebhookEvent
from app.services.event_processor import process_event


def create_event(session, event_type, call_id, timestamp, duration=0, cost=0):
    event = WebhookEvent(
        event_id=f"evt_{uuid4().hex}",
        account_id="acct_001",
        call_id=call_id,
        event_type=event_type,
        event_timestamp=timestamp,
        payload={
            "event_type": event_type,
            "duration_seconds": duration,
            "cost_cents": cost,
            "destination_country": "US",
        },
        processing_status="pending",
        attempts=0,
    )
    session.add(event)
    session.flush()
    return event


def test_started_then_ended():
    call_id = f"call_{uuid4().hex}"
    start = datetime.now(timezone.utc)
    end = start + timedelta(minutes=5)

    with SessionLocal.begin() as session:
        started = create_event(session, "call.started", call_id, start)
        process_event(session, started)

        ended = create_event(
            session, "call.ended", call_id, end,
            duration=300, cost=10,
        )
        call = process_event(session, ended)

        assert call.status == "ended"
        assert call.started_at == start
        assert call.ended_at == end
        assert call.duration_seconds == 300
        assert call.cost_cents == 10


def test_ended_before_started():
    call_id = f"call_{uuid4().hex}"
    start = datetime.now(timezone.utc)
    end = start + timedelta(minutes=5)

    with SessionLocal.begin() as session:
        ended = create_event(
            session, "call.ended", call_id, end,
            duration=300, cost=10,
        )
        call = process_event(session, ended)

        assert call.status == "ended"
        assert call.started_at is None

        started = create_event(session, "call.started", call_id, start)
        call = process_event(session, started)

        assert call.status == "ended"
        assert call.started_at == start
        assert call.ended_at == end


def test_older_event_does_not_overwrite_newer_status():
    call_id = f"call_{uuid4().hex}"
    now = datetime.now(timezone.utc)

    with SessionLocal.begin() as session:
        ended = create_event(
            session, "call.ended", call_id, now,
            duration=300, cost=10,
        )
        process_event(session, ended)

        older_started = create_event(
            session, "call.started", call_id,
            now - timedelta(minutes=5),
        )
        call = process_event(session, older_started)

        assert call.status == "ended"
        assert call.duration_seconds == 300
        assert call.cost_cents == 10