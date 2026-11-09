import json
import logging

from datetime import timezone

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.core.security import verify_webhook_signature
from app.db.session import SessionLocal
from app.models import Account, WebhookEvent
from app.schemas.call_event import CallEvent

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/webhooks/calls")
async def receive_call_event(
    request: Request,
    x_signature: str | None = Header(default=None),
):
    # 1. Read original bytes.
    raw_body = await request.body()

    # 2. Verify signature before parsing the payload.
    if not verify_webhook_signature(raw_body, x_signature):
        logger.warning("Webhook rejected: invalid signature")
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing signature",
        )

    # 3. Parse JSON.
    try:
        payload = json.loads(raw_body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(
            status_code=400,
            detail="Invalid JSON payload",
        )

    # 4. Validate event schema.
    try:
        event = CallEvent.model_validate(payload)
        event.validate_event_consistency()
    except (ValidationError, ValueError) as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        )

    # 5. Normalize timestamp.
    if event.timestamp.tzinfo is None:
        raise HTTPException(
            status_code=422,
            detail="Timestamp must include a timezone",
        )

    event_timestamp = event.timestamp.astimezone(timezone.utc)

    # 6. Persist event atomically.
    with SessionLocal.begin() as session:

        account = session.scalar(
            select(Account).where(
                Account.id == event.account_id
            )
        )

        if account is None:
            raise HTTPException(
                status_code=404,
                detail="Unknown account",
            )

        statement = (
            insert(WebhookEvent)
            .values(
                event_id=event.event_id,
                account_id=event.account_id,
                call_id=event.call_id,
                event_type=event.event_type,
                event_timestamp=event_timestamp,
                payload=payload,
                processing_status="pending",
                attempts=0,
            )
            .on_conflict_do_nothing(
                index_elements=["event_id"]
            )
            .returning(WebhookEvent.event_id)
        )

        inserted_event = session.execute(statement).scalar_one_or_none()

    # 7. Handle duplicate delivery.
    if inserted_event is None:
        logger.info(
            "Duplicate webhook ignored",
            extra={"event_id": event.event_id},
        )

        return {
            "status": "duplicate",
            "event_id": event.event_id,
        }

    logger.info(
        "Webhook accepted",
        extra={
            "event_id": event.event_id,
            "account_id": event.account_id,
            "event_type": event.event_type,
        },
    )

    return {
        "status": "accepted",
        "event_id": event.event_id,
    }