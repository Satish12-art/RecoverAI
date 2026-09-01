"""Type definitions and standard result envelopes for RecoverAI Agent Tools."""

from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field

from app.policies.policy_engine import PolicyResult


class ToolType(str, Enum):
    READ = "READ"
    WRITE = "WRITE"


class ToolDefinition(BaseModel):
    """Metadata describing a tool in the Tool Registry."""
    name: str
    description: str
    tool_type: ToolType
    read_only: bool
    requires_policy: bool
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]


class ToolResult(BaseModel):
    """Standardized tool response envelope."""
    success: bool
    tool_name: str
    data: Optional[dict[str, Any]] = None
    policy: Optional[PolicyResult] = None
    error: Optional[str] = None


class PaymentInfo(BaseModel):
    id: int
    external_payment_id: str
    external_order_id: Optional[str] = None
    customer_id: int
    order_id: Optional[int] = None
    amount: float
    currency: str
    status: str
    payment_method: Optional[str] = None
    failure_code: Optional[str] = None
    failure_reason: Optional[str] = None
    risk_flagged: bool
    created_at: str
    updated_at: str


class OrderInfo(BaseModel):
    id: int
    external_order_id: str
    customer_id: int
    amount: float
    currency: str
    status: str
    created_at: str
    updated_at: str


class CustomerInfo(BaseModel):
    id: int
    external_customer_id: str
    name: str
    email: Optional[str] = None
    total_orders: int
    successful_payments: int
    failed_payments: int
    refund_count: int
    chargeback_count: int
    average_order_value: float
    customer_tenure_days: int
    opted_out: bool
    created_at: str


class CustomerHistoryContext(BaseModel):
    customer_id: int
    total_orders: int
    successful_payments: int
    failed_payments: int
    historical_success_rate: float
    average_order_value: float
    chargeback_count: int
    refund_count: int
    customer_tenure_days: int
    opted_out: bool
    prior_recovery_cases_count: int
    prior_successful_recoveries: int


class RecoveryCaseInfo(BaseModel):
    id: int
    payment_id: int
    customer_id: int
    amount_at_risk: float
    expected_recovery_value: Optional[float] = None
    recovery_probability: Optional[float] = None
    scorer_confidence: Optional[float] = None
    recommended_action: Optional[str] = None
    actual_action: Optional[str] = None
    status: str
    retry_count: int
    escalation_reason: Optional[str] = None
    created_at: str
    updated_at: str


class RecoveryStatusInfo(BaseModel):
    case_id: int
    case_status: str
    retry_count: int
    latest_action: Optional[str] = None
    action_type: Optional[str] = None
    outcome_status: Optional[str] = None
    outcome_source: Optional[str] = None
    is_recovered: bool = False
    amount_recovered: float = 0.0
    action_executed_at: Optional[str] = None
    outcome_observed_at: Optional[str] = None
