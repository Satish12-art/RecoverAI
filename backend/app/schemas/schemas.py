"""Pydantic schemas for API request/response validation."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ──────────────────────────────────────────────────
# Health & Config
# ──────────────────────────────────────────────────
class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "0.1.0"
    mode: str
    demo_mode: bool


class ConfigResponse(BaseModel):
    recovery_mode: str
    demo_mode: bool
    version: str = "0.1.0"
    recovery_probability_threshold: float
    scorer_confidence_threshold: float
    auto_recovery_amount_limit: float
    max_retries: int


# ──────────────────────────────────────────────────
# Customer
# ──────────────────────────────────────────────────
class CustomerBase(BaseModel):
    external_customer_id: str
    name: str
    email: Optional[str] = None
    total_orders: int = 0
    successful_payments: int = 0
    failed_payments: int = 0
    refund_count: int = 0
    chargeback_count: int = 0
    average_order_value: float = 0.0
    customer_tenure_days: int = 0
    opted_out: bool = False


class CustomerResponse(CustomerBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────────
# Payment
# ──────────────────────────────────────────────────
class PaymentBase(BaseModel):
    external_payment_id: str
    external_order_id: Optional[str] = None
    amount: float
    currency: str = "INR"
    status: str
    payment_method: Optional[str] = None
    failure_code: Optional[str] = None
    failure_reason: Optional[str] = None
    risk_flagged: bool = False


class PaymentResponse(PaymentBase):
    id: int
    customer_id: int
    order_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────────
# Recovery Case
# ──────────────────────────────────────────────────
class RecoveryCaseBase(BaseModel):
    amount_at_risk: float
    expected_recovery_value: Optional[float] = None
    diagnosis: Optional[str] = None
    recoverability: Optional[str] = None
    recovery_probability: Optional[float] = None
    scorer_confidence: Optional[float] = None
    recommended_action: Optional[str] = None
    actual_action: Optional[str] = None
    status: str = "OPEN"
    escalation_reason: Optional[str] = None
    retry_count: int = 0


class ScoringDetail(BaseModel):
    recovery_probability: Optional[float] = None
    scorer_confidence: Optional[float] = None
    expected_recovery_value: Optional[float] = None


class AgentTraceStep(BaseModel):
    step: int
    state: Optional[str] = None
    action_type: str
    tool_name: Optional[str] = None
    reasoning_summary: Optional[str] = None
    policy_decision: Optional[str] = None
    policy_reason: Optional[str] = None
    output_json: Optional[dict] = None
    created_at: datetime


class OutcomeDetail(BaseModel):
    successful: Optional[bool] = None
    amount_recovered: float = 0.0
    recovery_time_seconds: Optional[float] = None
    simulated: bool = True
    outcome_source: Optional[str] = None
    action_executed_at: Optional[datetime] = None
    outcome_observed_at: Optional[datetime] = None


class RecoveryCaseResponse(RecoveryCaseBase):
    id: int
    payment_id: int
    customer_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RecoveryCaseDetail(BaseModel):
    """Full case detail with payment, customer, scoring, trace, and outcome."""
    id: int
    payment: PaymentResponse
    customer: CustomerResponse
    scoring: ScoringDetail
    diagnosis: Optional[str] = None
    recoverability: Optional[str] = None
    recommended_action: Optional[str] = None
    actual_action: Optional[str] = None
    status: str
    amount_at_risk: float
    recovery_type: str = "automatic"  # automatic | human_review
    agent_trace: list[AgentTraceStep] = []
    outcome: Optional[OutcomeDetail] = None
    mode: str = "simulation"


# ──────────────────────────────────────────────────
# Recovery Opportunity (queue item)
# ──────────────────────────────────────────────────
class RecoveryOpportunity(BaseModel):
    case_id: int
    payment_id: str
    customer_name: str
    amount: float
    failure_code: Optional[str] = None
    recovery_probability: Optional[float] = None
    expected_recovery_value: Optional[float] = None
    recommended_action: Optional[str] = None
    recovery_type: str = "automatic"  # automatic | human_review
    status: str


class RecoveryOpportunitiesResponse(BaseModel):
    opportunities: list[RecoveryOpportunity]
    sort: str = "expected_recovery_value"
    total: int


# ──────────────────────────────────────────────────
# Dashboard
# ──────────────────────────────────────────────────
class DashboardResponse(BaseModel):
    gross_revenue_at_risk: float = 0.0
    potentially_recoverable_revenue: float = 0.0
    revenue_recovered: float = 0.0
    recovery_rate: float = 0.0
    total_expected_recovery_value: float = 0.0
    cases_processed: int = 0
    mode: str = "simulation"
    last_updated: Optional[datetime] = None


# ──────────────────────────────────────────────────
# Audit
# ──────────────────────────────────────────────────
class AuditEntry(BaseModel):
    id: int
    recovery_case_id: int
    action_type: str
    tool_name: Optional[str] = None
    reasoning_summary: Optional[str] = None
    policy_decision: Optional[str] = None
    policy_reason: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditResponse(BaseModel):
    entries: list[AuditEntry]
    total: int


# ──────────────────────────────────────────────────
# Pagination
# ──────────────────────────────────────────────────
class PaginatedResponse(BaseModel):
    items: list = []
    total: int = 0
    page: int = 1
    page_size: int = 20
