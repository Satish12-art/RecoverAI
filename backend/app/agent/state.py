"""State definitions and bounds for the RecoverAI Bounded State Machine Agent."""

from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field

# Maximum agent execution bounds
MAX_AGENT_STEPS = 10
MAX_LLM_CALLS = 3
AGENT_TIMEOUT_SECONDS = 30.0


class AgentStep(str, Enum):
    DETECTED = "DETECTED"
    ELIGIBILITY_CHECK = "ELIGIBILITY_CHECK"
    CONTEXT_LOADING = "CONTEXT_LOADING"
    SCORING = "SCORING"
    DIAGNOSING = "DIAGNOSING"
    DECISION_PENDING = "DECISION_PENDING"
    POLICY_CHECK = "POLICY_CHECK"
    ACTION_EXECUTION = "ACTION_EXECUTION"
    OBSERVING_RESULT = "OBSERVING_RESULT"
    TERMINAL = "TERMINAL"


class TerminalState(str, Enum):
    RECOVERING = "RECOVERING"
    RECOVERED = "RECOVERED"
    FAILED = "FAILED"
    ESCALATED = "ESCALATED"
    STOPPED = "STOPPED"
    ERROR = "ERROR"


class StepTrace(BaseModel):
    step: AgentStep
    status: str
    details: Optional[dict[str, Any]] = None
    timestamp: str
