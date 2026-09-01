"""Razorpay Webhook API endpoints."""

import json
import uuid
import hmac
import hashlib
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.config import settings
from app.core.database import get_db
from app.models.models import WebhookEvent
from app.integrations.razorpay.service import RazorpayWebhookService

router = APIRouter()


class TestWebhookTriggerRequest(BaseModel):
    """Payload for triggering a simulated Razorpay test webhook."""
    event_type: str = "payment.failed"  # payment.failed | payment.captured | payment.authorized
    amount: float = 4999.0
    failure_code: str = "BAD_REQUEST_ERROR"
    failure_reason: str = "temporary_bank_error"
    customer_email: str = "test.merchant@example.com"
    customer_name: str = "Test Customer"
    payment_method: str = "card"


@router.get("/razorpay/status")
def get_razorpay_status(db: Session = Depends(get_db)):
    """Get current status of Razorpay test-mode integration without exposing secrets."""
    is_configured = bool(settings.razorpay_key_id or settings.razorpay_webhook_secret)
    
    last_event = db.query(WebhookEvent).filter(
        WebhookEvent.provider == "razorpay"
    ).order_by(WebhookEvent.id.desc()).first()

    return {
        "configured": is_configured,
        "mode": "test_mode",
        "webhook_ready": True,
        "webhook_endpoint": "/api/webhooks/razorpay",
        "last_event_at": last_event.created_at.isoformat() if last_event and last_event.created_at else None,
        "last_event_type": last_event.event_type if last_event else None,
        "last_processing_result": "processed" if last_event and last_event.processed else ("none" if not last_event else "failed"),
    }


@router.post("/razorpay")
async def ingest_razorpay_webhook(
    request: Request,
    x_razorpay_signature: Optional[str] = Header(None, alias="X-Razorpay-Signature"),
    x_razorpay_event_id: Optional[str] = Header(None, alias="X-Razorpay-Event-Id"),
    db: Session = Depends(get_db),
):
    """Ingest Razorpay webhook event with signature verification and idempotency."""
    raw_body = await request.body()
    event_id = x_razorpay_event_id or f"evt_{uuid.uuid4().hex[:14]}"

    result = RazorpayWebhookService.process_webhook(
        raw_body=raw_body,
        signature=x_razorpay_signature,
        event_id=event_id,
        db=db,
    )

    if result.get("status") == "rejected":
        raise HTTPException(
            status_code=400,
            detail=result.get("message", "Webhook processing failed"),
        )

    return result


@router.post("/razorpay/test-trigger")
def trigger_test_webhook(
    payload: TestWebhookTriggerRequest,
    db: Session = Depends(get_db),
):
    """Interactive demo / development test console endpoint that generates a realistic Razorpay event."""
    event_id = f"evt_test_{uuid.uuid4().hex[:12]}"
    payment_id = f"pay_test_{uuid.uuid4().hex[:12]}"
    order_id = f"order_test_{uuid.uuid4().hex[:12]}"
    amount_paise = int(payload.amount * 100)

    # Build standard Razorpay webhook structure
    simulated_payload = {
        "entity": "event",
        "account_id": "acc_test_recoverai",
        "event": payload.event_type,
        "contains": ["payment"],
        "payload": {
            "payment": {
                "entity": {
                    "id": payment_id,
                    "entity": "payment",
                    "amount": amount_paise,
                    "currency": "INR",
                    "status": "failed" if payload.event_type == "payment.failed" else "captured",
                    "order_id": order_id,
                    "method": payload.payment_method,
                    "email": payload.customer_email,
                    "contact": "+919876543210",
                    "error_code": payload.failure_code,
                    "error_description": payload.failure_reason,
                    "error_source": "issuer",
                    "error_step": "payment_authorization",
                    "error_reason": payload.failure_reason,
                    "notes": {
                        "customer_name": payload.customer_name,
                        "customer_email": payload.customer_email,
                        "source": "recoverai_test_console",
                    },
                }
            }
        },
        "created_at": 1724450000,
    }

    raw_body = json.dumps(simulated_payload).encode("utf-8")
    secret = settings.razorpay_webhook_secret or "test_webhook_secret"
    signature = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()

    result = RazorpayWebhookService.process_webhook(
        raw_body=raw_body,
        signature=signature,
        event_id=event_id,
        db=db,
    )

    return {
        "trigger": "success",
        "event_id": event_id,
        "result": result,
        "is_test_mode": True,
    }
