"""Recovery cases API endpoints with real database models and agent trace details."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import Customer, Payment, RecoveryCase, AgentAction, RecoveryOutcome
from app.services.recovery_scorer import RecoveryScorer

router = APIRouter()


@router.get("")
@router.get("/")
def list_cases(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    action: Optional[str] = None,
    failure_code: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = Query("expected_recovery_value", description="expected_recovery_value | amount | id"),
    db: Session = Depends(get_db),
):
    """List recovery cases with rich filters, sorting by ERV DESC by default."""
    query = db.query(RecoveryCase).join(Payment, RecoveryCase.payment_id == Payment.id).join(Customer, RecoveryCase.customer_id == Customer.id)

    if status:
        query = query.filter(RecoveryCase.status == status.upper())

    if action:
        query = query.filter(RecoveryCase.recommended_action == action.lower())

    if failure_code:
        query = query.filter(Payment.failure_code == failure_code)

    if search:
        search_fmt = f"%{search}%"
        query = query.filter(
            (Payment.external_payment_id.ilike(search_fmt)) |
            (Customer.name.ilike(search_fmt)) |
            (Customer.external_customer_id.ilike(search_fmt))
        )

    # Sorting
    if sort_by == "amount":
        query = query.order_by(RecoveryCase.amount_at_risk.desc())
    elif sort_by == "id":
        query = query.order_by(RecoveryCase.id.desc())
    else:
        # Default sort by expected_recovery_value DESC
        query = query.order_by(RecoveryCase.expected_recovery_value.desc().nullslast(), RecoveryCase.amount_at_risk.desc())

    total = query.count()
    cases = query.offset((page - 1) * page_size).limit(page_size).all()

    items = []
    for c in cases:
        pmt = db.query(Payment).filter(Payment.id == c.payment_id).first()
        cust = db.query(Customer).filter(Customer.id == c.customer_id).first()
        latest_outcome = db.query(RecoveryOutcome).filter(RecoveryOutcome.recovery_case_id == c.id).order_by(RecoveryOutcome.id.desc()).first()

        items.append({
            "id": c.id,
            "payment_id": c.payment_id,
            "external_payment_id": pmt.external_payment_id if pmt else f"pay_{c.payment_id:07d}",
            "customer_id": c.customer_id,
            "customer_name": cust.name if cust else f"Customer #{c.customer_id}",
            "amount_at_risk": float(c.amount_at_risk or 0.0),
            "currency": pmt.currency if pmt else "INR",
            "failure_code": pmt.failure_code if pmt else None,
            "recovery_probability": float(c.recovery_probability) if c.recovery_probability is not None else None,
            "scorer_confidence": float(c.scorer_confidence) if c.scorer_confidence is not None else None,
            "expected_recovery_value": float(c.expected_recovery_value) if c.expected_recovery_value is not None else round(float(c.amount_at_risk or 0.0) * float(c.recovery_probability or 0.0), 2),
            "recommended_action": c.recommended_action,
            "actual_action": c.actual_action,
            "status": c.status,
            "outcome_status": latest_outcome.outcome_status if latest_outcome else None,
            "amount_recovered": float(latest_outcome.amount_recovered or 0.0) if latest_outcome else 0.0,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{case_id}")
def get_case_detail(case_id: int, db: Session = Depends(get_db)):
    """Get comprehensive case details with customer context, scoring factors, policy checks, and agent trace."""
    case = db.query(RecoveryCase).filter(RecoveryCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Recovery case not found")

    pmt = db.query(Payment).filter(Payment.id == case.payment_id).first()
    cust = db.query(Customer).filter(Customer.id == case.customer_id).first()

    # Calculate real-time recovery score if not already populated
    score = None
    if pmt and cust:
        score = RecoveryScorer.calculate_score(pmt, cust)

    actions = db.query(AgentAction).filter(AgentAction.recovery_case_id == case.id).order_by(AgentAction.id.asc()).all()
    outcomes = db.query(RecoveryOutcome).filter(RecoveryOutcome.recovery_case_id == case.id).order_by(RecoveryOutcome.id.asc()).all()

    return {
        "case": {
            "id": case.id,
            "payment_id": case.payment_id,
            "customer_id": case.customer_id,
            "amount_at_risk": float(case.amount_at_risk or 0.0),
            "expected_recovery_value": float(case.expected_recovery_value) if case.expected_recovery_value is not None else (score.expected_recovery_value if score else 0.0),
            "diagnosis": case.diagnosis,
            "recoverability": case.recoverability,
            "recovery_probability": float(case.recovery_probability) if case.recovery_probability is not None else (score.recovery_probability if score else 0.0),
            "scorer_confidence": float(case.scorer_confidence) if case.scorer_confidence is not None else (score.confidence if score else 0.0),
            "recommended_action": case.recommended_action,
            "actual_action": case.actual_action,
            "status": case.status,
            "escalation_reason": case.escalation_reason,
            "retry_count": case.retry_count,
            "created_at": case.created_at.isoformat() if case.created_at else None,
            "updated_at": case.updated_at.isoformat() if case.updated_at else None,
        },
        "payment": {
            "id": pmt.id if pmt else case.payment_id,
            "external_payment_id": pmt.external_payment_id if pmt else f"pay_{case.payment_id:07d}",
            "amount": float(pmt.amount) if pmt else float(case.amount_at_risk or 0.0),
            "currency": pmt.currency if pmt else "INR",
            "status": pmt.status if pmt else "failed",
            "payment_method": pmt.payment_method if pmt else "card",
            "failure_code": pmt.failure_code if pmt else None,
            "failure_reason": pmt.failure_reason if pmt else None,
            "risk_flagged": bool(pmt.risk_flagged) if pmt else False,
            "created_at": pmt.created_at.isoformat() if pmt and pmt.created_at else None,
        },
        "customer": {
            "id": cust.id if cust else case.customer_id,
            "external_customer_id": cust.external_customer_id if cust else f"cust_{case.customer_id:06d}",
            "name": cust.name if cust else f"Customer #{case.customer_id}",
            "email": cust.email if cust else None,
            "total_orders": cust.total_orders if cust else 0,
            "successful_payments": cust.successful_payments if cust else 0,
            "failed_payments": cust.failed_payments if cust else 0,
            "refund_count": cust.refund_count if cust else 0,
            "chargeback_count": cust.chargeback_count if cust else 0,
            "customer_tenure_days": cust.customer_tenure_days if cust else 0,
            "opted_out": bool(cust.opted_out) if cust else False,
        },
        "scoring_factors": score.model_dump() if score else None,
        "actions": [
            {
                "id": a.id,
                "action_type": a.action_type,
                "tool_name": a.tool_name,
                "reasoning_summary": a.reasoning_summary,
                "policy_decision": a.policy_decision,
                "policy_reason": a.policy_reason,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in actions
        ],
        "outcomes": [
            {
                "id": o.id,
                "action": o.action,
                "outcome_status": o.outcome_status,
                "successful": o.successful,
                "amount_recovered": float(o.amount_recovered or 0.0),
                "failure_reason": o.failure_reason,
                "outcome_source": o.outcome_source,
                "outcome_observed_at": o.outcome_observed_at.isoformat() if o.outcome_observed_at else None,
            }
            for o in outcomes
        ],
    }
