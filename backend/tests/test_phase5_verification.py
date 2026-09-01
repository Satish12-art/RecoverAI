"""Phase 5 Final Verification Tests.

Explicitly validates:
1. Blocked Action Retry Count (no increment, no pending outcome, case not RECOVERING, audit record created)
2. Idempotency Persistence (durable persistence in database, survives session restart)
3. Message != Recovery (sending message does not increase revenue recovered; only observed outcome does)
"""

import pytest
from app.core.database import SessionLocal
from app.models.models import Customer, Payment, Order, RecoveryCase, AgentAction, RecoveryOutcome
from app.tools.recovery_tools import RecoveryTools
from app.tools.outcome_tools import OutcomeObserver
from app.services.revenue_metrics import RevenueMetricsService


@pytest.fixture
def verification_db(db):
    """Seed dedicated database records for the 3 verification checks."""
    db.query(RecoveryOutcome).delete()
    db.query(AgentAction).delete()
    db.query(RecoveryCase).delete()
    db.query(Payment).delete()
    db.query(Order).delete()
    db.query(Customer).delete()
    db.commit()

    # Good Customer
    c_good = Customer(
        id=100,
        external_customer_id="cust_000100",
        name="Ananya Verma",
        total_orders=20,
        successful_payments=19,
        failed_payments=1,
        customer_tenure_days=300,
        opted_out=False,
    )
    # Risky Customer with chargebacks
    c_risky = Customer(
        id=200,
        external_customer_id="cust_000200",
        name="Manish Kumar",
        total_orders=5,
        successful_payments=1,
        failed_payments=4,
        chargeback_count=2,
        customer_tenure_days=20,
        opted_out=False,
    )
    db.add_all([c_good, c_risky])
    db.commit()

    # 1. Normal transient failure payment
    p_good = Payment(
        id=100,
        external_payment_id="pay_0000100",
        customer_id=100,
        amount=4999.0,
        status="failed",
        payment_method="upi",
        failure_code="temporary_bank_error",
        risk_flagged=False,
    )
    # 2. Risk-flagged payment
    p_risk = Payment(
        id=200,
        external_payment_id="pay_0000200",
        customer_id=100,
        amount=2500.0,
        status="failed",
        payment_method="card",
        failure_code="risk_flagged",
        risk_flagged=True,
    )
    # 3. Low probability payment (insufficient funds on risky customer)
    p_low_prob = Payment(
        id=300,
        external_payment_id="pay_0000300",
        customer_id=200,
        amount=15000.0,
        status="failed",
        payment_method="card",
        failure_code="insufficient_funds",
        risk_flagged=False,
    )
    db.add_all([p_good, p_risk, p_low_prob])
    db.commit()

    # Cases
    case_good = RecoveryCase(id=100, payment_id=100, customer_id=100, amount_at_risk=4999.0, status="OPEN", retry_count=0)
    case_risk = RecoveryCase(id=200, payment_id=200, customer_id=100, amount_at_risk=2500.0, status="OPEN", retry_count=0)
    case_low_prob = RecoveryCase(id=300, payment_id=300, customer_id=200, amount_at_risk=15000.0, status="OPEN", retry_count=0)
    db.add_all([case_good, case_risk, case_low_prob])
    db.commit()

    return {"case_good": case_good, "case_risk": case_risk, "case_low_prob": case_low_prob}


