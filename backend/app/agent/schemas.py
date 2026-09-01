"""Pydantic schemas for structured LLM input context, output recommendations, and execution runs."""

from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field

from app.agent.state import StepTrace, TerminalState
from app.policies.policy_engine import PolicyDecision, PolicyReasonCode


class AllowedAction(str, Enum):
    RETRY = "retry"
    MESSAGE = "message"
    ESCALATE = "escalate"
    STOP = "stop"


class PaymentContext(BaseModel):
    id: int
    amount: float
    currency: str
    status: str
    failure_code: Optional[str] = None
    failure_reason: Optional[str] = None
    payment_method: Optional[str] = None
    risk_flagged: bool


class CustomerContext(BaseModel):
    id: int
    name: str
    customer_tenure_days: int
    total_orders: int
    successful_payments: int
    failed_payments: int
    historical_success_rate: float
    average_order_value: float
    chargeback_count: int
    refund_count: int
    opted_out: bool


class ScoringContext(BaseModel):
    recovery_probability: float
    scorer_confidence: float
    expected_recovery_value: float
    previous_recovery_attempts: int
    contributing_factors: list[dict[str, Any]] = Field(default_factory=list)


class AgentContext(BaseModel):
    """Production-facing context provided to the LLM."""
    payment: PaymentContext
    customer: CustomerContext
    scoring: ScoringContext


class LLMDiagnosis(BaseModel):
    failure_category: str
    summary: str


class LLMRecommendation(BaseModel):
    action: AllowedAction
    reason: str


class LLMStructuredOutput(BaseModel):
    diagnosis: LLMDiagnosis
    recommendation: LLMRecommendation
    message_personalization: Optional[str] = None


class AgentRunResult(BaseModel):
    case_id: int
    final_state: TerminalState
    recommended_action: Optional[str] = None
    policy_decision: Optional[str] = None
    policy_reason_codes: list[str] = Field(default_factory=list)
    recovery_probability: Optional[float] = None
    scorer_confidence: Optional[float] = None
    expected_recovery_value: Optional[float] = None
    action_executed: bool = False
    agent_action_id: Optional[int] = None
    recovery_outcome_id: Optional[int] = None
    trace: list[StepTrace] = Field(default_factory=list)
    llm_calls_made: int = 0
    total_steps: int = 0
    execution_time_seconds: float = 0.0
    error: Optional[str] = None
