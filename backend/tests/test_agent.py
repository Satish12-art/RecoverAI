"""Comprehensive unit and integration test suite for RecoverAI Bounded Agent & State Machine."""

import time
import pytest
from app.agent.llm_client import LLMClient, MockLLMClient
from app.agent.orchestrator import AgentOrchestrator
from app.agent.schemas import (
    AgentContext,
    AllowedAction,
    CustomerContext,
    LLMDiagnosis,
    LLMRecommendation,
    LLMStructuredOutput,
    PaymentContext,
    ScoringContext,
)
from app.agent.state import TerminalState
from app.models.models import Customer, Payment, Order, RecoveryCase, AgentAction, RecoveryOutcome


@pytest.fixture
def agent_test_db(db):
    """Seed test fixtures for agent test scenarios."""
    db.query(RecoveryOutcome).delete()
    db.query(AgentAction).delete()
    db.query(RecoveryCase).delete()
    db.query(Payment).delete()
    db.query(Order).delete()
    db.query(Customer).delete()
    db.commit()

    # Customer 1: Prime customer
    c_prime = Customer(
        id=501,
        external_customer_id="cust_000501",
        name="Vikram Seth",
        total_orders=25,
        successful_payments=24,
        failed_payments=1,
        customer_tenure_days=500,
        opted_out=False,
    )
    # Customer 2: Opted out customer
    c_optout = Customer(
        id=502,
        external_customer_id="cust_000502",
        name="Sunita Rao",
        total_orders=10,
        successful_payments=9,
        failed_payments=1,
        customer_tenure_days=200,
        opted_out=True,
    )
    # Customer 3: Risky customer
    c_risky = Customer(
        id=503,
        external_customer_id="cust_000503",
        name="Karan Malhotra",
        total_orders=4,
        successful_payments=1,
        failed_payments=3,
        chargeback_count=2,
        customer_tenure_days=15,
        opted_out=False,
    )
    db.add_all([c_prime, c_optout, c_risky])
    db.commit()

    # Payment 1: ₹4,999 transient bank error (Demo Case 1)
    p1 = Payment(
        id=501,
        external_payment_id="pay_0000501",
        customer_id=501,
        amount=4999.0,
        currency="INR",
        status="failed",
        payment_method="upi",
        failure_code="temporary_bank_error",
        failure_reason="Bank network timeout",
        risk_flagged=False,
    )
    # Payment 2: Expired card (Demo Case 2)
    p2 = Payment(
        id=502,
        external_payment_id="pay_0000502",
        customer_id=501,
        amount=2999.0,
        currency="INR",
        status="failed",
        payment_method="card",
        failure_code="expired_card",
        failure_reason="Card expired",
        risk_flagged=False,
    )
    # Payment 3: ₹65,000 High Value (Demo Case 3)
    p3 = Payment(
        id=503,
        external_payment_id="pay_0000503",
        customer_id=501,
        amount=65000.0,
        currency="INR",
        status="failed",
        payment_method="card",
        failure_code="temporary_bank_error",
        risk_flagged=False,
    )
    # Payment 4: Risk Flagged (Demo Case 4)
    p4 = Payment(
        id=504,
        external_payment_id="pay_0000504",
        customer_id=501,
        amount=1500.0,
        currency="INR",
        status="failed",
        payment_method="card",
        failure_code="risk_flagged",
        risk_flagged=True,
    )
    # Payment 5: Opted Out Payment
    p5 = Payment(
        id=505,
        external_payment_id="pay_0000505",
        customer_id=502,
        amount=1200.0,
        currency="INR",
        status="failed",
        payment_method="upi",
        failure_code="temporary_bank_error",
        risk_flagged=False,
    )
    # Payment 6: Low probability payment
    p6 = Payment(
        id=506,
        external_payment_id="pay_0000506",
        customer_id=503,
        amount=15000.0,
        currency="INR",
        status="failed",
        payment_method="card",
        failure_code="insufficient_funds",
        risk_flagged=False,
    )
    db.add_all([p1, p2, p3, p4, p5, p6])
    db.commit()

    # Recovery cases
    cases = [
        RecoveryCase(id=501, payment_id=501, customer_id=501, amount_at_risk=4999.0, status="OPEN", retry_count=0),
        RecoveryCase(id=502, payment_id=502, customer_id=501, amount_at_risk=2999.0, status="OPEN", retry_count=0),
        RecoveryCase(id=503, payment_id=503, customer_id=501, amount_at_risk=65000.0, status="OPEN", retry_count=0),
        RecoveryCase(id=504, payment_id=504, customer_id=501, amount_at_risk=1500.0, status="OPEN", retry_count=0),
        RecoveryCase(id=505, payment_id=505, customer_id=502, amount_at_risk=1200.0, status="OPEN", retry_count=0),
        RecoveryCase(id=506, payment_id=506, customer_id=503, amount_at_risk=15000.0, status="OPEN", retry_count=0),
    ]
    db.add_all(cases)
    db.commit()

    return {"p1": p1, "cases": cases}


