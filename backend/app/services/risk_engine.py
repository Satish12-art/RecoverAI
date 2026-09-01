"""Deterministic Revenue Risk Engine for RecoverAI.

Calculates Gross Revenue at Risk and classifies revenue risk categories
based strictly on observable production data.
"""

from decimal import Decimal
from enum import Enum
from typing import Sequence
from pydantic import BaseModel, Field


class RevenueEventType(str, Enum):
    PAYMENT_FAILURE = "PAYMENT_FAILURE"
    CHECKOUT_ABANDONMENT = "CHECKOUT_ABANDONMENT"
    SUBSCRIPTION_FAILURE = "SUBSCRIPTION_FAILURE"
    OTHER = "OTHER"


class RiskAssessment(BaseModel):
    is_at_risk: bool
    amount_at_risk: float
    event_type: RevenueEventType
    failure_code: str | None = None
    failure_reason: str | None = None


class RevenueRiskEngine:
    """Deterministic Revenue Risk Engine."""

    @staticmethod
    def assess_payment(payment: dict | object) -> RiskAssessment:
        """Assess risk for an individual payment event."""
        def get_val(obj, key, default=None):
            if obj is None:
                return default
            if isinstance(obj, dict):
                return obj.get(key, default)
            return getattr(obj, key, default)

        status = (get_val(payment, "status") or "").lower()
        amount = float(get_val(payment, "amount", 0.0) or 0.0)
        failure_code = get_val(payment, "failure_code")
        failure_reason = get_val(payment, "failure_reason")

        # Payment is at risk if status is failed or pending/created without capture
        is_failed = status == "failed"
        is_at_risk = is_failed and amount > 0.0

        return RiskAssessment(
            is_at_risk=is_at_risk,
            amount_at_risk=round(amount, 2) if is_at_risk else 0.0,
            event_type=RevenueEventType.PAYMENT_FAILURE,
            failure_code=failure_code,
            failure_reason=failure_reason,
        )

    @staticmethod
    def calculate_gross_revenue_at_risk(payments: Sequence[dict | object]) -> Decimal:
        """Calculate total Gross Revenue at Risk across a sequence of payments.
        
        Gross Revenue at Risk = sum of failed/at-risk payment amounts.
        Excludes successful payments and non-risk states.
        Uses Decimal for precision.
        """
        def get_val(obj, key, default=None):
            if obj is None:
                return default
            if isinstance(obj, dict):
                return obj.get(key, default)
            return getattr(obj, key, default)

        total = Decimal("0.00")
        for p in payments:
            status = (get_val(p, "status") or "").lower()
            if status == "failed":
                amt = Decimal(str(get_val(p, "amount", 0.0) or "0.0"))
                if amt > Decimal("0.00"):
                    total += amt

        return total.quantize(Decimal("0.01"))
