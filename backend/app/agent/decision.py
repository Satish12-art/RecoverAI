"""Decision recommendation component."""

from app.agent.llm_client import LLMClient
from app.agent.schemas import AgentContext, LLMRecommendation, AllowedAction, LLMStructuredOutput


class RecoveryDecisionEngine:
    """Produces structured action recommendations using the LLM client."""

    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    def recommend_action(self, context: AgentContext) -> LLMStructuredOutput:
        """Obtain structured decision containing diagnosis, recommendation, and optional message note."""
        return self.llm_client.generate_structured_decision(context)
