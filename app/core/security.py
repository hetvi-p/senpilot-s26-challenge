from __future__ import annotations

import hashlib
import hmac
import time
from dataclasses import dataclass
from typing import Optional

from app.core.errors import WebhookAuthError


@dataclass(frozen=True)
class MailgunSignature:
    timestamp: str
    token: str
    signature: str


def _now_epoch() -> int:
    return int(time.time())


def verify_mailgun_signature(
    signing_key: str,
    sig: MailgunSignature,
    *,
    max_age_seconds: int = 10 * 60,
    now_epoch: Optional[int] = None,
) -> None:
    """
    Verifies Mailgun webhook signature.

    Spec (Mailgun):
      - message = timestamp + token (no separator)
      - expected = HMAC-SHA256(signing_key, message).hexdigest()
      - compare expected to signature
      - optionally check timestamp freshness
    """
    if not signing_key:
        raise WebhookAuthError("Missing MAILGUN_WEBHOOK_SIGNING_KEY")

    if not sig.timestamp or not sig.token or not sig.signature:
        raise WebhookAuthError("Missing Mailgun signature fields (timestamp/token/signature)")

    try:
        ts_int = int(sig.timestamp)
    except ValueError as e:
        raise WebhookAuthError("Invalid timestamp") from e

    now = _now_epoch() if now_epoch is None else int(now_epoch)
    age = abs(now - ts_int)
    if age > max_age_seconds:
        raise WebhookAuthError(f"Stale webhook timestamp (age={age}s)")

    message = f"{sig.timestamp}{sig.token}".encode("utf-8")
    expected = hmac.new(
        key=signing_key.encode("utf-8"),
        msg=message,
        digestmod=hashlib.sha256,
    ).hexdigest()

    # constant-time compare
    if not hmac.compare_digest(expected, sig.signature):
        raise WebhookAuthError("Invalid webhook signature")