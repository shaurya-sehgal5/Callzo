import hashlib
import hmac
import os

from dotenv import load_dotenv

load_dotenv()


def verify_webhook_signature(
    payload: bytes,
    signature: str | None,
) -> bool:

    if not signature:
        return False

    secret = os.getenv("WEBHOOK_SECRET")

    if not secret:
        raise RuntimeError("WEBHOOK_SECRET is not configured")

    expected_signature = hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(
        expected_signature,
        signature.strip(),
    )