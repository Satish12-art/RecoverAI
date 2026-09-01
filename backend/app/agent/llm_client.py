"""LLM Client Abstraction supporting Deterministic Mock Mode and Real Providers."""

import json
import logging
from abc import ABC, abstractmethod
from typing import Optional

from app.agent.prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from app.agent.schemas import (
    AgentContext,
    AllowedAction,
    LLMDiagnosis,
    LLMRecommendation,
    LLMStructuredOutput,
)
from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMClient(ABC):
    """Abstract interface for LLM Decision Support."""

    @abstractmethod
    def generate_structured_decision(self, context: AgentContext) -> LLMStructuredOutput:
        """Generate structured diagnosis and action recommendation given observable context."""
        pass


class MockLLMClient(LLMClient):
    """Deterministic Mock LLM Client reasoning strictly on observable context (Zero Ground Truth)."""

    def generate_structured_decision(self, context: AgentContext) -> LLMStructuredOutput:
        pmt = context.payment
        cust = context.customer
        sc = context.scoring

        # Case 1: Hard Risk / Fraud / Opt-Out
        if pmt.risk_flagged or cust.opted_out:
            return LLMStructuredOutput(
                diagnosis=LLMDiagnosis(
                    failure_category="high_risk_or_opted_out",
                    summary="Payment flagged for risk or customer has opted out of communications.",
                ),
                recommendation=LLMRecommendation(
                    action=AllowedAction.STOP,
                    reason="Security stop required due to risk flag or customer opt-out status.",
                ),
            )

        # Case 2: Escalation criteria (Low probability, low confidence, high amount, or retry limit)
        if sc.recovery_probability < settings.recovery_probability_threshold:
            return LLMStructuredOutput(
                diagnosis=LLMDiagnosis(
                    failure_category="low_recovery_likelihood",
                    summary=f"Recovery probability ({sc.recovery_probability:.2f}) is below automated threshold ({settings.recovery_probability_threshold:.2f}).",
                ),
                recommendation=LLMRecommendation(
                    action=AllowedAction.ESCALATE,
                    reason="Low recovery probability requires merchant manual review.",
                ),
            )

        if sc.scorer_confidence < settings.scorer_confidence_threshold:
            return LLMStructuredOutput(
                diagnosis=LLMDiagnosis(
                    failure_category="low_scorer_confidence",
                    summary=f"Scorer confidence ({sc.scorer_confidence:.2f}) is below threshold ({settings.scorer_confidence_threshold:.2f}).",
                ),
                recommendation=LLMRecommendation(
                    action=AllowedAction.ESCALATE,
                    reason="Low confidence score indicates ambiguous payment history.",
                ),
            )

        if pmt.amount > settings.auto_recovery_amount_limit:
            return LLMStructuredOutput(
                diagnosis=LLMDiagnosis(
                    failure_category="high_value_transaction",
                    summary=f"Transaction amount (₹{pmt.amount:,.2f}) exceeds auto-recovery threshold (₹{settings.auto_recovery_amount_limit:,.2f}).",
                ),
                recommendation=LLMRecommendation(
                    action=AllowedAction.ESCALATE,
                    reason="High-value transaction requires human oversight.",
                ),
            )

        if sc.previous_recovery_attempts >= settings.max_retries:
            return LLMStructuredOutput(
                diagnosis=LLMDiagnosis(
                    failure_category="max_retries_exceeded",
                    summary=f"Maximum allowable recovery attempts ({settings.max_retries}) already reached.",
                ),
                recommendation=LLMRecommendation(
                    action=AllowedAction.ESCALATE,
                    reason="Repeated attempts exhausted; escalating to merchant ops.",
                ),
            )

        # Case 3: Customer Action Required Failures (Expired card, authentication failure, etc.)
        msg_failure_codes = {
            "expired_card",
            "invalid_card",
            "incorrect_pin",
            "customer_cancelled",
            "authentication_failed",
            "card_declined",
            "pin_incorrect",
        }
        if pmt.failure_code in msg_failure_codes:
            return LLMStructuredOutput(
                diagnosis=LLMDiagnosis(
                    failure_category="customer_action_required",
                    summary=f"Payment failed due to {pmt.failure_code.replace('_', ' ')}. Customer needs to update details.",
                ),
                recommendation=LLMRecommendation(
                    action=AllowedAction.MESSAGE,
                    reason="Sending a recovery message allows the customer to update their payment method safely.",
                ),
                message_personalization="Please update your payment method to complete your order.",
            )

        # Case 4: Transient Technical / Network Failure
        return LLMStructuredOutput(
            diagnosis=LLMDiagnosis(
                failure_category="temporary_bank_error",
                summary=f"Payment failed due to transient error ({pmt.failure_code or 'temporary_error'}) with strong customer history.",
            ),
            recommendation=LLMRecommendation(
                action=AllowedAction.RETRY,
                reason="High recovery probability and transient failure code support an automatic retry.",
            ),
        )


class RealLLMClient(LLMClient):
    """Real Provider LLM Client (OpenAI-compatible / Provider abstraction)."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or getattr(settings, "llm_api_key", None)
        self.model = model or getattr(settings, "llm_model", "gpt-4o-mini")

    def generate_structured_decision(self, context: AgentContext) -> LLMStructuredOutput:
        # Fallback to mock if API key is not configured or in testing environment
        if not self.api_key:
            logger.warning("No LLM API key configured. Falling back to MockLLMClient.")
            return MockLLMClient().generate_structured_decision(context)

        import urllib.request

        context_json = context.model_dump_json(indent=2)
        prompt = USER_PROMPT_TEMPLATE.format(context_json=context_json)

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.0,
        }

        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                content = data["choices"][0]["message"]["content"]
                parsed = json.loads(content)
                return LLMStructuredOutput.model_validate(parsed)
        except Exception as e:
            logger.error(f"Real LLM call failed: {e}. Falling back to safe escalation.")
            raise RuntimeError(f"LLM Provider Error: {str(e)}")


def get_llm_client() -> LLMClient:
    """Factory function returning the configured LLM client."""
    mode = getattr(settings, "llm_mode", "mock").lower()
    if mode == "real":
        return RealLLMClient()
    return MockLLMClient()
