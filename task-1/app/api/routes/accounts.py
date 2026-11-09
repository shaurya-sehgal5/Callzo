
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.auth import verify_api_token
from app.db.session import SessionLocal
from app.models import Account, Call, MonthlyUsage
from app.services.usage_service import (
    check_monthly_cap,
    get_billing_month,
)
from app.services.reconciliation_service import reconcile_monthly_usage


router = APIRouter(
    prefix="/api/v1/accounts",
    tags=["accounts"],
    dependencies=[Depends(verify_api_token)],
)


class AuthorizeCallRequest(BaseModel):
    call_id: str = Field(min_length=1, max_length=100)
    estimated_cost_cents: int = Field(strict=True, gt=0)


def current_billing_month() -> date:
    return get_billing_month(datetime.now(timezone.utc))


@router.get("/{account_id}/usage")
def get_account_usage(
    account_id: str,
    month: date | None = Query(default=None),
):
    billing_month = (
        date(month.year, month.month, 1)
        if month else current_billing_month()
    )

    with SessionLocal() as session:
        account = session.get(Account, account_id)

        if account is None:
            raise HTTPException(404, "Account not found")

        usage = session.scalar(
            select(MonthlyUsage).where(
                MonthlyUsage.account_id == account_id,
                MonthlyUsage.billing_month == billing_month,
            )
        )

        used = usage.total_cost_cents if usage else 0
        reserved = usage.reserved_cost_cents if usage else 0
        cap = account.monthly_cap_cents

        return {
            "account_id": account_id,
            "billing_month": billing_month.isoformat(),
            "total_calls": usage.total_calls if usage else 0,
            "total_duration_seconds": (
                usage.total_duration_seconds if usage else 0
            ),
            "used_cents": used,
            "reserved_cents": reserved,
            "monthly_cap_cents": cap,
            "remaining_cents": max(0, cap - used - reserved),
        }


@router.post("/{account_id}/authorize-call")
def authorize_call(
    account_id: str,
    request: AuthorizeCallRequest,
):
    now = datetime.now(timezone.utc)
    month = current_billing_month()

    with SessionLocal.begin() as session:
        account = session.scalar(
            select(Account)
            .where(Account.id == account_id)
            .with_for_update()
        )

        if account is None:
            raise HTTPException(404, "Account not found")

        if not account.is_active:
            raise HTTPException(403, "Account is inactive")

        # Lock and check for an existing authorization first.
        call = session.scalar(
            select(Call)
            .where(
                Call.account_id == account_id,
                Call.call_id == request.call_id,
            )
            .with_for_update()
        )

        if call is not None:
            if (
                call.authorization_status == "authorized"
                and call.reserved_cost_cents == request.estimated_cost_cents
            ):
                return {
                    "allowed": True,
                    "status": "already_authorized",
                    "call_id": request.call_id,
                    "reserved_cost_cents": call.reserved_cost_cents,
                }

            raise HTTPException(
                409,
                "Call already exists or has a different authorization",
            )

        usage = session.scalar(
            select(MonthlyUsage)
            .where(
                MonthlyUsage.account_id == account_id,
                MonthlyUsage.billing_month == month,
            )
            .with_for_update()
        )

        if usage is None:
            usage = MonthlyUsage(
                account_id=account_id,
                billing_month=month,
            )
            session.add(usage)
            session.flush()

        decision = check_monthly_cap(
            session,
            account_id,
            month,
            request.estimated_cost_cents,
        )

        if not decision["allowed"]:
            return {
                **decision,
                "status": "cap_exceeded",
                "call_id": request.call_id,
            }

        # Reserve the estimated amount before committing.
        usage.reserved_cost_cents += request.estimated_cost_cents

        call = Call(
            account_id=account_id,
            call_id=request.call_id,
            status="authorized",
            reserved_cost_cents=request.estimated_cost_cents,
            reservation_month=month,
            authorization_status="authorized",
            authorized_at=now,
        )

        session.add(call)
        session.flush()

        return {
            "allowed": True,
            "status": "authorized",
            "call_id": request.call_id,
            "reserved_cost_cents": request.estimated_cost_cents,
            "monthly_cap_cents": decision["monthly_cap_cents"],
            "used_cents": decision["used_cents"],
            "reserved_cents": decision["reserved_cents"]
            + request.estimated_cost_cents,
            "remaining_cents": decision["remaining_cents"]
            - request.estimated_cost_cents,
        }


@router.post("/{account_id}/reconcile")
def reconcile_account(
    account_id: str,
    month: date | None = Query(default=None),
):
    billing_month = (
        date(month.year, month.month, 1)
        if month else current_billing_month()
    )

    with SessionLocal.begin() as session:
        try:
            usage = reconcile_monthly_usage(
                session,
                account_id,
                billing_month,
            )
        except ValueError as exc:
            raise HTTPException(404, str(exc))

        return {
            "status": "reconciled",
            "account_id": account_id,
            "billing_month": billing_month.isoformat(),
            "total_calls": usage.total_calls,
            "total_duration_seconds": usage.total_duration_seconds,
            "total_cost_cents": usage.total_cost_cents,
            "reserved_cost_cents": usage.reserved_cost_cents,
        }
