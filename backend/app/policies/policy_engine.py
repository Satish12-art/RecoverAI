"""Deterministic Policy Engine for RecoverAI.

Authoritative deterministic gatekeeper between AI recommendations and execution.
Enforces 10 explicit policy rules in strict hierarchical order:
1. Hard Safety Stops (Already paid, Risk flag, Opted out, Invalid state)
2. Action Validation (Allowed actions: retry, message, escalate, stop)
3. Escalation Conditions (Max retries, Low probability, Low confidence, High amount)
4. Approval (All checks pass)

Contains NO bypass mechanisms, NO LLM dependencies, and NO ground truth access.
"""

from decimal import Decimal
from enum import Enum
from typing import Optional, Sequence
from pydantic import BaseModel, Field

from app.core.config import settings


class PolicyDecision(str, Enum):
    APPROVE = "APPROVE"
    ESCALATE = "ESCALATE"
    STOP = "STOP"
    REJECT = "REJECT"


class PolicyReasonCode(str, Enum):
    # Level 1 — Hard Safety Stops
    ALREADY_SUCCESSFUL = "ALREADY_SUCCESSFUL"
    RISK_FLAGGED = "RISK_FLAGGED"
    CUSTOMER_OPTED_OUT = "CUSTOMER_OPTED_OUT"
    INVALID_PAYMENT_STATE = "INVALID_PAYMENT_STATE"

    # Level 2 — Action Validation
    INVALID_ACTION = "INVALID_ACTION"

    # Level 3 — Escalation Conditions
    MAX_RETRIES_REACHED = "MAX_RETRIES_REACHED"
    LOW_RECOVERY_PROBABILITY = "LOW_RECOVERY_PROBABILITY"
    LOW_SCORER_CONFIDENCE = "LOW_SCORER_CONFIDENCE"
    AMOUNT_LIMIT_EXCEEDED = "AMOUNT_LIMIT_EXCEEDED"

    # Level 4 — Approval
    POLICY_APPROVED = "POLICY_APPROVED"


class PolicyCheckTrace(BaseModel):
    rule_number: int
    rule_name: str
    passed: bool
    detail: str


class PolicyResult(BaseModel):
    decision: PolicyDecision
    action: str
    reason_codes: list[PolicyReasonCode]
    checks: list[PolicyCheckTrace]
    explanation: str


