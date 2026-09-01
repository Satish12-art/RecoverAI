"""Deterministic Eligibility Gate Service for RecoverAI.

Determines whether a payment should proceed into recovery analysis,
be stopped (e.g. fraud, opted out, already paid), or be ignored (duplicate).
Operates strictly on observable production data without using LLMs or ground truth.
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class EligibilityDecision(str, Enum):
    PROCEED = "PROCEED"
    STOP = "STOP"
    IGNORE = "IGNORE"


class EligibilityReason(str, Enum):
    ELIGIBLE = "ELIGIBLE"
    ALREADY_SUCCESSFUL = "ALREADY_SUCCESSFUL"
    RISK_FLAGGED = "RISK_FLAGGED"
    CUSTOMER_OPTED_OUT = "CUSTOMER_OPTED_OUT"
    DUPLICATE_EVENT = "DUPLICATE_EVENT"
    INVALID_PAYMENT_STATE = "INVALID_PAYMENT_STATE"


class EligibilityResult(BaseModel):
    eligible: bool
    decision: EligibilityDecision
    reason: EligibilityReason
    message: str


class EligibilityGate:
    """Deterministic eligibility evaluator."""

    @staticmethod
    def evaluate(
        payment: dict | object,
        customer: Optional[dict | object] = None,
        is_duplicate: bool = False,
    ) -> EligibilityResult:
        """Evaluate payment eligibility against deterministic gateway rules.
        
        Rules evaluated in order:
        1. Duplicate event -> IGNORE
        2. Already successful status -> STOP
        3. Invalid payment state -> STOP
        4. Risk / fraud flagged -> STOP
        5. Customer opted out -> STOP
        6. Otherwise -> PROCEED
        """
        # Helper to extract attributes from dict or ORM model
        def get_val(obj, key, default=None):
            if obj is None:
                return default
            if isinstance(obj, dict):
                return obj.get(key, default)
            return getattr(obj, key, default)

        # 1. Duplicate check
        if is_duplicate:
            return EligibilityResult(
                eligible=False,
                decision=EligibilityDecision.IGNORE,
                reason=EligibilityReason.DUPLICATE_EVENT,
                message="Duplicate event detected - ignoring to ensure idempotency.",
            )

        # 2. Check payment status
        status = (get_val(payment, "status") or "").lower()
        if status in ("paid", "captured", "success", "successful"):
            return EligibilityResult(
                eligible=False,
                decision=EligibilityDecision.STOP,
                reason=EligibilityReason.ALREADY_SUCCESSFUL,
                message="Payment is already successfully captured/paid.",
            )

        if status not in ("failed", "created", "pending", "authorized"):
            return EligibilityResult(
                eligible=False,
                decision=EligibilityDecision.STOP,
                reason=EligibilityReason.INVALID_PAYMENT_STATE,
                message=f"Invalid payment status '{status}' for recovery analysis.",
            )

        # 3. Check risk flags
        risk_flagged = bool(get_val(payment, "risk_flagged", False))
        failure_code = (get_val(payment, "failure_code") or "").lower()
        if risk_flagged or failure_code == "risk_flagged":
            return EligibilityResult(
                eligible=False,
                decision=EligibilityDecision.STOP,
                reason=EligibilityReason.RISK_FLAGGED,
                message="Payment flagged as high risk / fraud. Automatic recovery prohibited.",
            )

        # 4. Check customer opt-out
        if customer is not None:
            opted_out = bool(get_val(customer, "opted_out", False))
            if opted_out:
                return EligibilityResult(
                    eligible=False,
                    decision=EligibilityDecision.STOP,
                    reason=EligibilityReason.CUSTOMER_OPTED_OUT,
                    message="Customer has opted out of automated communications/recovery.",
                )

        # 5. Passed all eligibility checks
        return EligibilityResult(
            eligible=True,
            decision=EligibilityDecision.PROCEED,
            reason=EligibilityReason.ELIGIBLE,
            message="Payment is eligible for recovery analysis.",
        )
