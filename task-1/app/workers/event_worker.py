import logging
import os
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, or_, select

from app.db.session import SessionLocal
from app.models import WebhookEvent
from app.services.event_processor import process_event


logger = logging.getLogger(__name__)

MAX_ATTEMPTS = int(os.getenv("MAX_EVENT_ATTEMPTS", "5"))
BASE_RETRY_SECONDS = 2
MAX_RETRY_SECONDS = 300
POLL_INTERVAL_SECONDS = 2


def record_failure(event_id: str, error: Exception):
    """Persist retry information after the processing transaction rolls back."""

    with SessionLocal.begin() as session:
        event = session.scalar(
            select(WebhookEvent)
            .where(WebhookEvent.event_id == event_id)
            .with_for_update()
        )

        if event is None or event.processing_status == "processed":
            return

        event.attempts += 1
        now = datetime.now(timezone.utc)

        if event.attempts >= MAX_ATTEMPTS:
            event.processing_status = "dead_letter"
            event.next_retry_at = None
        else:
            delay = min(
                BASE_RETRY_SECONDS * (2 ** (event.attempts - 1)),
                MAX_RETRY_SECONDS,
            )
            event.processing_status = "retry"
            event.next_retry_at = now + timedelta(seconds=delay)

        event.last_error = str(error)[:2000]

        logger.error(
            "event_processing_failed",
            extra={
                "event_id": event.event_id,
                "attempt": event.attempts,
                "status": event.processing_status,
                "error": event.last_error,
            },
        )


def process_one_event(event_id: str | None = None) -> bool:
    """
    Process one eligible event.

    Returns True if an event was picked up, otherwise False.
    event_id is optional and useful for targeted tests.
    """

    selected_event_id = None

    try:
        with SessionLocal.begin() as session:
            now = datetime.now(timezone.utc)

            eligible = or_(
                WebhookEvent.processing_status == "pending",
                and_(
                    WebhookEvent.processing_status == "retry",
                    WebhookEvent.next_retry_at <= now,
                ),
            )

            query = select(WebhookEvent).where(
                eligible,
                WebhookEvent.attempts < MAX_ATTEMPTS,
            )

            if event_id is not None:
                query = query.where(WebhookEvent.event_id == event_id)

            event = session.scalar(
                query
                .order_by(WebhookEvent.received_at.asc())
                .limit(1)
                .with_for_update(skip_locked=True)
            )

            if event is None:
                return False

            selected_event_id = event.event_id
            event.attempts += 1

            process_event(session, event)

            logger.info(
                "event_processed",
                extra={
                    "event_id": event.event_id,
                    "attempt": event.attempts,
                },
            )

        return True

    except Exception as exc:
        logger.exception(
            "event_processing_exception",
            extra={"event_id": selected_event_id},
        )

        if selected_event_id is not None:
            try:
                record_failure(selected_event_id, exc)
            except Exception:
                logger.exception(
                    "event_retry_persistence_failed",
                    extra={"event_id": selected_event_id},
                )

        return selected_event_id is not None


def run_worker():
    logger.info("callzo_event_worker_started")

    while True:
        picked_up = process_one_event()

        if not picked_up:
            time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    run_worker()