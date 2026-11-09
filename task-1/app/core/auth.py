
import hmac
import os

from fastapi import Header, HTTPException, status
from dotenv import load_dotenv

load_dotenv()


def verify_api_token(
    authorization: str | None = Header(default=None),
):
    expected_token = os.getenv("API_TOKEN")

    if not expected_token:
        raise RuntimeError("API_TOKEN is not configured")

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API token",
        )

    supplied_token = authorization.removeprefix("Bearer ").strip()

    if not hmac.compare_digest(supplied_token, expected_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API token",
        )

    return True
