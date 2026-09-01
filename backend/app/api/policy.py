"""Policy Engine evaluation API endpoint."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import Payment, Customer
from app.policies.policy_engine import PolicyEngine, PolicyResult

router = APIRouter()


class PolicyEvaluationRequest(BaseModel):
    payment_id: Optional[int] = None
    proposed_action: str = Field(default="retry", description="retry | message | escalate | stop")
    recovery_probability: Optional[float] = None
    scorer_confidence: Optional[float] = None
    previous_recovery_attempts: int = 0
    payment_data: Optional[dict] = None
    customer_data: Optional[dict] = None


@router.post("/evaluate", response_model=PolicyResult)
def evaluate_policy_endpoint(req: PolicyEvaluationRequest, db: Session = Depends(get_db)):
    """Evaluate a proposed action against deterministic policy rules.
    
    This endpoint evaluates policy decisions only. It does NOT execute any financial actions.
    """
    payment_obj = req.payment_data
    customer_obj = req.customer_data

    if req.payment_id is not None:
        payment = db.query(Payment).filter(Payment.id == req.payment_id).first()
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")
        payment_obj = payment
        customer = db.query(Customer).filter(Customer.id == payment.customer_id).first()
        customer_obj = customer

    if payment_obj is None:
        raise HTTPException(status_code=400, detail="Must provide payment_id or payment_data")

    return PolicyEngine.evaluate(
        payment=payment_obj,
        customer=customer_obj,
        proposed_action=req.proposed_action,
        recovery_probability=req.recovery_probability,
        scorer_confidence=req.scorer_confidence,
        previous_recovery_attempts=req.previous_recovery_attempts,
    )
