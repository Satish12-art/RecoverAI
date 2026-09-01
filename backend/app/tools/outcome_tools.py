"""Safe, bounded outcome observation service for RecoverAI.

Internal system-facing operation to transition pending recovery actions into observed outcomes.
Guarantees:
- Outcomes cannot be fabricated by arbitrary callers
- Amount recovered cannot exceed original transaction amount
- Prevents duplicate outcome finalization
- Updates recovery case lifecycle and records audit trail
"""

import json
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session

from app.models.models import (
    Payment,
    RecoveryCase,
    AgentAction,
    RecoveryOutcome,
)
from app.tools.tool_types import ToolResult


def _utcnow():
    return datetime.now(timezone.utc)


def _to_naive_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


class OutcomeObserver:
    """System-facing outcome observation controller."""

    VALID_OUTCOMES = {"recovered", "failed", "escalated", "stopped"}
    VALID_SOURCES = {"simulation", "webhook", "polling", "manual"}

    @classmethod
    def observe_outcome(
        cls,
        db: Session,
        agent_action_id: int,
        outcome: str,
        amount_recovered: float,
        source: str = "simulation",
        failure_reason: Optional[str] = None,
    ) -> ToolResult:
        """Observe and finalize an outcome for an executed recovery action."""
        norm_outcome = (outcome or "").strip().lower()
        norm_source = (source or "simulation").strip().lower()

        # 1. Verify Outcome Type
        if norm_outcome not in cls.VALID_OUTCOMES:
            return ToolResult(
                success=False,
                tool_name="observe_outcome",
                error=f"Invalid outcome '{outcome}'. Allowed: {cls.VALID_OUTCOMES}.",
            )

        # 2. Verify Source
        if norm_source not in cls.VALID_SOURCES:
            return ToolResult(
                success=False,
                tool_name="observe_outcome",
                error=f"Invalid outcome source '{source}'. Allowed: {cls.VALID_SOURCES}.",
            )

        # 3. Verify Agent Action Exists & Was Executed
        action = db.query(AgentAction).filter(AgentAction.id == agent_action_id).first()
        if not action:
            return ToolResult(
                success=False,
                tool_name="observe_outcome",
                error=f"Agent action #{agent_action_id} not found.",
            )

        if action.action_type != "execute":
            return ToolResult(
                success=False,
                tool_name="observe_outcome",
                error=f"Cannot observe outcome for non-executed action (type='{action.action_type}').",
            )

        # 4. Verify Associated Case & Payment
        case = db.query(RecoveryCase).filter(RecoveryCase.id == action.recovery_case_id).first()
        if not case:
            return ToolResult(
                success=False,
                tool_name="observe_outcome",
                error=f"Recovery case #{action.recovery_case_id} not found.",
            )

        payment = db.query(Payment).filter(Payment.id == case.payment_id).first()
        if not payment:
            return ToolResult(
                success=False,
                tool_name="observe_outcome",
                error=f"Payment #{case.payment_id} not found.",
            )

        # 5. Verify Pending RecoveryOutcome Record Exists
        rec_outcome = db.query(RecoveryOutcome).filter(RecoveryOutcome.agent_action_id == action.id).first()
        if not rec_outcome:
            return ToolResult(
                success=False,
                tool_name="observe_outcome",
                error=f"No pending outcome record found for agent action #{agent_action_id}.",
            )

        # 6. Verify Outcome Has Not Already Been Finalized (No Duplicate Observation)
        if rec_outcome.outcome_status == "observed":
            return ToolResult(
                success=False,
                tool_name="observe_outcome",
                error=f"Outcome for action #{agent_action_id} has already been finalized.",
            )

        # 7. Verify Amount Bounds (0 <= amount_recovered <= payment.amount)
        amt = float(amount_recovered)
        if amt < 0.0:
            return ToolResult(
                success=False,
                tool_name="observe_outcome",
                error=f"Recovered amount ({amt}) cannot be negative.",
            )

        if amt > payment.amount:
            return ToolResult(
                success=False,
                tool_name="observe_outcome",
                error=f"Recovered amount (₹{amt:,.2f}) cannot exceed original payment amount (₹{payment.amount:,.2f}).",
            )

        # 8. Finalize Outcome Record
        is_successful = (norm_outcome == "recovered" and amt > 0.0)
        now_dt = _utcnow()
        rec_outcome.outcome_status = "observed"
        rec_outcome.successful = is_successful
        rec_outcome.amount_recovered = amt if is_successful else 0.0
        rec_outcome.failure_reason = failure_reason if not is_successful else None
        rec_outcome.outcome_source = norm_source
        rec_outcome.outcome_observed_at = now_dt

        # Compute recovery time seconds if action_executed_at is present
        if rec_outcome.action_executed_at:
            t1 = _to_naive_utc(rec_outcome.action_executed_at)
            t2 = _to_naive_utc(rec_outcome.outcome_observed_at)
            if t1 and t2:
                rec_outcome.recovery_time_seconds = max(0.1, round((t2 - t1).total_seconds(), 2))

        # 9. Update Case Status
        if is_successful:
            case.status = "RECOVERED"
        elif norm_outcome == "escalated":
            case.status = "ESCALATED"
        elif norm_outcome == "stopped":
            case.status = "STOPPED"
        else:
            case.status = "FAILED"

        case.updated_at = now_dt

        # 10. Create Audit Trail Entry for Outcome Observation
        audit_log = AgentAction(
            recovery_case_id=case.id,
            action_type="observe_outcome",
            tool_name="observe_outcome",
            input_json=json.dumps({
                "agent_action_id": agent_action_id,
                "outcome": norm_outcome,
                "amount_recovered": amt,
                "source": norm_source,
            }),
            output_json=json.dumps({
                "outcome_status": "observed",
                "successful": is_successful,
                "amount_recovered": rec_outcome.amount_recovered,
            }),
            reasoning_summary=f"Outcome observed: {norm_outcome.upper()} (₹{rec_outcome.amount_recovered:,.2f}) via {norm_source}",
            policy_decision="APPROVED",
            policy_reason="System outcome observed successfully.",
            created_at=now_dt,
        )
        db.add(audit_log)
        db.commit()

        return ToolResult(
            success=True,
            tool_name="observe_outcome",
            data={
                "outcome_status": "observed",
                "successful": is_successful,
                "amount_recovered": rec_outcome.amount_recovered,
                "case_status": case.status,
                "outcome_source": norm_source,
                "recovery_outcome_id": rec_outcome.id,
            },
        )
