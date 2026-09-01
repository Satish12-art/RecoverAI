"""Unit and Integration tests for RecoverAI Agent Tools and Outcome Observation."""

import pytest
from app.models.models import Payment, Order, Customer, RecoveryCase, AgentAction, RecoveryOutcome
from app.tools.read_tools import ReadTools
from app.tools.recovery_tools import RecoveryTools
from app.tools.outcome_tools import OutcomeObserver
from app.tools.tool_registry import ToolRegistry
from app.services.revenue_metrics import RevenueMetricsService


@pytest.fixture
def test_setup(db):
    """Seed test fixtures specifically for tool operations, cleaning up before/after."""
    db.query(RecoveryOutcome).delete()
    db.query(AgentAction).delete()
    db.query(RecoveryCase).delete()
    db.query(Payment).delete()
    db.query(Order).delete()
    db.query(Customer).delete()
    db.commit()

    # Customer 1: High quality
    c1 = Customer(
        id=10,
        external_customer_id="cust_000010",
        name="Aarav Gupta",
        email="aarav@example.com",
        total_orders=25,
        successful_payments=24,
        failed_payments=1,
        chargeback_count=0,
        customer_tenure_days=500,
        opted_out=False,
    )
    # Customer 2: Risky / Opted out
    c2 = Customer(
        id=20,
        external_customer_id="cust_000020",
        name="Rohan Mehta",
        email="rohan@example.com",
        total_orders=5,
        successful_payments=2,
        failed_payments=3,
        chargeback_count=2,
        customer_tenure_days=30,
        opted_out=True,
    )
    db.add_all([c1, c2])
    db.commit()

    # Order 1 & 2
    o1 = Order(id=10, external_order_id="ord_000010", customer_id=10, amount=4999.0, status="failed")
    o2 = Order(id=20, external_order_id="ord_000020", customer_id=20, amount=75000.0, status="failed")
    db.add_all([o1, o2])
    db.commit()

    # Payment 1: Eligible failed payment (₹4,999, temporary_bank_error)
    p1 = Payment(
        id=10,
        external_payment_id="pay_0000010",
        external_order_id="ord_000010",
        customer_id=10,
        order_id=10,
        amount=4999.0,
        currency="INR",
        status="failed",
        payment_method="upi",
        failure_code="temporary_bank_error",
        failure_reason="Bank switch timeout",
        risk_flagged=False,
    )
    # Payment 2: High value failed payment (₹75,000)
    p2 = Payment(
        id=20,
        external_payment_id="pay_0000020",
        external_order_id="ord_000020",
        customer_id=20,
        order_id=20,
        amount=75000.0,
        currency="INR",
        status="failed",
        payment_method="card",
        failure_code="insufficient_funds",
        risk_flagged=False,
    )
    # Payment 3: Risk flagged payment
    p3 = Payment(
        id=30,
        external_payment_id="pay_0000030",
        external_order_id="ord_000010",
        customer_id=10,
        order_id=10,
        amount=2500.0,
        currency="INR",
        status="failed",
        payment_method="card",
        failure_code="risk_flagged",
        risk_flagged=True,
    )
    db.add_all([p1, p2, p3])
    db.commit()

    # Cases
    case1 = RecoveryCase(
        id=10,
        payment_id=10,
        customer_id=10,
        amount_at_risk=4999.0,
        status="OPEN",
        retry_count=0,
    )
    case2 = RecoveryCase(
        id=20,
        payment_id=20,
        customer_id=20,
        amount_at_risk=75000.0,
        status="OPEN",
        retry_count=0,
    )
    case3 = RecoveryCase(
        id=30,
        payment_id=30,
        customer_id=10,
        amount_at_risk=2500.0,
        status="OPEN",
        retry_count=0,
    )
    db.add_all([case1, case2, case3])
    db.commit()

    return {"case1": case1, "case2": case2, "case3": case3, "p1": p1, "p2": p2, "p3": p3}


