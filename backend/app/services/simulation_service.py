"""Simulation Runner and Batch Lifecycle Execution Service for RecoverAI."""

import random
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Optional
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.llm_client import MockLLMClient, RealLLMClient
from app.agent.orchestrator import AgentOrchestrator
from app.models.models import Customer, Payment, RecoveryCase, RecoveryOutcome, AgentAction
from app.services.revenue_metrics import RevenueMetricsService, RevenueMetricsSummary
from app.services.simulation_engine import SimulationOutcomeEngine
from app.tools.outcome_tools import OutcomeObserver


class CaseSimulationTrace(BaseModel):
    payment_id: int
    case_id: int
    amount: float
    currency: str
    failure_code: Optional[str] = None
    eligibility_decision: str
    recovery_probability: Optional[float] = None
    scorer_confidence: Optional[float] = None
    expected_recovery_value: Optional[float] = None
    llm_recommendation: Optional[str] = None
    policy_decision: Optional[str] = None
    policy_reason_codes: list[str] = Field(default_factory=list)
    tool_executed: Optional[str] = None
    agent_action_id: Optional[int] = None
    outcome: Optional[str] = None
    amount_recovered: float = 0.0
    final_state: str
    error: Optional[str] = None


class SimulationResult(BaseModel):
    simulation_id: str
    seed: int
    mode: str
    started_at: str
    completed_at: str
    duration_seconds: float
    payments_processed: int
    eligible_count: int
    stopped_count: int
    escalated_count: int
    actions_executed: int
    outcomes_observed: int
    recovered_cases: int
    failed_cases: int
    error_cases: int
    # Explicit Batch-specific metrics (this run only)
    batch_revenue_recovered: float = 0.0
    batch_recovery_rate: float = 0.0
    batch_gross_revenue_at_risk: float = 0.0
    # Explicit Global database cumulative metrics
    cumulative_revenue_recovered: float = 0.0
    gross_revenue_at_risk: float = 0.0
    potentially_recoverable_revenue: float = 0.0
    expected_recovery_value: float = 0.0
    revenue_recovered: float = 0.0
    recovery_rate: float = 0.0
    ai_recommendations: dict[str, int] = Field(default_factory=dict)
    policy_decisions: dict[str, int] = Field(default_factory=dict)
    case_traces: list[CaseSimulationTrace] = Field(default_factory=list)