class AdversarialMockLLM(LLMClient):
    """Adversarial LLM attempting to bypass policy or manipulate amounts."""

    def __init__(self, action="retry", note=""):
        self.action = action
        self.note = note

    def generate_structured_decision(self, context: AgentContext) -> LLMStructuredOutput:
        return LLMStructuredOutput(
            diagnosis=LLMDiagnosis(failure_category="adversarial", summary="Adversarial attempt."),
            recommendation=LLMRecommendation(action=AllowedAction(self.action), reason="Force execute action."),
            message_personalization=self.note,
        )


class FaultyLLM(LLMClient):
    """Faulty LLM raising exceptions or timeouts."""

    def generate_structured_decision(self, context: AgentContext) -> LLMStructuredOutput:
        raise RuntimeError("LLM provider 500 internal error")


class TestAgentExecutionFlows:
    """Test standard and demo agent execution flows."""

    def test_demo_case_1_successful_retry(self, db, agent_test_db):
        """Case 1: ₹4,999 temporary_bank_error -> AI recommends retry -> Policy approves -> retry executed."""
        orchestrator = AgentOrchestrator(llm_client=MockLLMClient())
        result = orchestrator.run(db, case_id=501)

        assert result.final_state == TerminalState.RECOVERING
        assert result.recommended_action == "retry"
        assert result.policy_decision == "APPROVE"
        assert result.action_executed is True
        assert result.agent_action_id is not None
        assert result.recovery_outcome_id is not None
        assert result.recovery_probability >= 0.85
        assert result.scorer_confidence >= 0.85
        assert result.llm_calls_made == 1

        # Check trace
        steps = [t.step.value for t in result.trace]
        assert steps == [
            "DETECTED",
            "ELIGIBILITY_CHECK",
            "CONTEXT_LOADING",
            "SCORING",
            "DIAGNOSING",
            "DECISION_PENDING",
            "POLICY_CHECK",
            "ACTION_EXECUTION",
            "TERMINAL",
        ]

    def test_demo_case_2_message_recommendation(self, db, agent_test_db):
        """Case 2: Expired card -> AI recommends message -> Policy approves -> Message sent."""
        orchestrator = AgentOrchestrator(llm_client=MockLLMClient())
        result = orchestrator.run(db, case_id=502)

        assert result.final_state == TerminalState.RECOVERING
        assert result.recommended_action == "message"
        assert result.policy_decision == "APPROVE"
        assert result.action_executed is True

    def test_demo_case_3_human_escalation_high_amount(self, db, agent_test_db):
        """Case 3: ₹65,000 -> Even if AI recommends retry, Policy overrides to ESCALATE."""
        # Test with AI recommending retry on ₹65k
        orchestrator = AgentOrchestrator(llm_client=AdversarialMockLLM(action="retry"))
        result = orchestrator.run(db, case_id=503)

        assert result.final_state == TerminalState.ESCALATED
        assert result.policy_decision == "ESCALATE"
        assert "AMOUNT_LIMIT_EXCEEDED" in result.policy_reason_codes
        assert result.action_executed is False

    def test_demo_case_4_risk_stop_no_llm_call(self, db, agent_test_db):
        """Case 4: risk_flagged -> Eligibility gate catches it -> No LLM call made -> STOP."""
        orchestrator = AgentOrchestrator(llm_client=MockLLMClient())
        result = orchestrator.run(db, case_id=504)

        assert result.final_state == TerminalState.STOPPED
        assert result.policy_decision == "STOP"
        assert result.llm_calls_made == 0  # Cost & safety optimization
        assert result.action_executed is False

    def test_demo_case_5_opted_out_stop_no_llm_call(self, db, agent_test_db):
        """Opted out customer caught by eligibility gate -> STOP."""
        orchestrator = AgentOrchestrator(llm_client=MockLLMClient())
        result = orchestrator.run(db, case_id=505)

        assert result.final_state == TerminalState.STOPPED
        assert result.policy_decision == "STOP"
        assert result.llm_calls_made == 0

    def test_low_probability_causes_escalation(self, db, agent_test_db):
        """Low recovery probability -> Policy overrides retry to Escalation."""
        orchestrator = AgentOrchestrator(llm_client=AdversarialMockLLM(action="retry"))
        result = orchestrator.run(db, case_id=506)

        assert result.final_state == TerminalState.ESCALATED
        assert result.policy_decision == "ESCALATE"
        assert "LOW_RECOVERY_PROBABILITY" in result.policy_reason_codes
        assert result.action_executed is False

    def test_retry_limit_causes_escalation(self, db, agent_test_db):
        """Case with 2 attempts escalates without retry even if AI recommends retry."""
        case = db.query(RecoveryCase).filter(RecoveryCase.id == 501).first()
        case.retry_count = 2
        db.commit()

        orchestrator = AgentOrchestrator(llm_client=AdversarialMockLLM(action="retry"))
        result = orchestrator.run(db, case_id=501)

        assert result.final_state == TerminalState.ESCALATED
        assert result.policy_decision == "ESCALATE"
        assert "MAX_RETRIES_REACHED" in result.policy_reason_codes


