"""Diagnostic reasoning component for payment failures."""

from app.agent.llm_client import LLMClient
from app.agent.schemas import AgentContext, LLMDiagnosis


class PaymentDiagnoser:
    """Diagnoses payment failure context using the LLM client."""

    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    def diagnose(self, context: AgentContext) -> LLMDiagnosis:
        """Extract structured diagnosis from LLM decision."""
        decision = self.llm_client.generate_structured_decision(context)
        return decision.diagnosis