class TestReadTools:
    """Test all read-only agent tools."""

    def test_get_payment(self, db, test_setup):
        res = ReadTools.get_payment(db, payment_id=10)
        assert res.success is True
        assert res.data["id"] == 10
        assert res.data["amount"] == 4999.0
        assert res.data["failure_code"] == "temporary_bank_error"
        # Verify no ground truth leaked
        assert "true_best_action" not in res.data

    def test_get_payment_not_found(self, db):
        res = ReadTools.get_payment(db, payment_id=99999)
        assert res.success is False
        assert "not found" in res.error

    def test_get_order(self, db, test_setup):
        res = ReadTools.get_order(db, order_id=10)
        assert res.success is True
        assert res.data["id"] == 10
        assert res.data["customer_id"] == 10

    def test_get_customer(self, db, test_setup):
        res = ReadTools.get_customer(db, customer_id=10)
        assert res.success is True
        assert res.data["name"] == "Aarav Gupta"
        assert res.data["opted_out"] is False

    def test_get_customer_history(self, db, test_setup):
        res = ReadTools.get_customer_history(db, customer_id=10)
        assert res.success is True
        assert res.data["total_orders"] == 25
        assert res.data["successful_payments"] == 24
        assert res.data["historical_success_rate"] == 0.96

    def test_calculate_recovery_score(self, db, test_setup):
        res = ReadTools.calculate_recovery_score(db, payment_id=10)
        assert res.success is True
        assert res.data["recovery_probability"] >= 0.85
        assert res.data["scorer_confidence"] >= 0.85
        assert res.data["expected_recovery_value"] > 0

    def test_get_recovery_case(self, db, test_setup):
        res = ReadTools.get_recovery_case(db, case_id=10)
        assert res.success is True
        assert res.data["id"] == 10
        assert res.data["amount_at_risk"] == 4999.0

    def test_get_recovery_status_initial_state(self, db, test_setup):
        res = ReadTools.get_recovery_status(db, case_id=10)
        assert res.success is True
        assert res.data["case_status"] == "OPEN"
        assert res.data["is_recovered"] is False
        assert res.data["amount_recovered"] == 0.0


