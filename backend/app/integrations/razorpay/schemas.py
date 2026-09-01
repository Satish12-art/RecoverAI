"""Pydantic schemas for Razorpay Webhook payloads and internal normalized payment events."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RazorpayPaymentEntity(BaseModel):
    """Raw Razorpay Payment Entity schema."""
    id: str
    entity: str = "payment"
    amount: int  # in paise (e.g. 499900 = ₹4,999.00)
    currency: str = "INR"
    status: str  # created, authorized, captured, refunded, failed
    order_id: Optional[str] = None
    invoice_id: Optional[str] = None
    international: bool = False
    method: str = "card"
    amount_refunded: int = 0
    refund_status: Optional[str] = None
    captured: bool = False
    description: Optional[str] = None
    card_id: Optional[str] = None
    bank: Optional[str] = None
    wallet: Optional[str] = None
    vpa: Optional[str] = None
    email: Optional[str] = None
    contact: Optional[str] = None
    customer_id: Optional[str] = None
    error_code: Optional[str] = None
    error_description: Optional[str] = None
    error_source: Optional[str] = None
    error_step: Optional[str] = None
    error_reason: Optional[str] = None
    notes: Dict[str, Any] = Field(default_factory=dict)
    fee: Optional[int] = None
    tax: Optional[int] = None
    error_metadata: Optional[Dict[str, Any]] = None
    created_at: int = 0


class RazorpayWebhookPayload(BaseModel):
    """Standard Razorpay Webhook envelope."""
    entity: str = "event"
    account_id: Optional[str] = None
    event: str  # e.g. payment.failed, payment.captured, payment.authorized
    contains: List[str] = Field(default_factory=list)
    payload: Dict[str, Any]  # contains payment, order, etc.
    created_at: int = 0


class NormalizedPaymentEvent(BaseModel):
    """Internal canonical normalized event model."""
    event_id: str
    event_type: str  # payment.failed | payment.captured | payment.authorized | unknown
    external_payment_id: str
    external_order_id: Optional[str] = None
    external_customer_id: Optional[str] = None
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    amount_inr: float
    currency: str = "INR"
    payment_method: str = "card"
    status: str  # failed | successful | authorized | pending
    failure_code: Optional[str] = None  # canonical RecoverAI failure code
    failure_reason: Optional[str] = None
    risk_flagged: bool = False
    occurred_at: datetime
    raw_event_name: str
    is_test_mode: bool = True


class PaymentUpdateLinkResponse(BaseModel):
    """Safe test mode payment link response."""
    payment_link_id: str
    short_url: str
    amount_inr: float
    currency: str = "INR"
    status: str = "created"
    is_test_mode: bool = True
    expires_at: Optional[str] = None
