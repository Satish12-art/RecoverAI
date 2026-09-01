"""Naive Retry Baseline Strategy for Evaluation Comparison.

Represents a conventional, non-AI recovery strategy:
Retries all non-risk failed payments up to hard limits.
Strictly ground-truth blind and fair.
"""

from typing import Optional
from pydantic import BaseModel


class BaselineDecision(BaseModel):
    action: str  # "retry" | "stop" | "escalate"
    reason: str


class NaiveRetryBaseline:
    """Conventional recovery policy retrying failed payments."""

    @classmethod
    def evaluate(
        cls,
        payment_amount: float,
        risk_flagged: bool,
        opted_out: bool,
        failure_code: Optional[str] = None,
        retry_count: int = 0,
        max_retries: int = 2,
        amount_limit: float = 50000.0,
    ) -> BaselineDecision:
        """Produce a naive baseline decision given observable context."""
        # 1. Hard safety stops
        if risk_flagged or opted_out or failure_code == "risk_flagged":
            return BaselineDecision(
                action="stop",
                reason="Safety check: risk flagged or customer opted out.",
            )

        # 2. Hard escalation limits
        if retry_count >= max_retries:
            return BaselineDecision(
                action="escalate",
                reason="Retry limit reached.",
            )

        if payment_amount > amount_limit:
            return BaselineDecision(
                action="escalate",
                reason="Transaction amount exceeds automated limit.",
            )

        # 3. Default naive action: Retry
        return BaselineDecision(
            action="retry",
            reason="Conventional strategy: automatic retry of failed transaction.",
        )
