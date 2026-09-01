"""Payments API endpoints with deterministic revenue intelligence."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import Payment, Customer
from app.schemas.schemas import PaymentResponse
from app.services.eligibility import EligibilityGate, EligibilityResult
from app.services.recovery_scorer import RecoveryScorer, RecoveryScore

router = APIRouter()


@router.get("", response_model=dict)
@router.get("/", response_model=dict)
def list_payments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    db: Session = Depends(get_db),
):
    """List payments with pagination and status filter."""
    query = db.query(Payment)
    if status:
        query = query.filter(Payment.status == status)

    total = query.count()
    items = query.order_by(Payment.id.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return {
        "items": [PaymentResponse.model_validate(p) for p in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{payment_id}", response_model=PaymentResponse)
def get_payment(payment_id: int, db: Session = Depends(get_db)):
    """Get single payment details."""
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return PaymentResponse.model_validate(payment)


@router.get("/{payment_id}/eligibility", response_model=EligibilityResult)
def get_payment_eligibility(payment_id: int, db: Session = Depends(get_db)):
    """Evaluate deterministic eligibility for a payment."""
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    customer = db.query(Customer).filter(Customer.id == payment.customer_id).first()
    return EligibilityGate.evaluate(payment=payment, customer=customer)


@router.get("/{payment_id}/score", response_model=RecoveryScore)
def get_payment_score(payment_id: int, db: Session = Depends(get_db)):
    """Calculate deterministic recovery score and expected recovery value for a payment."""
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    customer = db.query(Customer).filter(Customer.id == payment.customer_id).first()
    return RecoveryScorer.calculate_score(payment=payment, customer=customer)


@router.get("/{payment_id}/recovery-analysis")
def get_payment_recovery_analysis(payment_id: int, db: Session = Depends(get_db)):
    """Comprehensive recovery analysis: eligibility + scoring + expected recovery value."""
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    customer = db.query(Customer).filter(Customer.id == payment.customer_id).first()

    eligibility = EligibilityGate.evaluate(payment=payment, customer=customer)
    score = RecoveryScorer.calculate_score(payment=payment, customer=customer)

    return {
        "payment": PaymentResponse.model_validate(payment),
        "eligibility": eligibility,
        "scoring": score,
    }
