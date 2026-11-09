import hashlib
import hmac

from app.core.security import verify_webhook_signature


SECRET = "callzo_test_secret_change_me"


def create_signature(payload: bytes) -> str:
    return hmac.new(
        SECRET.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()


def test_valid_signature():
    payload = b'{"event_id":"evt_123"}'

    signature = create_signature(payload)

    assert verify_webhook_signature(
        payload,
        signature,
    )


def test_invalid_signature():
    payload = b'{"event_id":"evt_123"}'

    assert not verify_webhook_signature(
        payload,
        "invalid_signature",
    )


def test_missing_signature():
    payload = b'{"event_id":"evt_123"}'

    assert not verify_webhook_signature(
        payload,
        None,
    )


def test_modified_payload():
    original = b'{"event_id":"evt_123"}'
    modified = b'{"event_id":"evt_456"}'

    signature = create_signature(original)

    assert not verify_webhook_signature(
        modified,
        signature,
    )


def test_whitespace_changes_signature():
    original = b'{"event_id":"evt_123"}'
    modified = b'{ "event_id": "evt_123" }'

    signature = create_signature(original)

    assert not verify_webhook_signature(
        modified,
        signature,
    )