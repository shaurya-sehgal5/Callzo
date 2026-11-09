
import os
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import app
from app.db.session import SessionLocal
from app.models import Account, Call, MonthlyUsage


client = TestClient(app)
TOKEN = os.getenv("API_TOKEN", "callzo_dev_api_token")
HEADERS = {"Authorization": f"Bearer {TOKEN}"}


def test_usage_requires_authentication():
    response = client.get("/api/v1/accounts/acct_001/usage")
    assert response.status_code == 401


def test_get_account_usage():
    response = client.get(
        "/api/v1/accounts/acct_001/usage",
        headers=HEADERS,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["account_id"] == "acct_001"
    assert "used_cents" in data
    assert "reserved_cents" in data
    assert "remaining_cents" in data


def test_authorize_call_reserves_cost():
    call_id = f"api_test_{uuid4().hex}"
    month = None

    try:
        response = client.post(
            "/api/v1/accounts/acct_001/authorize-call",
            headers=HEADERS,
            json={
                "call_id": call_id,
                "estimated_cost_cents": 10,
            },
        )

        assert response.status_code == 200
        assert response.json()["allowed"] is True
        assert response.json()["reserved_cost_cents"] == 10

        # Repeating the same request must not reserve twice.
        duplicate = client.post(
            "/api/v1/accounts/acct_001/authorize-call",
            headers=HEADERS,
            json={
                "call_id": call_id,
                "estimated_cost_cents": 10,
            },
        )

        assert duplicate.status_code == 200
        assert duplicate.json()["status"] == "already_authorized"

    finally:
        with SessionLocal.begin() as session:
            call = session.scalar(
                select(Call).where(
                    Call.account_id == "acct_001",
                    Call.call_id == call_id,
                )
            )

            if call:
                if call.reserved_cost_cents and call.reservation_month:
                    usage = session.scalar(
                        select(MonthlyUsage).where(
                            MonthlyUsage.account_id == "acct_001",
                            MonthlyUsage.billing_month == call.reservation_month,
                        )
                    )

                    if usage:
                        usage.reserved_cost_cents = max(
                            0,
                            usage.reserved_cost_cents
                            - call.reserved_cost_cents,
                        )

                session.delete(call)


def test_authorize_call_rejects_cost_above_cap():
    call_id = f"api_cap_test_{uuid4().hex}"

    with SessionLocal.begin() as session:
        account = session.get(Account, "acct_001")
        original_cap = account.monthly_cap_cents
        account.monthly_cap_cents = 5

    try:
        response = client.post(
            "/api/v1/accounts/acct_001/authorize-call",
            headers=HEADERS,
            json={
                "call_id": call_id,
                "estimated_cost_cents": 10,
            },
        )

        assert response.status_code == 200
        assert response.json()["allowed"] is False
        assert response.json()["status"] == "cap_exceeded"

    finally:
        with SessionLocal.begin() as session:
            account = session.get(Account, "acct_001")
            account.monthly_cap_cents = original_cap


def test_authorize_call_rejects_missing_token():
    response = client.post(
        "/api/v1/accounts/acct_001/authorize-call",
        json={
            "call_id": f"api_auth_test_{uuid4().hex}",
            "estimated_cost_cents": 10,
        },
    )

    assert response.status_code == 401
