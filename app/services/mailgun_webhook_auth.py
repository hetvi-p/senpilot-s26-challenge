from __future__ import annotations

from typing import Any, Mapping, Optional

from app.core.errors import WebhookAuthError
from app.core.security import MailgunSignature, verify_mailgun_signature
from app.storage.token_store import TokenStore


def extract_mailgun_signature(form: Mapping[str, Any]) -> MailgunSignature:
    """
    Mailgun commonly sends these as top-level form fields:
      - timestamp
      - token
      - signature
    """
    timestamp = str(form.get("timestamp") or "").strip()
    token = str(form.get("token") or "").strip()
    signature = str(form.get("signature") or "").strip()
    return MailgunSignature(timestamp=timestamp, token=token, signature=signature)


def authenticate_mailgun_webhook(
    *,
    signing_key: str,
    form: Mapping[str, Any],
    token_store: Optional[TokenStore] = None,
    max_age_seconds: int = 10 * 60,
    replay_ttl_seconds: int = 10 * 60,
) -> MailgunSignature:
    sig = extract_mailgun_signature(form)

    # Verify HMAC + timestamp freshness
    verify_mailgun_signature(
        signing_key=signing_key,
        sig=sig,
        max_age_seconds=max_age_seconds,
    )

    # Optional replay protection
    if token_store is not None:
        if token_store.seen_before(sig.token):
            raise WebhookAuthError("Replay attack detected (token reused)")
        token_store.mark_seen(sig.token, ttl_seconds=replay_ttl_seconds)

    return sig