class TestWriteTools:
    """Test policy-gated write tools, simulation outcomes, and audit logging."""

    def test_approved_retry_executes_simulation(self, db, test_setup):
        """Happy path: High quality customer transient error approves retry and creates pending outcome."""
        res = RecoveryTools.request_payment_retry(db, case_id=10)

        assert res.success is True
        assert res.data["action_executed"] is True
        assert res.data["outcome_status"] == "pending"
        assert res.data["simulated"] is True
        assert res.policy.decision.value == "APPROVE"

        # Verify case updated
        case = db.query(RecoveryCase).filter(RecoveryCase.id == 10).first()
        assert case.status == "RECOVERING"
        assert case.retry_count == 1

        # Verify audit log in agent_actions
        action_log = db.query(AgentAction).filter(AgentAction.recovery_case_id == 10).first()
        assert action_log is not None
        assert action_log.tool_name == "request_payment_retry"
        assert action_log.policy_decision == "APPROVE"

        # Verify pending recovery outcome created
        outcome = db.query(RecoveryOutcome).filter(RecoveryOutcome.recovery_case_id == 10).first()
        assert outcome is not None
        assert outcome.outcome_status == "pending"
        assert outcome.successful is None
        assert outcome.amount_recovered == 0.0

    def test_risk_flagged_payment_retry_is_blocked(self, db, test_setup):
        """Hard safety check: Risk flagged payment is blocked by policy."""
        res = RecoveryTools.request_payment_retry(db, case_id=30)

        assert res.success is False
        assert "Action blocked by policy" in res.error
        assert res.policy.decision.value == "STOP"

        # Verify case status set to STOPPED
        case = db.query(RecoveryCase).filter(RecoveryCase.id == 30).first()
        assert case.status == "STOPPED"

        # Verify NO recovery outcome created
        outcome = db.query(RecoveryOutcome).filter(RecoveryOutcome.recovery_case_id == 30).first()
        assert outcome is None

    def test_opted_out_customer_retry_is_blocked(self, db, test_setup):
        """Hard safety check: Customer opted out is blocked by policy."""
        res = RecoveryTools.request_payment_retry(db, case_id=20)
        assert res.success is False
        assert res.policy.decision.value in ("STOP", "ESCALATE")

    def test_high_amount_retry_escalates(self, db, test_setup):
        """₹75,000 payment escalates due to amount limit."""
        p_high = Payment(
            id=40,
            external_payment_id="pay_0000040",
            customer_id=10,
            amount=75000.0,
            currency="INR",
            status="failed",
            failure_code="temporary_bank_error",
        )
        c_high = RecoveryCase(id=40, payment_id=40, customer_id=10, amount_at_risk=75000.0, status="OPEN")
        db.add_all([p_high, c_high])
        db.commit()

        res = RecoveryTools.request_payment_retry(db, case_id=40)
        assert res.success is False
        assert res.policy.decision.value == "ESCALATE"
        assert "AMOUNT_LIMIT_EXCEEDED" in [r.value for r in res.policy.reason_codes]

    def test_retry_limit_blocks_after_max_attempts(self, db, test_setup):
        """Case with 2 attempts escalates when 3rd attempt is requested."""
        case = db.query(RecoveryCase).filter(RecoveryCase.id == 10).first()
        case.retry_count = 2
        db.commit()

        res = RecoveryTools.request_payment_retry(db, case_id=10)
        assert res.success is False
        assert res.policy.decision.value == "ESCALATE"
        assert "MAX_RETRIES_REACHED" in [r.value for r in res.policy.reason_codes]

    def test_send_recovery_message_approved(self, db, test_setup):
        """Approved message sends simulated message and logs audit."""
        res = RecoveryTools.send_recovery_message(
            db,
            case_id=10,
            template_id="PAYMENT_RETRY",
            personalized_note="Please retry your transaction.",
        )
        assert res.success is True
        assert res.data["action_executed"] is True
        assert "Aarav Gupta" in res.data["message_body"]
        assert "4,999.00" in res.data["message_body"]
        assert res.data["outcome_status"] == "pending"

    def test_send_recovery_message_rejects_unsafe_personalization(self, db, test_setup):
        """Personalization requesting CVV or passwords is rejected immediately."""
        res = RecoveryTools.send_recovery_message(
            db,
            case_id=10,
            template_id="PAYMENT_RETRY",
            personalized_note="Please send your CVV and netbanking password.",
        )
        assert res.success is False
        assert "Prohibited content detected" in res.error

    def test_escalate_to_human(self, db, test_setup):
        """Explicit human escalation updates case status and logs audit."""
        res = RecoveryTools.escalate_to_human(db, case_id=10, reason="High value customer disputed charge.")
        assert res.success is True
        assert res.data["escalated"] is True

        case = db.query(RecoveryCase).filter(RecoveryCase.id == 10).first()
        assert case.status == "ESCALATED"
        assert case.escalation_reason == "High value customer disputed charge."

    def test_idempotent_action_does_not_execute_twice(self, db, test_setup):
        """Re-submitting with same idempotency key returns existing action without creating duplicate outcome."""
        res1 = RecoveryTools.request_payment_retry(db, case_id=10, idempotency_key="unique_retry_001")
        assert res1.success is True

        outcomes_count_1 = db.query(RecoveryOutcome).filter(RecoveryOutcome.recovery_case_id == 10).count()

        # Call again with same idempotency key
        res2 = RecoveryTools.request_payment_retry(db, case_id=10, idempotency_key="unique_retry_001")
        assert res2.success is True
        assert res2.data.get("idempotent_replay") is True

        outcomes_count_2 = db.query(RecoveryOutcome).filter(RecoveryOutcome.recovery_case_id == 10).count()
        assert outcomes_count_1 == outcomes_count_2


class TestOutcomeObservation:
    """Test outcome observation rules, validations, and bounds."""

    def test_observe_outcome_happy_path(self, db, test_setup):
        # 1. Execute retry
        res_action = RecoveryTools.request_payment_retry(db, case_id=10)
        action_id = res_action.data["agent_action_id"]

        # 2. Observe outcome
        res_obs = OutcomeObserver.observe_outcome(
            db,
            agent_action_id=action_id,
            outcome="recovered",
            amount_recovered=4999.0,
            source="simulation",
        )
        assert res_obs.success is True
        assert res_obs.data["outcome_status"] == "observed"
        assert res_obs.data["successful"] is True
        assert res_obs.data["amount_recovered"] == 4999.0

        # Case updated to RECOVERED
        case = db.query(RecoveryCase).filter(RecoveryCase.id == 10).first()
        assert case.status == "RECOVERED"

    def test_outcome_amount_cannot_exceed_payment_amount(self, db, test_setup):
        """Security: Rejects manipulated outcome where recovered amount > payment amount."""
        res_action = RecoveryTools.request_payment_retry(db, case_id=10)
        action_id = res_action.data["agent_action_id"]

        res_obs = OutcomeObserver.observe_outcome(
            db,
            agent_action_id=action_id,
            outcome="recovered",
            amount_recovered=99999.0,  # exceeds payment amount of 4999.0
            source="simulation",
        )
        assert res_obs.success is False
        assert "cannot exceed original payment amount" in res_obs.error

    def test_duplicate_outcome_observation_is_rejected(self, db, test_setup):
        """Cannot finalize the same outcome twice."""
        res_action = RecoveryTools.request_payment_retry(db, case_id=10)
        action_id = res_action.data["agent_action_id"]

        # First observation
        OutcomeObserver.observe_outcome(db, agent_action_id=action_id, outcome="recovered", amount_recovered=4999.0)

        # Second observation on same action
        res_second = OutcomeObserver.observe_outcome(
            db, agent_action_id=action_id, outcome="recovered", amount_recovered=4999.0
        )
        assert res_second.success is False
        assert "already been finalized" in res_second.error


