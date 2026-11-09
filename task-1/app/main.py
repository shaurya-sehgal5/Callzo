import logging
from app.api.routes.accounts import router as accounts_router
from fastapi import FastAPI
from sqlalchemy import text

from app.api.routes.webhooks import router as webhook_router
from app.db.session import engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

app = FastAPI(
    title="Callzo Usage Metering Service",
    description="Webhook ingestion and usage metering backend",
    version="1.0.0",
)

app.include_router(webhook_router)
app.include_router(accounts_router)

@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "callzo-usage-metering",
    }


@app.get("/ready")
def readiness():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        return {
            "status": "ready",
            "database": "connected",
        }

    except Exception:
        logging.getLogger(__name__).exception(
            "Database readiness check failed"
        )

        from fastapi import HTTPException

        raise HTTPException(
            status_code=503,
            detail="Database unavailable",
        )