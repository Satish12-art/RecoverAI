"""SQLAlchemy models for all 7 RecoverAI tables.

Schema matches the v2.1 architecture plan exactly.
"""

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


# ──────────────────────────────────────────────────
# customers
# ──────────────────────────────────────────────────
class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    external_customer_id = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=True)
    total_orders = Column(Integer, default=0)
    successful_payments = Column(Integer, default=0)
    failed_payments = Column(Integer, default=0)
    refund_count = Column(Integer, default=0)
    chargeback_count = Column(Integer, default=0)
    average_order_value = Column(Float, default=0.0)
    customer_tenure_days = Column(Integer, default=0)
    opted_out = Column(Boolean, default=False)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    # Relationships
    orders = relationship("Order", back_populates="customer")
    payments = relationship("Payment", back_populates="customer")
    recovery_cases = relationship("RecoveryCase", back_populates="customer")


# ──────────────────────────────────────────────────
# orders
# ──────────────────────────────────────────────────
class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    external_order_id = Column(String, unique=True, nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String, default="INR")
    status = Column(String, nullable=False)  # created, paid, failed
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    # Relationships
    customer = relationship("Customer", back_populates="orders")
    payments = relationship("Payment", back_populates="order")


# ──────────────────────────────────────────────────
# payments
# ──────────────────────────────────────────────────
class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    external_payment_id = Column(String, unique=True, nullable=False, index=True)
    external_order_id = Column(String, nullable=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    amount = Column(Float, nullable=False)
    currency = Column(String, default="INR")
    status = Column(String, nullable=False)  # created, failed, paid, captured
    payment_method = Column(String, nullable=True)  # card, upi, netbanking, wallet
    failure_code = Column(String, nullable=True)
    failure_reason = Column(String, nullable=True)
    risk_flagged = Column(Boolean, default=False)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    # Relationships
    customer = relationship("Customer", back_populates="payments")
    order = relationship("Order", back_populates="payments")
    recovery_cases = relationship("RecoveryCase", back_populates="payment")


# ──────────────────────────────────────────────────
# recovery_cases
# ──────────────────────────────────────────────────
CASE_STATUSES = [
    "OPEN",
    "ANALYZING",
    "ACTION_PENDING",
    "RECOVERING",
    "RECOVERED",
    "FAILED",
    "ESCALATED",
    "STOPPED",
]


class RecoveryCase(Base):
    __tablename__ = "recovery_cases"

    id = Column(Integer, primary_key=True, index=True)
    payment_id = Column(Integer, ForeignKey("payments.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    amount_at_risk = Column(Float, nullable=False)
    expected_recovery_value = Column(Float, nullable=True)
    diagnosis = Column(String, nullable=True)
    recoverability = Column(String, nullable=True)  # high, medium, low, none
    recovery_probability = Column(Float, nullable=True)
    scorer_confidence = Column(Float, nullable=True)
    recommended_action = Column(String, nullable=True)  # retry, message, escalate, stop
    actual_action = Column(String, nullable=True)
    status = Column(String, default="OPEN", nullable=False)
    escalation_reason = Column(String, nullable=True)
    retry_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    # Relationships
    payment = relationship("Payment", back_populates="recovery_cases")
    customer = relationship("Customer", back_populates="recovery_cases")
    agent_actions = relationship("AgentAction", back_populates="recovery_case")
    recovery_outcomes = relationship("RecoveryOutcome", back_populates="recovery_case")


# ──────────────────────────────────────────────────
# agent_actions (audit log)
# ──────────────────────────────────────────────────
class AgentAction(Base):
    __tablename__ = "agent_actions"

    id = Column(Integer, primary_key=True, index=True)
    recovery_case_id = Column(Integer, ForeignKey("recovery_cases.id"), nullable=False)
    action_type = Column(String, nullable=False)  # context_load, diagnose, score, policy_check, execute, observe_outcome
    tool_name = Column(String, nullable=True)
    input_json = Column(Text, nullable=True)  # JSON string
    output_json = Column(Text, nullable=True)  # JSON string
    reasoning_summary = Column(String, nullable=True)
    policy_decision = Column(String, nullable=True)  # APPROVED, REJECTED, ESCALATE, STOP
    policy_reason = Column(String, nullable=True)
    created_at = Column(DateTime, default=_utcnow)

    # Relationships
    recovery_case = relationship("RecoveryCase", back_populates="agent_actions")
    recovery_outcome = relationship("RecoveryOutcome", back_populates="agent_action", uselist=False)


# ──────────────────────────────────────────────────
# recovery_outcomes
# ──────────────────────────────────────────────────
class RecoveryOutcome(Base):
    __tablename__ = "recovery_outcomes"

    id = Column(Integer, primary_key=True, index=True)
    recovery_case_id = Column(Integer, ForeignKey("recovery_cases.id"), nullable=False)
    agent_action_id = Column(Integer, ForeignKey("agent_actions.id"), nullable=True)
    action = Column(String, nullable=False)  # retry, message, escalate, stop
    outcome_status = Column(String, default="pending")  # pending, observed, timed_out
    successful = Column(Boolean, nullable=True)  # null while pending
    amount_recovered = Column(Float, default=0.0)
    recovery_time_seconds = Column(Float, nullable=True)
    failure_reason = Column(String, nullable=True)
    outcome_source = Column(String, nullable=True)  # simulation, webhook, polling, manual
    simulated = Column(Boolean, default=True)
    action_executed_at = Column(DateTime, nullable=True)
    outcome_observed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=_utcnow)

    # Relationships
    recovery_case = relationship("RecoveryCase", back_populates="recovery_outcomes")
    agent_action = relationship("AgentAction", back_populates="recovery_outcome")


# ──────────────────────────────────────────────────
# webhook_events
# ──────────────────────────────────────────────────
class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String, nullable=False)  # razorpay
    external_event_id = Column(String, unique=True, nullable=False, index=True)
    event_type = Column(String, nullable=False)
    payload = Column(Text, nullable=True)  # JSON string
    signature_valid = Column(Boolean, default=False)
    processed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=_utcnow)

    __table_args__ = (
        UniqueConstraint("external_event_id", name="uq_webhook_external_event_id"),
    )
