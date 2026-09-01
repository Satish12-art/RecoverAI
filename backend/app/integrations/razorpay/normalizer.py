"""Razorpay event normalization into RecoverAI internal canonical schema."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple
from app.integrations.razorpay.schemas import NormalizedPaymentEvent


class RazorpayEventNormalizer:
    """Normalizes raw Razorpay webhook payloads into standard internal events."""

    @staticmethod
    def map_failure_code(
        error_code: Optional[str],
        error_reason: Optional[str],
        error_description: Optional[str],
    ) -> Tuple[str, str]:
        """Map Razorpay error codes and descriptions to canonical RecoverAI failure codes.
        
        Canonical codes:
        - temporary_bank_error
        - network_error
        - insufficient_funds
        - expired_card
        - authentication_failure
        - risk_flagged
        - unknown_failure
        """
        combined = f"{error_code or ''} {error_reason or ''} {error_description or ''}".lower()

        if any(w in combined for w in ["fraud", "risk", "blacklisted", "suspicious", "stolen"]):
            return "risk_flagged", "Transaction flagged by risk/fraud filters."

        if any(w in combined for w in ["insufficient", "balance", "limit_exceeded"]):
            return "insufficient_funds", "Account balance insufficient for transaction amount."

        if any(w in combined for w in ["expired", "card_expired", "expiry"]):
            return "expired_card", "Payment card expired."

        if any(w in combined for w in ["otp", "auth", "3ds", "authentication", "verification", "pin"]):
            return "authentication_failure", "Customer authentication/OTP verification timeout or failure."

        if any(w in combined for w in ["bank", "issuer", "gateway_error", "bank_error", "down"]):
            return "temporary_bank_error", "Issuing bank or gateway temporary communication error."

        if any(w in combined for w in ["network", "timeout", "connection", "timed_out"]):
            return "network_error", "Transient network timeout during authorization."

        return "unknown_failure", error_description or "Payment failed due to an unclassified error."

    @classmethod
    def normalize(cls, payload: Dict[str, Any], event_id: str) -> NormalizedPaymentEvent:
        """Parse and normalize a Razorpay webhook payload envelope."""
        event_type = payload.get("event", "unknown")
        raw_payload = payload.get("payload", {})
        
        # Payment entity is usually at payload.payment.entity
        payment_data = raw_payload.get("payment", {}).get("entity", {})
        
        # If payload is empty or not in standard wrapper, try root
        if not payment_data and "id" in payload:
            payment_data = payload

        # Extract payment attributes
        raw_payment_id = payment_data.get("id", f"pay_unknown_{event_id[:8]}")
        raw_order_id = payment_data.get("order_id")
        raw_amount_paise = payment_data.get("amount", 0)
        amount_inr = round(float(raw_amount_paise) / 100.0, 2)
        currency = payment_data.get("currency", "INR")
        payment_method = payment_data.get("method", "card")
        raw_status = payment_data.get("status", "unknown")

        # Customer metadata
        notes = payment_data.get("notes", {}) or {}
        customer_email = payment_data.get("email") or notes.get("customer_email")
        customer_name = notes.get("customer_name") or (customer_email.split("@")[0].title() if customer_email else "Razorpay Customer")
        customer_id_ext = payment_data.get("customer_id") or notes.get("customer_id")

        # Failure mapping
        failure_code = None
        failure_reason = None
        risk_flagged = False

        if event_type == "payment.failed" or (raw_status == "failed" and "payment" in event_type):
            f_code, f_reason = cls.map_failure_code(
                error_code=payment_data.get("error_code"),
                error_reason=payment_data.get("error_reason"),
                error_description=payment_data.get("error_description"),
            )
            failure_code = f_code
            failure_reason = f_reason
            risk_flagged = (f_code == "risk_flagged")
            canonical_status = "failed"
        elif event_type in {"payment.captured", "payment.authorized", "order.paid"} or raw_status in {"captured", "authorized", "paid"}:
            canonical_status = "successful"
        else:
            canonical_status = raw_status

        # Timestamp
        created_at_ts = payload.get("created_at") or payment_data.get("created_at")
        if created_at_ts:
            occurred_at = datetime.fromtimestamp(created_at_ts, tz=timezone.utc)
        else:
            occurred_at = datetime.now(timezone.utc)

        return NormalizedPaymentEvent(
            event_id=event_id,
            event_type=event_type,
            external_payment_id=raw_payment_id,
            external_order_id=raw_order_id,
            external_customer_id=customer_id_ext,
            customer_name=customer_name,
            customer_email=customer_email,
            amount_inr=amount_inr,
            currency=currency,
            payment_method=payment_method,
            status=canonical_status,
            failure_code=failure_code,
            failure_reason=failure_reason,
            risk_flagged=risk_flagged,
            occurred_at=occurred_at,
            raw_event_name=event_type,
            is_test_mode=True,
        )
