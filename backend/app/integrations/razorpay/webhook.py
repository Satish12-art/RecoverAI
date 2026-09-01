"""Razorpay Webhook signature verification and security utilities."""

import hashlib
import hmac
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def verify_razorpay_signature(
    raw_body: bytes,
    signature: Optional[str],
    secret: Optional[str],
) -> bool:
    """Verify Razorpay webhook signature via HMAC SHA256.
    
    Security rules:
    - Never logs secrets or credentials.
    - Constant-time comparison to prevent timing attacks.
    - Rejects missing signature or missing secret.
    """
    if not signature or not secret or not raw_body:
        return False

    try:
        expected_signature = hmac.new(
            secret.encode("utf-8"),
            raw_body,
            hashlib.sha256,
        ).hexdigest()

        # Constant-time comparison
        return hmac.compare_digest(expected_signature, signature)
    except Exception as exc:
        logger.warning(f"Signature verification error: {type(exc).__name__}")
        return False
