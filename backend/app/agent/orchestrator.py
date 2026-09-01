"""Bounded Orchestrator for the RecoverAI Recovery Agent."""

import time
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session

from app.agent.llm_client import LLMClient, get_llm_client
from app.agent.schemas import (
    AgentContext,
    AgentRunResult,
    CustomerContext,
    PaymentContext,
    ScoringContext,
    LLMStructuredOutput,
)
from app.agent.state import (
    MAX_AGENT_STEPS,
    MAX_LLM_CALLS,
    AGENT_TIMEOUT_SECONDS,
    AgentStep,
    TerminalState,
)
from app.agent.trace import AgentTraceCollector
from app.models.models import Customer, Payment, RecoveryCase
from app.policies.policy_engine import PolicyDecision, PolicyEngine
from app.services.eligibility import EligibilityDecision, EligibilityGate
from app.services.recovery_scorer import RecoveryScorer
from app.tools.read_tools import ReadTools
from app.tools.recovery_tools import RecoveryTools


class AgentOrchestrator:
    """Orchestrates the bounded state machine for payment recovery."""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm_client = llm_client or get_llm_client()

    def run(self, db: Session, case_id: int) -> AgentRunResult:
        start_time = time.time()
        trace_collector = AgentTraceCollector()
        step_count = 0
        llm_calls_made = 0

        def _check_bounds() -> Optional[AgentRunResult]:
            nonlocal step_count, llm_calls_made
            elapsed = time.time() - start_time
            if elapsed > AGENT_TIMEOUT_SECONDS:
                trace_collector.log_step(
                    AgentStep.TERMINAL,
                    "timeout_exceeded",
                    {"elapsed_seconds": round(elapsed, 2)},
                )
                return AgentRunResult(
                    case_id=case_id,
                    final_state=TerminalState.ESCALATED,
                    error=f"Agent execution timed out after {elapsed:.2f}s",
                    trace=trace_collector.get_traces(),
                    llm_calls_made=llm_calls_made,
                    total_steps=step_count,
                    execution_time_seconds=round(elapsed, 3),
                )
            if step_count >= MAX_AGENT_STEPS:
                trace_collector.log_step(
                    AgentStep.TERMINAL,
                    "max_steps_exceeded",
                    {"steps": step_count},
                )
                return AgentRunResult(
                    case_id=case_id,
                    final_state=TerminalState.ESCALATED,
                    error=f"Agent exceeded max step limit of {MAX_AGENT_STEPS}",
                    trace=trace_collector.get_traces(),
                    llm_calls_made=llm_calls_made,
                    total_steps=step_count,
                    execution_time_seconds=round(elapsed, 3),
                )
            return None

        # ── Step 1: DETECTED ──
        step_count += 1
        trace_collector.log_step(AgentStep.DETECTED, "started", {"case_id": case_id})

        case = db.query(RecoveryCase).filter(RecoveryCase.id == case_id).first()
        if not case:
            trace_collector.log_step(AgentStep.TERMINAL, "case_not_found", {"case_id": case_id})
            return AgentRunResult(
                case_id=case_id,
                final_state=TerminalState.ERROR,
                error=f"Recovery case #{case_id} not found.",
                trace=trace_collector.get_traces(),
                total_steps=step_count,
                execution_time_seconds=round(time.time() - start_time, 3),
            )

        payment = db.query(Payment).filter(Payment.id == case.payment_id).first()
        customer = db.query(Customer).filter(Customer.id == case.customer_id).first()

        if not payment or not customer:
            trace_collector.log_step(AgentStep.TERMINAL, "data_missing", {"payment_exists": bool(payment), "customer_exists": bool(customer)})
            return AgentRunResult(
                case_id=case_id,
                final_state=TerminalState.ERROR,
                error="Associated payment or customer record missing.",
                trace=trace_collector.get_traces(),
                total_steps=step_count,
                execution_time_seconds=round(time.time() - start_time, 3),
            )

        # ── Step 2: ELIGIBILITY_CHECK ──
        step_count += 1
        eligibility = EligibilityGate.evaluate(payment=payment, customer=customer)
        reason_val = eligibility.reason.value if eligibility.reason else "UNKNOWN"
        trace_collector.log_step(
            AgentStep.ELIGIBILITY_CHECK,
            eligibility.decision.value,
            {"reason": reason_val, "message": eligibility.message},
        )

        if eligibility.decision != EligibilityDecision.PROCEED:
            # Deterministic gate stopped it -> DO NOT CALL LLM (Cost & Safety optimization)
            case.status = "STOPPED"
            case.updated_at = datetime.now(timezone.utc)
            db.commit()

            return AgentRunResult(
                case_id=case.id,
                final_state=TerminalState.STOPPED,
                recommended_action="stop",
                policy_decision="STOP",
                policy_reason_codes=[reason_val],
                action_executed=False,
                trace=trace_collector.get_traces(),
                llm_calls_made=0,
                total_steps=step_count,
                execution_time_seconds=round(time.time() - start_time, 3),
            )

        # ── Step 3: CONTEXT_LOADING ──
        step_count += 1
        hist_res = ReadTools.get_customer_history(db, customer.id)
        hist_data = hist_res.data or {}
        trace_collector.log_step(AgentStep.CONTEXT_LOADING, "completed")

        # ── Step 4: SCORING (Deterministic Single Source of Truth) ──
        step_count += 1
        score = RecoveryScorer.calculate_score(
            payment=payment,
            customer=customer,
            previous_recovery_attempts=case.retry_count,
        )
        case.recovery_probability = score.recovery_probability
        case.scorer_confidence = score.scorer_confidence
        case.expected_recovery_value = score.expected_recovery_value
        db.commit()

        trace_collector.log_step(
            AgentStep.SCORING,
            "calculated",
            {
                "recovery_probability": score.recovery_probability,
                "scorer_confidence": score.scorer_confidence,
                "expected_recovery_value": score.expected_recovery_value,
            },
        )

        # Construct strictly production-facing AgentContext
        agent_context = AgentContext(
            payment=PaymentContext(
                id=payment.id,
                amount=payment.amount,
                currency=payment.currency,
                status=payment.status,
                failure_code=payment.failure_code,
                failure_reason=payment.failure_reason,
                payment_method=payment.payment_method,
                risk_flagged=payment.risk_flagged,
            ),
            customer=CustomerContext(
                id=customer.id,
                name=customer.name,
                customer_tenure_days=customer.customer_tenure_days,
                total_orders=customer.total_orders,
                successful_payments=customer.successful_payments,
                failed_payments=customer.failed_payments,
                historical_success_rate=hist_data.get("historical_success_rate", 0.0),
                average_order_value=customer.average_order_value,
                chargeback_count=customer.chargeback_count,
                refund_count=customer.refund_count,
                opted_out=customer.opted_out,
            ),
            scoring=ScoringContext(
                recovery_probability=score.recovery_probability,
                scorer_confidence=score.scorer_confidence,
                expected_recovery_value=score.expected_recovery_value,
                previous_recovery_attempts=case.retry_count,
                contributing_factors=[f.model_dump() for f in score.factors],
            ),
        )

        # Check bounds before calling LLM
        bound_err = _check_bounds()
        if bound_err:
            return bound_err

        # ── Step 5: DIAGNOSING & DECISION_PENDING (LLM Decision Support) ──
        step_count += 1
        llm_decision: Optional[LLMStructuredOutput] = None

        if llm_calls_made >= MAX_LLM_CALLS:
            trace_collector.log_step(AgentStep.TERMINAL, "max_llm_calls_exceeded", {"calls": llm_calls_made})
            return AgentRunResult(
                case_id=case.id,
                final_state=TerminalState.ESCALATED,
                error=f"Exceeded max LLM calls ({MAX_LLM_CALLS})",
                trace=trace_collector.get_traces(),
                llm_calls_made=llm_calls_made,
                total_steps=step_count,
                execution_time_seconds=round(time.time() - start_time, 3),
            )

        try:
            llm_calls_made += 1
            llm_decision = self.llm_client.generate_structured_decision(agent_context)
            trace_collector.log_step(
                AgentStep.DIAGNOSING,
                "completed",
                {"category": llm_decision.diagnosis.failure_category, "summary": llm_decision.diagnosis.summary},
            )
            step_count += 1
            trace_collector.log_step(
                AgentStep.DECISION_PENDING,
                "recommended",
                {"action": llm_decision.recommendation.action.value, "reason": llm_decision.recommendation.reason},
            )
        except Exception as e:
            # LLM failure (malformed JSON, timeout, error) -> Safely Escalate, NEVER execute unverified action
            trace_collector.log_step(AgentStep.DIAGNOSING, "llm_error", {"error": str(e)})
            case.status = "ESCALATED"
            case.escalation_reason = f"LLM decision support error: {str(e)}"
            db.commit()

            return AgentRunResult(
                case_id=case.id,
                final_state=TerminalState.ESCALATED,
                error=f"LLM failure: {str(e)}",
                trace=trace_collector.get_traces(),
                llm_calls_made=llm_calls_made,
                total_steps=step_count,
                execution_time_seconds=round(time.time() - start_time, 3),
            )

        case.recommended_action = llm_decision.recommendation.action.value

        # ── Step 6: POLICY_CHECK (Authoritative Deterministic Gate) ──
        step_count += 1
        policy_res = PolicyEngine.evaluate(
            payment=payment,
            customer=customer,
            proposed_action=llm_decision.recommendation.action.value,
            recovery_probability=score.recovery_probability,
            scorer_confidence=score.scorer_confidence,
            previous_recovery_attempts=case.retry_count,
        )

        trace_collector.log_step(
            AgentStep.POLICY_CHECK,
            policy_res.decision.value,
            {
                "reason_codes": [r.value for r in policy_res.reason_codes],
                "explanation": policy_res.explanation,
            },
        )

        # ── Step 7: ACTION_EXECUTION (Bounded Tool Execution) ──
        step_count += 1
        executed = False
        action_id: Optional[int] = None
        outcome_id: Optional[int] = None
        final_terminal_state: TerminalState

        if policy_res.decision != PolicyDecision.APPROVE:
            # Policy blocked action -> DO NOT call write tool
            trace_collector.log_step(
                AgentStep.ACTION_EXECUTION,
                "blocked_by_policy",
                {"decision": policy_res.decision.value, "reason": policy_res.explanation},
            )
            if policy_res.decision == PolicyDecision.STOP:
                final_terminal_state = TerminalState.STOPPED
                case.status = "STOPPED"
            else:
                final_terminal_state = TerminalState.ESCALATED
                case.status = "ESCALATED"
                case.escalation_reason = policy_res.explanation

            db.commit()
        else:
            # Policy APPROVED -> Call the corresponding bounded Phase 5 tool
            tool_action = llm_decision.recommendation.action.value

            if tool_action == "retry":
                tool_res = RecoveryTools.request_payment_retry(db, case_id=case.id)
            elif tool_action == "message":
                tmpl = "PAYMENT_UPDATE" if payment.failure_code in ("expired_card", "invalid_card") else "PAYMENT_RETRY"
                tool_res = RecoveryTools.send_recovery_message(
                    db,
                    case_id=case.id,
                    template_id=tmpl,
                    personalized_note=llm_decision.message_personalization,
                )
            elif tool_action == "escalate":
                tool_res = RecoveryTools.escalate_to_human(
                    db,
                    case_id=case.id,
                    reason=llm_decision.recommendation.reason,
                )
            else:
                tool_res = None

            if tool_res and tool_res.success:
                executed = True
                action_id = tool_res.data.get("agent_action_id")
                outcome_id = tool_res.data.get("recovery_outcome_id")
                final_terminal_state = TerminalState.RECOVERING if tool_action in ("retry", "message") else TerminalState.ESCALATED
                trace_collector.log_step(
                    AgentStep.ACTION_EXECUTION,
                    "executed",
                    {"tool_name": tool_res.tool_name, "agent_action_id": action_id},
                )
            else:
                final_terminal_state = TerminalState.ESCALATED
                trace_collector.log_step(
                    AgentStep.ACTION_EXECUTION,
                    "tool_failed",
                    {"error": tool_res.error if tool_res else "Unknown action"},
                )

        step_count += 1
        trace_collector.log_step(AgentStep.TERMINAL, final_terminal_state.value)

        elapsed = time.time() - start_time
        return AgentRunResult(
            case_id=case.id,
            final_state=final_terminal_state,
            recommended_action=llm_decision.recommendation.action.value,
            policy_decision=policy_res.decision.value,
            policy_reason_codes=[r.value for r in policy_res.reason_codes],
            recovery_probability=score.recovery_probability,
            scorer_confidence=score.scorer_confidence,
            expected_recovery_value=score.expected_recovery_value,
            action_executed=executed,
            agent_action_id=action_id,
            recovery_outcome_id=outcome_id,
            trace=trace_collector.get_traces(),
            llm_calls_made=llm_calls_made,
            total_steps=step_count,
            execution_time_seconds=round(elapsed, 3),
        )