class TestEndToEndToolIntegration:
    """Full integration simulation test flow."""

    def test_complete_positive_recovery_flow(self, db, test_setup):
        """Complete positive path:
        Failed payment -> get_payment -> get_customer_history -> calculate_recovery_score ->
        request_payment_retry -> policy approves -> pending outcome -> outcome observed -> revenue recovered updated.
        """
        # Step 1: Read payment
        pmt_res = ReadTools.get_payment(db, payment_id=10)
        assert pmt_res.success is True

        # Step 2: Read customer history
        hist_res = ReadTools.get_customer_history(db, customer_id=pmt_res.data["customer_id"])
        assert hist_res.success is True

        # Step 3: Calculate score
        score_res = ReadTools.calculate_recovery_score(db, payment_id=10)
        assert score_res.success is True

        # Step 4: Request Retry
        retry_res = RecoveryTools.request_payment_retry(db, case_id=10)
        assert retry_res.success is True
        action_id = retry_res.data["agent_action_id"]

        # Verify revenue recovered before observation is still 0
        payments = db.query(Payment).all()
        customers = {c.id: c for c in db.query(Customer).all()}
        outcomes_before = db.query(RecoveryOutcome).all()
        metrics_before = RevenueMetricsService.calculate_metrics(payments, customers, outcomes_before)
        assert metrics_before.revenue_recovered == 0.0

        # Step 5: Observe outcome
        obs_res = OutcomeObserver.observe_outcome(
            db, agent_action_id=action_id, outcome="recovered", amount_recovered=4999.0
        )
        assert obs_res.success is True

        # Step 6: Verify revenue recovered updated
        outcomes_after = db.query(RecoveryOutcome).all()
        metrics_after = RevenueMetricsService.calculate_metrics(payments, customers, outcomes_after)
        assert metrics_after.revenue_recovered == 4999.0
        assert metrics_after.recovery_rate > 0.0

    def test_complete_negative_risk_flagged_flow(self, db, test_setup):
        """Negative path:
        Risk flagged payment -> request_payment_retry -> policy STOP -> no retry executed -> revenue recovered unchanged.
        """
        retry_res = RecoveryTools.request_payment_retry(db, case_id=30)
        assert retry_res.success is False
        assert retry_res.policy.decision.value == "STOP"

        # Verify audit log exists
        logs = db.query(AgentAction).filter(AgentAction.recovery_case_id == 30).all()
        assert len(logs) >= 1
        assert logs[0].policy_decision == "STOP"

        # Verify no outcomes created
        outcomes = db.query(RecoveryOutcome).filter(RecoveryOutcome.recovery_case_id == 30).all()
        assert len(outcomes) == 0


class TestToolRegistry:
    """Test ToolRegistry metadata."""

    def test_registry_contains_all_tools(self):
        tools = ToolRegistry.get_all_tools()
        names = {t.name for t in tools}

        expected_names = {
            "get_payment",
            "get_order",
            "get_customer",
            "get_customer_history",
            "calculate_recovery_score",
            "get_recovery_case",
            "get_recovery_status",
            "request_payment_retry",
            "send_recovery_message",
            "escalate_to_human",
        }
        assert expected_names.issubset(names)

    def test_read_tools_flagged_read_only(self):
        read_tools = ToolRegistry.get_read_tools()
        for t in read_tools:
            assert t.read_only is True
            assert t.requires_policy is False

    def test_write_tools_require_policy(self):
        write_tools = ToolRegistry.get_write_tools()
        for t in write_tools:
            assert t.read_only is False
            assert t.requires_policy is True
