import hashlib
import hmac
import json
import os
import time
import uuid
from datetime import datetime, timedelta, timezone

import httpx
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "http://localhost:8080"
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
API_TOKEN = os.getenv("API_TOKEN")

if not WEBHOOK_SECRET or not API_TOKEN:
    raise RuntimeError("WEBHOOK_SECRET or API_TOKEN missing from .env")


def make_event(event_type, account_id, call_id, timestamp,
               duration=0, cost=0, event_id=None):
    return {
        "event_id": event_id or f"local-{uuid.uuid4().hex}",
        "event_type": event_type,
        "account_id": account_id,
        "call_id": call_id,
        "timestamp": timestamp.isoformat(),
        "duration_seconds": duration,
        "cost_cents": cost,
        "destination_country": "US",
    }


def send_webhook(client, payload, bad_signature=False, raw=None):
    body = raw if raw is not None else json.dumps(
        payload, separators=(",", ":")
    ).encode()

    signature = hmac.new(
        WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()

    if bad_signature:
        signature = "invalid_signature"

    return client.post(
        f"{BASE_URL}/webhooks/calls",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Signature": signature,
        },
    )


def report(name, passed, detail=""):
    print(
        f"[{'PASS' if passed else 'FAIL'}] {name}"
        + (f" - {detail}" if detail else "")
    )


def run():
    results = []
    now = datetime.now(timezone.utc)

    with httpx.Client(timeout=20) as client:

        print("\n========== 1. NORMAL CALL ==========")

        call_id = f"normal-{uuid.uuid4().hex[:12]}"

        started = make_event(
            "call.started", "acct_001", call_id, now
        )
        ended = make_event(
            "call.ended", "acct_001", call_id,
            now + timedelta(seconds=60), 60, 2
        )

        r1 = send_webhook(client, started)
        r2 = send_webhook(client, ended)

        ok = r1.status_code == 200 and r2.status_code == 200
        report("Normal lifecycle", ok, f"{r1.status_code}, {r2.status_code}")
        results.append(ok)

        print("\n========== 2. DUPLICATE EVENTS ==========")

        duplicate_id = f"duplicate-{uuid.uuid4().hex[:12]}"

        duplicate = make_event(
            "call.started", "acct_002", duplicate_id, now
        )

        first = send_webhook(client, duplicate)
        second = send_webhook(client, duplicate)
        third = send_webhook(client, duplicate)

        first_status = first.json().get("status")
        second_status = second.json().get("status")
        third_status = third.json().get("status")

        ok = (
            first_status == "accepted"
            and second_status == "duplicate"
            and third_status == "duplicate"
        )

        report(
            "Duplicate idempotency",
            ok,
            f"{first_status}, {second_status}, {third_status}",
        )
        results.append(ok)

        print("\n========== 3. OUT-OF-ORDER EVENTS ==========")

        out_call = f"outorder-{uuid.uuid4().hex[:12]}"

        late_started = make_event(
            "call.started", "acct_003", out_call, now
        )
        early_ended = make_event(
            "call.ended", "acct_003", out_call,
            now + timedelta(seconds=60), 60, 2
        )

        first = send_webhook(client, early_ended)
        second = send_webhook(client, late_started)

        ok = first.status_code == 200 and second.status_code == 200
        report("Out-of-order ingestion", ok)
        results.append(ok)

        print("\n========== 4. LATE EVENTS ==========")

        old_time = now - timedelta(days=35)
        late_call = f"late-{uuid.uuid4().hex[:12]}"

        first = send_webhook(
            client,
            make_event("call.started", "acct_004", late_call, old_time),
        )

        second = send_webhook(
            client,
            make_event(
                "call.ended", "acct_004", late_call,
                old_time + timedelta(seconds=60), 60, 2
            ),
        )

        ok = first.status_code == 200 and second.status_code == 200
        report("35-day late event ingestion", ok)
        results.append(ok)

        print("\n========== 5. MALFORMED PAYLOADS ==========")

        valid = make_event(
            "call.started",
            "acct_005",
            f"malformed-{uuid.uuid4().hex[:12]}",
            now,
        )

        cases = [
            ("Empty body", b"", 400),
            ("Truncated JSON", b'{"event_id":', 400),
            (
                "Missing field",
                {k: v for k, v in valid.items()
                 if k != "destination_country"},
                422,
            ),
            (
                "Wrong field type",
                {**valid, "duration_seconds": "sixty"},
                422,
            ),
            (
                "Unknown event type",
                {**valid, "event_type": "call.unknown"},
                422,
            ),
        ]

        for name, payload, expected in cases:
            response = send_webhook(
                client,
                payload if isinstance(payload, dict) else {},
                raw=payload if isinstance(payload, bytes) else None,
            )

            ok = response.status_code == expected
            report(name, ok, f"HTTP {response.status_code}")
            results.append(ok)

        print("\n========== 6. BAD SIGNATURE ==========")

        bad_payload = make_event(
            "call.started",
            "acct_006",
            f"badsig-{uuid.uuid4().hex[:12]}",
            now,
        )

        response = send_webhook(
            client, bad_payload, bad_signature=True
        )

        ok = response.status_code == 401
        report("Invalid HMAC rejected", ok, f"HTTP {response.status_code}")
        results.append(ok)

        print("\n========== 7. CAP BURST ==========")

        headers = {"Authorization": f"Bearer {API_TOKEN}"}

        usage_response = client.get(
            f"{BASE_URL}/api/v1/accounts/acct_010/usage",
            headers=headers,
        )

        if usage_response.status_code != 200:
            report("Cap burst", False, "Could not read account usage")
            results.append(False)
            accepted_calls = []
        else:
            usage = usage_response.json()
            print(
                f"Starting balance: {usage['remaining_cents']} cents"
            )

            accepted_calls = []
            denied = 0

            for i in range(40):
                call_id = f"burst-{uuid.uuid4().hex[:16]}"

                response = client.post(
                    f"{BASE_URL}/api/v1/accounts/acct_010/authorize-call",
                    headers=headers,
                    json={
                        "call_id": call_id,
                        "estimated_cost_cents": 300,
                    },
                )

                if response.status_code != 200:
                    print("Unexpected API status:", response.status_code)
                    continue

                decision = response.json()

                if decision.get("allowed"):
                    accepted_calls.append(call_id)
                elif decision.get("status") == "cap_exceeded":
                    denied += 1

            ok = denied > 0 and len(accepted_calls) < 40

            report(
                "Cap enforced under 40-call burst",
                ok,
                f"Authorized: {len(accepted_calls)}, denied: {denied}",
            )
            results.append(ok)

        print("\n========== CLEANUP ==========")

        for call_id in accepted_calls:
            failed_event = make_event(
                "call.failed",
                "acct_010",
                call_id,
                datetime.now(timezone.utc),
            )
            response = send_webhook(client, failed_event)
            print(f"Release {call_id}: HTTP {response.status_code}")

        print("\nWaiting for background worker...")
        time.sleep(8)

    print("\n========== FINAL RESULTS ==========")

    passed = sum(results)
    total = len(results)

    print(f"Passed: {passed}/{total}")
    print(f"Failed: {total - passed}/{total}")

    if passed != total:
        raise SystemExit(1)


if __name__ == "__main__":
    run()