class SimulationRunner:
    """Batch simulation runner executing the complete end-to-end lifecycle."""

    @classmethod
    def run(
        cls,
        db: Session,
        seed: int = 42,
        limit: Optional[int] = 100,
        all_payments: bool = False,
        mode: str = "mock",
        fast_mode: bool = True,
        verbose: bool = False,
    ) -> SimulationResult:
        """Run batch simulation on failed payments deterministically."""
        sim_id = f"sim_{uuid.uuid4().hex[:10]}"
        start_time = time.time()
        started_at = datetime.now(timezone.utc).isoformat()
        rng = random.Random(seed)

        # 1. Select Unprocessed / Unresolved Failed Payments Deterministically
        # Do not re-process payments that already have an active or resolved recovery lifecycle
        processed_payment_ids = (
            select(RecoveryCase.payment_id)
            .filter(RecoveryCase.status.in_(["RECOVERED", "FAILED", "ESCALATED", "STOPPED", "RECOVERING"]))
        )
        query = (
            db.query(Payment)
            .filter(
                Payment.status == "failed",
                Payment.id.not_in(processed_payment_ids),
            )
            .order_by(Payment.id.asc())
        )
        if not all_payments and limit is not None:
            failed_payments = query.limit(limit).all()
        else:
            failed_payments = query.all()

        llm_client = MockLLMClient() if mode.lower() == "mock" else RealLLMClient()
        orchestrator = AgentOrchestrator(llm_client=llm_client)

        case_traces: list[CaseSimulationTrace] = []
        eligible_cnt = 0
        stopped_cnt = 0
        escalated_cnt = 0
        actions_exec_cnt = 0
        outcomes_obs_cnt = 0
        recovered_cnt = 0
        failed_cnt = 0
        error_cnt = 0

        ai_recs: dict[str, int] = {"retry": 0, "message": 0, "escalate": 0, "stop": 0}
        policy_decs: dict[str, int] = {"APPROVE": 0, "ESCALATE": 0, "STOP": 0, "REJECT": 0}

        # 2. Iterate through payments with Error Isolation
        for pmt in failed_payments:
            try:
                # Ensure RecoveryCase exists
                case = db.query(RecoveryCase).filter(RecoveryCase.payment_id == pmt.id).first()
                if not case:
                    case = RecoveryCase(
                        payment_id=pmt.id,
                        customer_id=pmt.customer_id,
                        amount_at_risk=pmt.amount,
                        status="OPEN",
                        retry_count=0,
                        created_at=datetime.now(timezone.utc),
                        updated_at=datetime.now(timezone.utc),
                    )
                    db.add(case)
                    db.commit()
                    db.refresh(case)

                # Run Bounded AI Agent
                run_res = orchestrator.run(db, case_id=case.id)

                if run_res.recommended_action:
                    ai_recs[run_res.recommended_action] = ai_recs.get(run_res.recommended_action, 0) + 1

                if run_res.policy_decision:
                    policy_decs[run_res.policy_decision] = policy_decs.get(run_res.policy_decision, 0) + 1

                # Track counts
                if run_res.final_state.value == "STOPPED":
                    stopped_cnt += 1
                elif run_res.final_state.value == "ESCALATED":
                    escalated_cnt += 1
                else:
                    eligible_cnt += 1

                observed_outcome_str: Optional[str] = None
                amt_recovered = 0.0

                # If an action was approved and executed, simulate and observe outcome
                if run_res.action_executed and run_res.agent_action_id is not None:
                    actions_exec_cnt += 1

                    # Generate simulated outcome from deterministic simulation engine
                    sim_outcome = SimulationOutcomeEngine.generate_outcome(
                        action_type=run_res.recommended_action or "retry",
                        payment_amount=pmt.amount,
                        failure_code=pmt.failure_code,
                        recovery_probability=run_res.recovery_probability or 0.50,
                        rng=rng,
                    )

                    # Observe outcome via authoritative OutcomeObserver
                    obs_res = OutcomeObserver.observe_outcome(
                        db=db,
                        agent_action_id=run_res.agent_action_id,
                        outcome=sim_outcome.outcome,
                        amount_recovered=sim_outcome.amount_recovered,
                        source="simulation",
                        failure_reason=sim_outcome.failure_reason,
                    )

                    if obs_res.success:
                        outcomes_obs_cnt += 1
                        observed_outcome_str = sim_outcome.outcome
                        amt_recovered = sim_outcome.amount_recovered
                        if sim_outcome.outcome == "recovered" and amt_recovered > 0:
                            recovered_cnt += 1
                        else:
                            failed_cnt += 1

                trace = CaseSimulationTrace(
                    payment_id=pmt.id,
                    case_id=case.id,
                    amount=pmt.amount,
                    currency=pmt.currency,
                    failure_code=pmt.failure_code,
                    eligibility_decision="PROCEED" if run_res.final_state.value not in ("STOPPED", "ERROR") else "STOP",
                    recovery_probability=run_res.recovery_probability,
                    scorer_confidence=run_res.scorer_confidence,
                    expected_recovery_value=run_res.expected_recovery_value,
                    llm_recommendation=run_res.recommended_action,
                    policy_decision=run_res.policy_decision,
                    policy_reason_codes=run_res.policy_reason_codes,
                    tool_executed=f"request_payment_{run_res.recommended_action}" if run_res.action_executed else None,
                    agent_action_id=run_res.agent_action_id,
                    outcome=observed_outcome_str,
                    amount_recovered=amt_recovered,
                    final_state=case.status,
                    error=run_res.error,
                )
                case_traces.append(trace)

            except Exception as e:
                error_cnt += 1
                case_traces.append(
                    CaseSimulationTrace(
                        payment_id=pmt.id,
                        case_id=pmt.id,
                        amount=pmt.amount,
                        currency=pmt.currency,
                        failure_code=pmt.failure_code,
                        eligibility_decision="ERROR",
                        final_state="ERROR",
                        error=str(e),
                    )
                )

        # 3. Calculate Batch Metrics (derived strictly from this run)
        batch_revenue = round(sum(t.amount_recovered for t in case_traces), 2)
        batch_gross_risk = round(sum(t.amount for t in case_traces), 2)
        batch_rate = round((batch_revenue / batch_gross_risk * 100), 2) if batch_gross_risk > 0 else 0.0

        # 4. Calculate Final Global Three-Tier Revenue Metrics (across entire DB)
        all_payments_in_db = db.query(Payment).all()
        all_customers = db.query(Customer).all()
        cust_map = {c.id: c for c in all_customers}
        all_outcomes = db.query(RecoveryOutcome).all()

        metrics = RevenueMetricsService.calculate_metrics(
            payments=all_payments_in_db,
            customer_map=cust_map,
            observed_outcomes=all_outcomes,
        )

        completed_at = datetime.now(timezone.utc).isoformat()
        duration = round(time.time() - start_time, 3)

        return SimulationResult(
            simulation_id=sim_id,
            seed=seed,
            mode=mode,
            started_at=started_at,
            completed_at=completed_at,
            duration_seconds=duration,
            payments_processed=len(failed_payments),
            eligible_count=eligible_cnt,
            stopped_count=stopped_cnt,
            escalated_count=escalated_cnt,
            actions_executed=actions_exec_cnt,
            outcomes_observed=outcomes_obs_cnt,
            recovered_cases=recovered_cnt,
            failed_cases=failed_cnt,
            error_cases=error_cnt,
            batch_revenue_recovered=batch_revenue,
            batch_recovery_rate=batch_rate,
            batch_gross_revenue_at_risk=batch_gross_risk,
            cumulative_revenue_recovered=metrics.revenue_recovered,
            gross_revenue_at_risk=metrics.gross_revenue_at_risk,
            potentially_recoverable_revenue=metrics.potentially_recoverable_revenue,
            expected_recovery_value=metrics.total_expected_recovery_value,
            revenue_recovered=batch_revenue,
            recovery_rate=batch_rate,
            ai_recommendations=ai_recs,
            policy_decisions=policy_decs,
            case_traces=case_traces,
        )
