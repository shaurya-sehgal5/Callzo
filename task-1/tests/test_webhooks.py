import hashlib
import hmac
import json
import os
import uuid

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

SECRET = os.getenv(
    "WEBHOOK_SECRET",
    "callzo_test_secret_change_me",
)


def signed_request(payload: dict):
    body = json.dumps(payload).encode()

    signature = hmac.new(
        SECRET.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()

    return client.post(
        "/webhooks/calls",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Signature": signature,
        },
    )


def create_event():
    return {
        "event_id": f"evt_{uuid.uuid4().hex}",
        "event_type": "call.started",
        "account_id": "acct_001",
        "call_id": f"call_{uuid.uuid4().hex}",
        "timestamp": "2026-11-09T10:15:30+00:00",
        "duration_seconds": 0,
        "cost_cents": 0,
        "destination_country": "US",
    }


def test_valid_webhook():
    response = signed_request(create_event())

    assert response.status_code == 200
    assert response.json()["status"] == "accepted"


def test_duplicate_webhook():
    event = create_event()

    first = signed_request(event)
    second = signed_request(event)

    assert first.status_code == 200
    assert second.status_code == 200

    assert first.json()["status"] == "accepted"
    assert second.json()["status"] == "duplicate"


def test_invalid_signature():
    response = client.post(
        "/webhooks/calls",
        content=b'{"event_id":"invalid"}',
        headers={
            "Content-Type": "application/json",
            "X-Signature": "wrong",
        },
    )

    assert response.status_code == 401


def test_missing_signature():
    response = client.post(
        "/webhooks/calls",
        json=create_event(),
    )

    assert response.status_code == 401


def test_unknown_event_type():
    event = create_event()
    event["event_type"] = "call.unknown"

    response = signed_request(event)

    assert response.status_code == 422


def test_malformed_json():
    body = b'{"event_id":'

    signature = hmac.new(
        SECRET.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()

    response = client.post(
        "/webhooks/calls",
        content=body,
        headers={"X-Signature": signature},
    )

    assert response.status_code == 400