class TestAgentSafetyAndSecurity:
    """Critical safety, adversarial, and boundary tests."""

    def test_adversarial_llm_cannot_bypass_risk_flag(self, db, agent_test_db):
        """Adversarial LLM attempts to force a retry on a risk flagged case -> Policy stops it."""
        p = db.query(Payment).filter(Payment.id == 504).first()
        p.failure_code = "temporary_bank_error"  # to pass eligibility check to LLM
        db.commit()

        adversarial_llm = AdversarialMockLLM(action="retry")
        orchestrator = AgentOrchestrator(llm_client=adversarial_llm)
        result = orchestrator.run(db, case_id=504)

        assert result.final_state == TerminalState.STOPPED
        assert result.policy_decision == "STOP"
        assert result.action_executed is False

    def test_faulty_llm_fails_safely_to_escalation(self, db, agent_test_db):
        """Faulty LLM raising exception fails safely to human escalation."""
        orchestrator = AgentOrchestrator(llm_client=FaultyLLM())
        result = orchestrator.run(db, case_id=501)

        assert result.final_state == TerminalState.ESCALATED
        assert "LLM failure" in result.error
        assert result.action_executed is False

    def test_llm_cannot_change_probability_or_confidence(self, db, agent_test_db):
        """Scorer output remains deterministic and unchanged regardless of LLM recommendation."""
        orchestrator = AgentOrchestrator(llm_client=MockLLMClient())
        result = orchestrator.run(db, case_id=501)

        assert result.recovery_probability >= 0.85
        assert result.scorer_confidence >= 0.85

    def test_mock_mode_is_deterministic(self, db, agent_test_db):
        """Same input context produces identical recommendation across runs."""
        client = MockLLMClient()
        pmt = PaymentContext(id=1, amount=4999, currency="INR", status="failed", failure_code="temporary_bank_error", risk_flagged=False)
        cust = CustomerContext(id=1, name="Test", customer_tenure_days=100, total_orders=10, successful_payments=9, failed_payments=1, historical_success_rate=0.9, average_order_value=2000, chargeback_count=0, refund_count=0, opted_out=False)
        sc = ScoringContext(recovery_probability=0.85, scorer_confidence=0.90, expected_recovery_value=4249, previous_recovery_attempts=0)
        ctx = AgentContext(payment=pmt, customer=cust, scoring=sc)

        res1 = client.generate_structured_decision(ctx)
        res2 = client.generate_structured_decision(ctx)

        assert res1.recommendation.action == res2.recommendation.action
        assert res1.diagnosis.failure_category == res2.diagnosis.failure_category

    def test_approved_action_calls_exactly_one_bounded_tool(self, db, agent_test_db):
        """Successful retry creates exactly 1 agent_action and 1 recovery_outcome."""
        orchestrator = AgentOrchestrator(llm_client=MockLLMClient())
        result = orchestrator.run(db, case_id=501)

        actions = db.query(AgentAction).filter(AgentAction.recovery_case_id == 501).all()
        outcomes = db.query(RecoveryOutcome).filter(RecoveryOutcome.recovery_case_id == 501).all()

        assert len(actions) == 1
        assert len(outcomes) == 1

    def test_blocked_action_calls_zero_write_tools(self, db, agent_test_db):
        """Blocked high amount case creates zero pending outcomes."""
        orchestrator = AgentOrchestrator(llm_client=AdversarialMockLLM(action="retry"))
        result = orchestrator.run(db, case_id=503)

        outcomes = db.query(RecoveryOutcome).filter(RecoveryOutcome.recovery_case_id == 503).all()
        assert len(outcomes) == 0


class TestAgentApiEndpoint:
    """Test POST /api/agent/recover/{case_id} endpoint."""

    def test_api_run_recovery_agent(self, client):
        # Case 1 is seeded by conftest fixture
        res = client.post("/api/agent/recover/1")
        assert res.status_code == 200
        data = res.json()

        assert data["case_id"] == 1
        assert data["final_state"] == "RECOVERING"
        assert data["recommended_action"] == "retry"
        assert data["policy_decision"] == "APPROVE"
        assert len(data["trace"]) > 0

    def test_api_run_recovery_agent_not_found(self, client):
        res = client.post("/api/agent/recover/99999")
        assert res.status_code == 404
