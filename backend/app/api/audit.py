"""Audit trail API endpoints reading directly from agent_actions and policy evaluations."""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import AgentAction, RecoveryCase, Payment, Customer

router = APIRouter()


@router.get("")
@router.get("/")
def list_audit_events(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    tool_name: Optional[str] = None,
    policy_decision: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List agent actions, tool calls, and policy governance decisions with pagination and filters."""
    query = db.query(AgentAction).order_by(AgentAction.id.desc())

    if tool_name:
        query = query.filter(AgentAction.tool_name == tool_name)

    if policy_decision:
        query = query.filter(AgentAction.policy_decision == policy_decision.upper())

    if search:
        search_fmt = f"%{search}%"
        query = query.filter(
            (AgentAction.tool_name.ilike(search_fmt)) |
            (AgentAction.reasoning_summary.ilike(search_fmt)) |
            (AgentAction.policy_reason.ilike(search_fmt))
        )

    total = query.count()
    actions = query.offset((page - 1) * page_size).limit(page_size).all()

    items = []
    for a in actions:
        case = db.query(RecoveryCase).filter(RecoveryCase.id == a.recovery_case_id).first() if a.recovery_case_id else None
        pmt = db.query(Payment).filter(Payment.id == case.payment_id).first() if case else None

        items.append({
            "id": a.id,
            "recovery_case_id": a.recovery_case_id,
            "external_payment_id": pmt.external_payment_id if pmt else None,
            "payment_amount": float(pmt.amount) if pmt else (float(case.amount_at_risk) if case else None),
            "action_type": a.action_type,
            "tool_name": a.tool_name,
            "reasoning_summary": a.reasoning_summary,
            "policy_decision": a.policy_decision,
            "policy_reason": a.policy_reason,
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "actor": "RecoverAI Agent",
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }
