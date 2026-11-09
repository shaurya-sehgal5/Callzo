from datetime import date, datetime, timezone
from uuid import uuid4

from app.db.session import SessionLocal
from app.models import Account, Call, MonthlyUsage
from app.services.usage_service import (
    check_monthly_cap,
    get_billing_month,
    recalculate_monthly_usage,
)


def test_monthly_usage_recalculation_is_idempotent():
    now = datetime.now(timezone.utc)
    month = get_billing_month(now)

    with SessionLocal() as session:
        with session.begin_nested():
            call = Call(
                account_id="acct_001",
                call_id=f"usage_test_{uuid4().hex}",
                status="ended",
                started_at=now,
                ended_at=now,
                duration_seconds=600,
                cost_cents=17,
                destination_country="US",
                last_event_at=now,
            )
            session.add(call)
            session.flush()

            first = recalculate_monthly_usage(
                session, "acct_001", month
            )
            first_totals = (
                first.total_calls,
                first.total_duration_seconds,
                first.total_cost_cents,
            )

            second = recalculate_monthly_usage(
                session, "acct_001", month
            )
            second_totals = (
                second.total_calls,
                second.total_duration_seconds,
                second.total_cost_cents,
            )

            assert first_totals == second_totals
            assert second.total_calls >= 1
            assert second.total_duration_seconds >= 600
            assert second.total_cost_cents >= 17


def test_monthly_cap_denies_call_that_exceeds_limit():
    month = date.today().replace(day=1)

    with SessionLocal() as session:
        with session.begin_nested():
            account = session.get(Account, "acct_001")
            assert account is not None

            usage = session.query(MonthlyUsage).filter_by(
                account_id="acct_001",
                billing_month=month,
            ).first()

            if usage is None:
                usage = MonthlyUsage(
                    account_id="acct_001",
                    billing_month=month,
                )
                session.add(usage)

            usage.total_cost_cents = account.monthly_cap_cents
            session.flush()

            result = check_monthly_cap(
                session,
                "acct_001",
                month,
                requested_cost_cents=1,
            )

            assert result["allowed"] is False
            assert result["remaining_cents"] == 0