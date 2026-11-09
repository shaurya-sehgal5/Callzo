import os

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import Account


def seed_accounts():
    default_cap = int(
        os.getenv("DEFAULT_MONTHLY_CAP_CENTS", "1000")
    )

    if default_cap <= 0:
        raise ValueError("Monthly cap must be positive")

    account_ids = [
        f"acct_{i:03d}"
        for i in range(1, 11)
    ]

    with SessionLocal.begin() as session:
        existing_ids = set(
            session.scalars(
                select(Account.id).where(
                    Account.id.in_(account_ids)
                )
            ).all()
        )

        new_accounts = [
            Account(
                id=account_id,
                monthly_cap_cents=default_cap,
                is_active=True,
            )
            for account_id in account_ids
            if account_id not in existing_ids
        ]

        session.add_all(new_accounts)

    print(f"Account seeding completed.")
    print(f"New accounts created: {len(new_accounts)}")
    print(f"Default monthly cap: {default_cap} cents")


if __name__ == "__main__":
    seed_accounts()