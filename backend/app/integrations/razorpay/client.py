"""Razorpay test mode client and outbound payment link generator."""

import uuid
from typing import Optional
from app.core.config import settings
from app.integrations.razorpay.schemas import PaymentUpdateLinkResponse


class RazorpayTestClient:
    """Safe test-mode outbound link generator and client.
    
    Security rules:
    - Never exposes secret keys or signing material.
    - Explicitly returns test mode links labeled as TEST MODE.
    """

    @classmethod
    def is_configured(cls) -> bool:
        """Check if Razorpay test credentials or webhook secret is configured."""
        return bool(settings.razorpay_key_id or settings.razorpay_webhook_secret)

    @classmethod
    def generate_payment_update_link(
        cls,
        payment_id: str,
        amount_inr: float,
        customer_email: Optional[str] = None,
        description: str = "RecoverAI Test-Mode Payment Update",
    ) -> PaymentUpdateLinkResponse:
        """Generate a safe, test-mode payment link URL."""
        link_id = f"plink_test_{uuid.uuid4().hex[:12]}"
        short_url = f"https://rzp.io/i/test_{link_id[11:]}"

        return PaymentUpdateLinkResponse(
            payment_link_id=link_id,
            short_url=short_url,
            amount_inr=amount_inr,
            currency="INR",
            status="created",
            is_test_mode=True,
            expires_at=None,
        )
