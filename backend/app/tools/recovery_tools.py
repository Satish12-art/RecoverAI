"""Policy-gated write tools for the RecoverAI Agent.

Executes bounded simulated recovery actions (retry, message, escalation)
strictly gated by the deterministic PolicyEngine.
All actions log sanitized audit records to agent_actions and initialize pending recovery outcomes.
"""

import json
from datetime import datetime, timezone
from typing import Any, Optional
from sqlalchemy.orm import Session

from app.models.models import (
    Customer,
    Payment,
    RecoveryCase,
    AgentAction,
    RecoveryOutcome,
)
from app.policies.message_templates import (
    TemplateId,
    MessagePersonalizationContract,
    MessageTemplateEngine,
)
from app.policies.policy_engine import (
    PolicyEngine,
    PolicyDecision,
)
from app.services.recovery_scorer import RecoveryScorer
from app.tools.tool_types import ToolResult


def _utcnow():
    return datetime.now(timezone.utc)


def _sanitize_dict(data: dict) -> dict:
    """Sanitize sensitive keys before logging to audit trail."""
    sanitized = {}
    sensitive_keys = {"cvv", "pin", "password", "otp", "secret", "card_number", "credentials"}
    for k, v in data.items():
        if any(s in k.lower() for s in sensitive_keys):
            sanitized[k] = "[REDACTED]"
        elif isinstance(v, dict):
            sanitized[k] = _sanitize_dict(v)
        else:
            sanitized[k] = v
    return sanitized