class TestPhase5FinalVerification:
    """Three mandatory code-level verification checks."""

    def test_check_1_blocked_action_retry_count_and_state(self, db, verification_db):
        """Check 1:
        Verify that policy-blocked request_payment_retry:
        - does NOT increment retry_count
        - does NOT create a pending recovery outcome
        - does NOT change case to RECOVERING
        - DOES create audit record in agent_actions
        """
        # Test 1A: risk_flagged -> retry request -> STOP
        res_risk = RecoveryTools.request_payment_retry(db, case_id=200)
        assert res_risk.success is False
        assert res_risk.policy.decision.value == "STOP"

        case_risk = db.query(RecoveryCase).filter(RecoveryCase.id == 200).first()
        assert case_risk.retry_count == 0  # NOT incremented
        assert case_risk.status == "STOPPED"  # NOT RECOVERING

        outcomes_risk = db.query(RecoveryOutcome).filter(RecoveryOutcome.recovery_case_id == 200).all()
        assert len(outcomes_risk) == 0  # NO pending outcome

        actions_risk = db.query(AgentAction).filter(AgentAction.recovery_case_id == 200).all()
        assert len(actions_risk) == 1  # Audit record created
        assert actions_risk[0].action_type == "policy_blocked"
        assert actions_risk[0].policy_decision == "STOP"

        # Test 1B: low probability -> retry request -> ESCALATE
        res_esc = RecoveryTools.request_payment_retry(db, case_id=300)
        assert res_esc.success is False
        assert res_esc.policy.decision.value == "ESCALATE"

        case_esc = db.query(RecoveryCase).filter(RecoveryCase.id == 300).first()
        assert case_esc.retry_count == 0  # NOT incremented
        assert case_esc.status == "ESCALATED"  # NOT RECOVERING

        outcomes_esc = db.query(RecoveryOutcome).filter(RecoveryOutcome.recovery_case_id == 300).all()
        assert len(outcomes_esc) == 0  # NO pending outcome

        actions_esc = db.query(AgentAction).filter(AgentAction.recovery_case_id == 300).all()
        assert len(actions_esc) == 1  # Audit record created
        assert actions_esc[0].action_type == "policy_blocked"
        assert actions_esc[0].policy_decision == "ESCALATE"

    def test_check_2_idempotency_durable_persistence(self, db, verification_db):
        """Check 2:
        Verify that write-tool idempotency is persisted durably in the database.
        Survives new session/process request.
        """
        # Session 1: Execute retry with specific key
        res1 = RecoveryTools.request_payment_retry(db, case_id=100, idempotency_key="durable_key_001")
        assert res1.success is True
        assert res1.data["action_executed"] is True
        assert res1.data.get("idempotent_replay") is None
        action_id = res1.data["agent_action_id"]

        # Close session and create a brand-new DB session simulating a new request
        db.close()
        new_session = SessionLocal()
        try:
            # Session 2: Send identical retry request with same idempotency key
            res2 = RecoveryTools.request_payment_retry(new_session, case_id=100, idempotency_key="durable_key_001")
            assert res2.success is True
            assert res2.data.get("idempotent_replay") is True
            assert res2.data["agent_action_id"] == action_id

            # Verify no duplicate action logs created
            actions = new_session.query(AgentAction).filter(AgentAction.recovery_case_id == 100).all()
            assert len(actions) == 1

            # Verify no duplicate pending outcomes created
            outcomes = new_session.query(RecoveryOutcome).filter(RecoveryOutcome.recovery_case_id == 100).all()
            assert len(outcomes) == 1

            # Verify retry count remained at 1 (not double-incremented)
            case = new_session.query(RecoveryCase).filter(RecoveryCase.id == 100).first()
            assert case.retry_count == 1
        finally:
            new_session.close()

    def test_check_escalate_to_human_idempotency(self, db, verification_db):
        """Verify escalate_to_human idempotency and single audit trail row across multiple calls."""
        res1 = RecoveryTools.escalate_to_human(db, case_id=300, reason="Initial review needed")
        assert res1.success is True
        action_id = res1.data["agent_action_id"]

        # Call again on same case
        res2 = RecoveryTools.escalate_to_human(db, case_id=300, reason="Duplicate trigger")
        assert res2.success is True
        assert res2.data.get("idempotent_replay") is True
        assert res2.data["agent_action_id"] == action_id

        # Verify exactly 1 AgentAction row in database
        actions = db.query(AgentAction).filter(AgentAction.recovery_case_id == 300).all()
        assert len(actions) == 1

    def test_check_3_message_does_not_equal_recovery(self, db, verification_db):
        """Check 3:
        Verify:
        send_recovery_message -> action executed -> pending outcome -> revenue recovered remains 0.0.
        Only observed outcome with amount_recovered > 0 may increase Revenue Recovered.
        """
        # 1. Send Recovery Message
        msg_res = RecoveryTools.send_recovery_message(
            db,
            case_id=100,
            template_id="PAYMENT_RETRY",
            personalized_note="Please retry whenever convenient.",
        )
        assert msg_res.success is True
        assert msg_res.data["action_executed"] is True
        assert msg_res.data["outcome_status"] == "pending"
        action_id = msg_res.data["agent_action_id"]

        # 2. Check 3-Tier Metrics: Revenue Recovered must be strictly 0.00
        payments = db.query(Payment).all()
        customers = {c.id: c for c in db.query(Customer).all()}
        outcomes_pending = db.query(RecoveryOutcome).all()

        metrics_pending = RevenueMetricsService.calculate_metrics(
            payments=payments,
            customer_map=customers,
            observed_outcomes=outcomes_pending,
        )
        assert metrics_pending.revenue_recovered == 0.00
        assert metrics_pending.recovery_rate == 0.00

        # 3. Transition to Observed Recovered Outcome
        obs_res = OutcomeObserver.observe_outcome(
            db,
            agent_action_id=action_id,
            outcome="recovered",
            amount_recovered=4999.0,
            source="simulation",
        )
        assert obs_res.success is True
        assert obs_res.data["outcome_status"] == "observed"

        # 4. Check 3-Tier Metrics again: Revenue Recovered must now reflect ₹4,999.00
        outcomes_observed = db.query(RecoveryOutcome).all()
        metrics_observed = RevenueMetricsService.calculate_metrics(
            payments=payments,
            customer_map=customers,
            observed_outcomes=outcomes_observed,
        )
        assert metrics_observed.revenue_recovered == 4999.00
        assert metrics_observed.recovery_rate > 0.00