class PolicyEngine:
    """Deterministic Policy Engine."""

    ALLOWED_ACTIONS = {"retry", "message", "escalate", "stop"}

    @classmethod
    def evaluate(
        cls,
        payment: dict | object,
        customer: Optional[dict | object] = None,
        proposed_action: str = "retry",
        recovery_probability: Optional[float] = None,
        scorer_confidence: Optional[float] = None,
        previous_recovery_attempts: int = 0,
        prob_threshold: Optional[float] = None,
        conf_threshold: Optional[float] = None,
        amount_limit: Optional[float] = None,
        max_retries: Optional[int] = None,
    ) -> PolicyResult:
        """Evaluate a proposed action against the 10 deterministic policy rules in order."""
        if prob_threshold is None:
            prob_threshold = settings.recovery_probability_threshold
        if conf_threshold is None:
            conf_threshold = settings.scorer_confidence_threshold
        if amount_limit is None:
            amount_limit = settings.auto_recovery_amount_limit
        if max_retries is None:
            max_retries = settings.max_retries

        def get_val(obj, key, default=None):
            if obj is None:
                return default
            if isinstance(obj, dict):
                return obj.get(key, default)
            return getattr(obj, key, default)

        checks: list[PolicyCheckTrace] = []
        reason_codes: list[PolicyReasonCode] = []

        status = (get_val(payment, "status") or "").lower()
        amount_dec = Decimal(str(get_val(payment, "amount", 0.0) or "0.0"))
        limit_dec = Decimal(str(amount_limit))
        risk_flagged = bool(get_val(payment, "risk_flagged", False))
        failure_code = (get_val(payment, "failure_code") or "").lower()
        opted_out = bool(get_val(customer, "opted_out", False)) if customer else False

        norm_action = (proposed_action or "").strip().lower()

        # ──────────────────────────────────────────────
        # LEVEL 1: HARD SAFETY STOPS
        # ──────────────────────────────────────────────

        # Rule 1: Already successful
        if status in ("paid", "captured", "success", "successful"):
            checks.append(PolicyCheckTrace(
                rule_number=1,
                rule_name="payment_not_already_successful",
                passed=False,
                detail=f"Payment status is '{status}'. No recovery needed.",
            ))
            reason_codes.append(PolicyReasonCode.ALREADY_SUCCESSFUL)
            return PolicyResult(
                decision=PolicyDecision.STOP,
                action="stop",
                reason_codes=reason_codes,
                checks=checks,
                explanation="Payment is already successful. Recovery action prohibited.",
            )
        checks.append(PolicyCheckTrace(
            rule_number=1,
            rule_name="payment_not_already_successful",
            passed=True,
            detail="Payment is not paid or captured.",
        ))

        # Rule 2: Risk / Fraud Flagged
        if risk_flagged or failure_code == "risk_flagged":
            checks.append(PolicyCheckTrace(
                rule_number=2,
                rule_name="no_fraud_risk_flag",
                passed=False,
                detail="Payment is flagged as high risk / fraud.",
            ))
            reason_codes.append(PolicyReasonCode.RISK_FLAGGED)
            return PolicyResult(
                decision=PolicyDecision.STOP,
                action="stop",
                reason_codes=reason_codes,
                checks=checks,
                explanation="High fraud/risk indicator present. Automated recovery prohibited.",
            )
        checks.append(PolicyCheckTrace(
            rule_number=2,
            rule_name="no_fraud_risk_flag",
            passed=True,
            detail="No fraud or risk indicators present.",
        ))

        # Rule 3: Customer Opted Out
        if opted_out:
            checks.append(PolicyCheckTrace(
                rule_number=3,
                rule_name="customer_not_opted_out",
                passed=False,
                detail="Customer has active opt-out flag.",
            ))
            reason_codes.append(PolicyReasonCode.CUSTOMER_OPTED_OUT)
            return PolicyResult(
                decision=PolicyDecision.STOP,
                action="stop",
                reason_codes=reason_codes,
                checks=checks,
                explanation="Customer has opted out of automated communications. Recovery stopped.",
            )
        checks.append(PolicyCheckTrace(
            rule_number=3,
            rule_name="customer_not_opted_out",
            passed=True,
            detail="Customer has not opted out.",
        ))

        # Rule 4: Invalid Payment State
        if status not in ("failed", "created", "pending", "authorized"):
            checks.append(PolicyCheckTrace(
                rule_number=4,
                rule_name="valid_payment_state",
                passed=False,
                detail=f"Payment status '{status}' is invalid for recovery.",
            ))
            reason_codes.append(PolicyReasonCode.INVALID_PAYMENT_STATE)
            return PolicyResult(
                decision=PolicyDecision.STOP,
                action="stop",
                reason_codes=reason_codes,
                checks=checks,
                explanation=f"Payment state '{status}' is unrecoverable. Action stopped.",
            )
        checks.append(PolicyCheckTrace(
            rule_number=4,
            rule_name="valid_payment_state",
            passed=True,
            detail=f"Payment status '{status}' is valid for recovery.",
        ))

        # ──────────────────────────────────────────────
        # LEVEL 2: ACTION VALIDATION
        # ──────────────────────────────────────────────

        # Rule 5: Action is within allowed set
        if norm_action not in cls.ALLOWED_ACTIONS:
            checks.append(PolicyCheckTrace(
                rule_number=5,
                rule_name="valid_proposed_action",
                passed=False,
                detail=f"Proposed action '{proposed_action}' is not in allowed actions {cls.ALLOWED_ACTIONS}.",
            ))
            reason_codes.append(PolicyReasonCode.INVALID_ACTION)
            return PolicyResult(
                decision=PolicyDecision.REJECT,
                action="escalate",
                reason_codes=reason_codes,
                checks=checks,
                explanation=f"Action '{proposed_action}' is unrecognized. Action rejected.",
            )
        checks.append(PolicyCheckTrace(
            rule_number=5,
            rule_name="valid_proposed_action",
            passed=True,
            detail=f"Proposed action '{norm_action}' is a recognized recovery strategy.",
        ))

        # If the proposed action was explicitly 'stop' or 'escalate', we can process it directly
        if norm_action == "stop":
            return PolicyResult(
                decision=PolicyDecision.APPROVE,
                action="stop",
                reason_codes=[PolicyReasonCode.POLICY_APPROVED],
                checks=checks,
                explanation="Approved explicit 'stop' recommendation.",
            )

        if norm_action == "escalate":
            return PolicyResult(
                decision=PolicyDecision.APPROVE,
                action="escalate",
                reason_codes=[PolicyReasonCode.POLICY_APPROVED],
                checks=checks,
                explanation="Approved explicit 'escalate' recommendation for human review.",
            )

        # ──────────────────────────────────────────────
        # LEVEL 3: ESCALATION CONDITIONS
        # ──────────────────────────────────────────────

        escalate_reasons = []

        # Rule 6: Maximum Retry Limit
        if previous_recovery_attempts >= max_retries:
            checks.append(PolicyCheckTrace(
                rule_number=6,
                rule_name="retry_limit_not_exceeded",
                passed=False,
                detail=f"Prior recovery attempts ({previous_recovery_attempts}) reached or exceeded maximum limit ({max_retries}).",
            ))
            escalate_reasons.append(PolicyReasonCode.MAX_RETRIES_REACHED)
        else:
            checks.append(PolicyCheckTrace(
                rule_number=6,
                rule_name="retry_limit_not_exceeded",
                passed=True,
                detail=f"Prior attempts ({previous_recovery_attempts}) < max limit ({max_retries}).",
            ))

        # Rule 7: Recovery Probability Threshold
        prob_val = recovery_probability if recovery_probability is not None else 0.0
        if prob_val < prob_threshold:
            checks.append(PolicyCheckTrace(
                rule_number=7,
                rule_name="recovery_probability_above_threshold",
                passed=False,
                detail=f"Recovery probability ({prob_val:.2f}) is below threshold ({prob_threshold:.2f}).",
            ))
            escalate_reasons.append(PolicyReasonCode.LOW_RECOVERY_PROBABILITY)
        else:
            checks.append(PolicyCheckTrace(
                rule_number=7,
                rule_name="recovery_probability_above_threshold",
                passed=True,
                detail=f"Recovery probability ({prob_val:.2f}) >= threshold ({prob_threshold:.2f}).",
            ))

        # Rule 8: Scorer Confidence Threshold
        conf_val = scorer_confidence if scorer_confidence is not None else 0.0
        if conf_val < conf_threshold:
            checks.append(PolicyCheckTrace(
                rule_number=8,
                rule_name="scorer_confidence_above_threshold",
                passed=False,
                detail=f"Scorer confidence ({conf_val:.2f}) is below threshold ({conf_threshold:.2f}).",
            ))
            escalate_reasons.append(PolicyReasonCode.LOW_SCORER_CONFIDENCE)
        else:
            checks.append(PolicyCheckTrace(
                rule_number=8,
                rule_name="scorer_confidence_above_threshold",
                passed=True,
                detail=f"Scorer confidence ({conf_val:.2f}) >= threshold ({conf_threshold:.2f}).",
            ))

        # Rule 9: High Amount Limit
        if amount_dec > limit_dec:
            checks.append(PolicyCheckTrace(
                rule_number=9,
                rule_name="amount_within_automatic_limit",
                passed=False,
                detail=f"Transaction amount (₹{amount_dec}) exceeds automatic recovery limit (₹{limit_dec}).",
            ))
            escalate_reasons.append(PolicyReasonCode.AMOUNT_LIMIT_EXCEEDED)
        else:
            checks.append(PolicyCheckTrace(
                rule_number=9,
                rule_name="amount_within_automatic_limit",
                passed=True,
                detail=f"Transaction amount (₹{amount_dec}) is within automatic limit (₹{limit_dec}).",
            ))

        # If any Level 3 escalation checks failed, escalate to human review
        if escalate_reasons:
            reasons_text = ", ".join([r.value for r in escalate_reasons])
            return PolicyResult(
                decision=PolicyDecision.ESCALATE,
                action="escalate",
                reason_codes=escalate_reasons,
                checks=checks,
                explanation=f"Policy requirements not met for automatic action: {reasons_text}. Escalated to human review.",
            )

        # ──────────────────────────────────────────────
        # LEVEL 4: APPROVAL
        # ──────────────────────────────────────────────

        # Rule 10: All mandatory checks pass
        checks.append(PolicyCheckTrace(
            rule_number=10,
            rule_name="all_mandatory_checks_passed",
            passed=True,
            detail="All deterministic policy checks passed successfully.",
        ))
        reason_codes.append(PolicyReasonCode.POLICY_APPROVED)

        return PolicyResult(
            decision=PolicyDecision.APPROVE,
            action=norm_action,
            reason_codes=reason_codes,
            checks=checks,
            explanation=f"Policy APPROVED '{norm_action}' action. All 10 deterministic checks passed.",
        )