class RecoveryTools:
    """Namespace for policy-gated recovery actions."""

    @staticmethod
    def _get_or_create_case(db: Session, payment: Payment) -> RecoveryCase:
        """Fetch existing recovery case for payment or create a new one."""
        case = db.query(RecoveryCase).filter(RecoveryCase.payment_id == payment.id).first()
        if not case:
            case = RecoveryCase(
                payment_id=payment.id,
                customer_id=payment.customer_id,
                amount_at_risk=payment.amount,
                status="OPEN",
                retry_count=0,
                created_at=_utcnow(),
                updated_at=_utcnow(),
            )
            db.add(case)
            db.commit()
            db.refresh(case)
        return case

    @classmethod
    def request_payment_retry(
        cls,
        db: Session,
        case_id: int,
        idempotency_key: Optional[str] = None,
    ) -> ToolResult:
        """Execute a simulated payment retry if and only if approved by PolicyEngine."""
        case = db.query(RecoveryCase).filter(RecoveryCase.id == case_id).first()
        if not case:
            return ToolResult(
                success=False,
                tool_name="request_payment_retry",
                error=f"Recovery case #{case_id} not found.",
            )

        payment = db.query(Payment).filter(Payment.id == case.payment_id).first()
        customer = db.query(Customer).filter(Customer.id == case.customer_id).first()

        # Idempotency Check: Check if an identical retry action was already executed for this attempt
        attempt_num = case.retry_count + 1
        idem_key = idempotency_key or f"case_{case_id}_retry_{attempt_num}"

        existing_action = (
            db.query(AgentAction)
            .filter(
                AgentAction.recovery_case_id == case.id,
                AgentAction.tool_name == "request_payment_retry",
                AgentAction.reasoning_summary.like(f"%{idem_key}%"),
            )
            .first()
        )
        if existing_action:
            return ToolResult(
                success=True,
                tool_name="request_payment_retry",
                data={
                    "idempotent_replay": True,
                    "action_executed": True,
                    "outcome_status": "pending",
                    "simulated": True,
                    "agent_action_id": existing_action.id,
                },
            )

        # 1. Deterministic Recovery Score
        score = RecoveryScorer.calculate_score(
            payment=payment,
            customer=customer,
            previous_recovery_attempts=case.retry_count,
        )
        case.recovery_probability = score.recovery_probability
        case.scorer_confidence = score.scorer_confidence
        case.expected_recovery_value = score.expected_recovery_value

        # 2. Evaluate Policy
        policy_res = PolicyEngine.evaluate(
            payment=payment,
            customer=customer,
            proposed_action="retry",
            recovery_probability=score.recovery_probability,
            scorer_confidence=score.scorer_confidence,
            previous_recovery_attempts=case.retry_count,
        )

        # Log policy check trace to AgentAction
        action_log = AgentAction(
            recovery_case_id=case.id,
            action_type="execute" if policy_res.decision == PolicyDecision.APPROVE else "policy_blocked",
            tool_name="request_payment_retry",
            input_json=json.dumps(_sanitize_dict({"case_id": case_id, "idempotency_key": idem_key})),
            output_json=json.dumps({
                "decision": policy_res.decision.value,
                "reason_codes": [r.value for r in policy_res.reason_codes],
                "explanation": policy_res.explanation,
            }),
            reasoning_summary=f"Attempt {attempt_num} [{idem_key}]: {policy_res.explanation}",
            policy_decision=policy_res.decision.value,
            policy_reason=", ".join([r.value for r in policy_res.reason_codes]),
            created_at=_utcnow(),
        )
        db.add(action_log)
        db.commit()
        db.refresh(action_log)

        # 3. Handle Policy Decision
        if policy_res.decision != PolicyDecision.APPROVE:
            if policy_res.decision == PolicyDecision.STOP:
                case.status = "STOPPED"
            else:
                case.status = "ESCALATED"
                case.escalation_reason = policy_res.explanation

            case.updated_at = _utcnow()
            db.commit()

            return ToolResult(
                success=False,
                tool_name="request_payment_retry",
                policy=policy_res,
                error=f"Action blocked by policy: {policy_res.explanation}",
            )

        # 4. Policy APPROVED -> Execute Simulation Action & Create Pending Outcome
        case.retry_count = attempt_num
        case.actual_action = "retry"
        case.status = "RECOVERING"
        case.updated_at = _utcnow()

        outcome = RecoveryOutcome(
            recovery_case_id=case.id,
            agent_action_id=action_log.id,
            action="retry",
            outcome_status="pending",
            successful=None,
            amount_recovered=0.0,
            outcome_source="simulation",
            simulated=True,
            action_executed_at=_utcnow(),
            outcome_observed_at=None,
            created_at=_utcnow(),
        )
        db.add(outcome)
        db.commit()
        db.refresh(outcome)

        return ToolResult(
            success=True,
            tool_name="request_payment_retry",
            data={
                "action_executed": True,
                "outcome_status": "pending",
                "simulated": True,
                "agent_action_id": action_log.id,
                "recovery_outcome_id": outcome.id,
                "attempt_number": attempt_num,
            },
            policy=policy_res,
        )

    @classmethod
    def send_recovery_message(
        cls,
        db: Session,
        case_id: int,
        template_id: str,
        personalized_note: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> ToolResult:
        """Send an approved recovery message if and only if approved by PolicyEngine."""
        case = db.query(RecoveryCase).filter(RecoveryCase.id == case_id).first()
        if not case:
            return ToolResult(
                success=False,
                tool_name="send_recovery_message",
                error=f"Recovery case #{case_id} not found.",
            )

        payment = db.query(Payment).filter(Payment.id == case.payment_id).first()
        customer = db.query(Customer).filter(Customer.id == case.customer_id).first()

        try:
            enum_tmpl_id = TemplateId(template_id)
        except ValueError:
            return ToolResult(
                success=False,
                tool_name="send_recovery_message",
                error=f"Invalid template_id '{template_id}'. Allowed: {[t.value for t in TemplateId]}.",
            )

        contract = MessagePersonalizationContract(
            template_id=enum_tmpl_id,
            customer_name=customer.name if customer else "Customer",
            amount=f"{payment.amount:,.2f}",
            currency=payment.currency,
            payment_reference=payment.external_payment_id,
            personalized_note=personalized_note or "",
        )
        try:
            rendered = MessageTemplateEngine.render(contract)
        except ValueError as e:
            return ToolResult(
                success=False,
                tool_name="send_recovery_message",
                error=f"Message validation error: {str(e)}",
            )

        idem_key = idempotency_key or f"case_{case_id}_msg_{template_id}"
        existing_action = (
            db.query(AgentAction)
            .filter(
                AgentAction.recovery_case_id == case.id,
                AgentAction.tool_name == "send_recovery_message",
                AgentAction.reasoning_summary.like(f"%{idem_key}%"),
            )
            .first()
        )
        if existing_action:
            return ToolResult(
                success=True,
                tool_name="send_recovery_message",
                data={
                    "idempotent_replay": True,
                    "action_executed": True,
                    "outcome_status": "pending",
                    "simulated": True,
                    "agent_action_id": existing_action.id,
                },
            )

        score = RecoveryScorer.calculate_score(
            payment=payment,
            customer=customer,
            previous_recovery_attempts=case.retry_count,
        )
        case.recovery_probability = score.recovery_probability
        case.scorer_confidence = score.scorer_confidence
        case.expected_recovery_value = score.expected_recovery_value

        policy_res = PolicyEngine.evaluate(
            payment=payment,
            customer=customer,
            proposed_action="message",
            recovery_probability=score.recovery_probability,
            scorer_confidence=score.scorer_confidence,
            previous_recovery_attempts=case.retry_count,
        )

        action_log = AgentAction(
            recovery_case_id=case.id,
            action_type="execute" if policy_res.decision == PolicyDecision.APPROVE else "policy_blocked",
            tool_name="send_recovery_message",
            input_json=json.dumps(_sanitize_dict({
                "case_id": case_id,
                "template_id": template_id,
                "personalized_note": personalized_note,
                "idempotency_key": idem_key,
            })),
            output_json=json.dumps({
                "decision": policy_res.decision.value,
                "reason_codes": [r.value for r in policy_res.reason_codes],
                "explanation": policy_res.explanation,
            }),
            reasoning_summary=f"Message [{idem_key}]: {policy_res.explanation}",
            policy_decision=policy_res.decision.value,
            policy_reason=", ".join([r.value for r in policy_res.reason_codes]),
            created_at=_utcnow(),
        )
        db.add(action_log)
        db.commit()
        db.refresh(action_log)

        if policy_res.decision != PolicyDecision.APPROVE:
            if policy_res.decision == PolicyDecision.STOP:
                case.status = "STOPPED"
            else:
                case.status = "ESCALATED"
                case.escalation_reason = policy_res.explanation

            case.updated_at = _utcnow()
            db.commit()

            return ToolResult(
                success=False,
                tool_name="send_recovery_message",
                policy=policy_res,
                error=f"Action blocked by policy: {policy_res.explanation}",
            )

        case.actual_action = "message"
        case.status = "RECOVERING"
        case.updated_at = _utcnow()

        outcome = RecoveryOutcome(
            recovery_case_id=case.id,
            agent_action_id=action_log.id,
            action="message",
            outcome_status="pending",
            successful=None,
            amount_recovered=0.0,
            outcome_source="simulation",
            simulated=True,
            action_executed_at=_utcnow(),
            outcome_observed_at=None,
            created_at=_utcnow(),
        )
        db.add(outcome)
        db.commit()
        db.refresh(outcome)

        return ToolResult(
            success=True,
            tool_name="send_recovery_message",
            data={
                "action_executed": True,
                "message_subject": rendered.subject,
                "message_body": rendered.body,
                "outcome_status": "pending",
                "simulated": True,
                "agent_action_id": action_log.id,
                "recovery_outcome_id": outcome.id,
            },
            policy=policy_res,
        )

    @classmethod
    def escalate_to_human(
        cls,
        db: Session,
        case_id: int,
        reason: str,
    ) -> ToolResult:
        """Escalate case to human review."""
        case = db.query(RecoveryCase).filter(RecoveryCase.id == case_id).first()
        if not case:
            return ToolResult(
                success=False,
                tool_name="escalate_to_human",
                error=f"Recovery case #{case_id} not found.",
            )

        # Idempotency Check: Check if an identical escalate action was already executed for this case
        existing_action = (
            db.query(AgentAction)
            .filter(
                AgentAction.recovery_case_id == case.id,
                AgentAction.tool_name == "escalate_to_human",
            )
            .first()
        )
        if existing_action:
            return ToolResult(
                success=True,
                tool_name="escalate_to_human",
                data={
                    "idempotent_replay": True,
                    "escalated": True,
                    "case_id": case.id,
                    "reason": reason,
                    "agent_action_id": existing_action.id,
                },
            )

        case.status = "ESCALATED"
        case.escalation_reason = reason
        case.actual_action = "escalate"
        case.updated_at = _utcnow()

        action_log = AgentAction(
            recovery_case_id=case.id,
            action_type="escalate",
            tool_name="escalate_to_human",
            input_json=json.dumps(_sanitize_dict({"case_id": case_id, "reason": reason})),
            output_json=json.dumps({"escalated": True, "reason": reason}),
            reasoning_summary=f"Human escalation: {reason}",
            policy_decision="APPROVED",
            policy_reason="Explicit human escalation approved.",
            created_at=_utcnow(),
        )
        db.add(action_log)
        db.commit()
        db.refresh(action_log)

        return ToolResult(
            success=True,
            tool_name="escalate_to_human",
            data={
                "escalated": True,
                "case_id": case.id,
                "reason": reason,
                "agent_action_id": action_log.id,
            },
        )
