"""Unit tests for RecoverAI Deterministic Policy Engine."""

import pytest
from app.policies.policy_engine import (
    PolicyEngine,
    PolicyDecision,
    PolicyReasonCode,
)


class TestTenPolicyRules:
    """Test each of the 10 explicit policy rules independently."""

    def test_rule_1_already_successful_payment_stops(self):
        payment = {"status": "paid", "amount": 2000.0}
        res = PolicyEngine.evaluate(
            payment=payment,
            proposed_action="retry",
            recovery_probability=0.95,
            scorer_confidence=0.95,
        )
        assert res.decision == PolicyDecision.STOP
        assert res.action == "stop"
        assert PolicyReasonCode.ALREADY_SUCCESSFUL in res.reason_codes
        assert res.checks[0].rule_number == 1
        assert res.checks[0].passed is False

    def test_rule_2_risk_flagged_payment_stops(self):
        payment = {"status": "failed", "amount": 1000.0, "risk_flagged": True}
        res = PolicyEngine.evaluate(
            payment=payment,
            proposed_action="retry",
            recovery_probability=0.99,
            scorer_confidence=0.99,
        )
        assert res.decision == PolicyDecision.STOP
        assert res.action == "stop"
        assert PolicyReasonCode.RISK_FLAGGED in res.reason_codes

    def test_rule_3_customer_opted_out_stops(self):
        payment = {"status": "failed", "amount": 1500.0, "failure_code": "temporary_bank_error"}
        customer = {"opted_out": True}
        res = PolicyEngine.evaluate(
            payment=payment,
            customer=customer,
            proposed_action="message",
            recovery_probability=0.95,
            scorer_confidence=0.90,
        )
        assert res.decision == PolicyDecision.STOP
        assert res.action == "stop"
        assert PolicyReasonCode.CUSTOMER_OPTED_OUT in res.reason_codes

    def test_rule_4_invalid_payment_state_stops(self):
        payment = {"status": "void_expired", "amount": 2000.0}
        res = PolicyEngine.evaluate(
            payment=payment,
            proposed_action="retry",
            recovery_probability=0.85,
            scorer_confidence=0.85,
        )
        assert res.decision == PolicyDecision.STOP
        assert res.action == "stop"
        assert PolicyReasonCode.INVALID_PAYMENT_STATE in res.reason_codes

    def test_rule_5_unknown_proposed_action_rejects(self):
        payment = {"status": "failed", "amount": 2000.0, "failure_code": "temporary_bank_error"}
        res = PolicyEngine.evaluate(
            payment=payment,
            proposed_action="direct_debit_hack",
            recovery_probability=0.85,
            scorer_confidence=0.85,
        )
        assert res.decision == PolicyDecision.REJECT
        assert res.action == "escalate"
        assert PolicyReasonCode.INVALID_ACTION in res.reason_codes

    def test_rule_6_max_retries_reached_escalates(self):
        payment = {"status": "failed", "amount": 2000.0, "failure_code": "temporary_bank_error"}
        res = PolicyEngine.evaluate(
            payment=payment,
            proposed_action="retry",
            recovery_probability=0.90,
            scorer_confidence=0.90,
            previous_recovery_attempts=2,
            max_retries=2,
        )
        assert res.decision == PolicyDecision.ESCALATE
        assert res.action == "escalate"
        assert PolicyReasonCode.MAX_RETRIES_REACHED in res.reason_codes

    def test_rule_7_low_recovery_probability_escalates(self):
        payment = {"status": "failed", "amount": 2000.0, "failure_code": "insufficient_funds"}
        res = PolicyEngine.evaluate(
            payment=payment,
            proposed_action="retry",
            recovery_probability=0.55,
            scorer_confidence=0.85,
            prob_threshold=0.60,
        )
        assert res.decision == PolicyDecision.ESCALATE
        assert res.action == "escalate"
        assert PolicyReasonCode.LOW_RECOVERY_PROBABILITY in res.reason_codes

    def test_rule_8_low_scorer_confidence_escalates(self):
        payment = {"status": "failed", "amount": 2000.0, "failure_code": "temporary_bank_error"}
        res = PolicyEngine.evaluate(
            payment=payment,
            proposed_action="retry",
            recovery_probability=0.85,
            scorer_confidence=0.65,
            conf_threshold=0.70,
        )
        assert res.decision == PolicyDecision.ESCALATE
        assert res.action == "escalate"
        assert PolicyReasonCode.LOW_SCORER_CONFIDENCE in res.reason_codes

    def test_rule_9_amount_limit_exceeded_escalates(self):
        payment = {"status": "failed", "amount": 50000.01, "failure_code": "temporary_bank_error"}
        res = PolicyEngine.evaluate(
            payment=payment,
            proposed_action="retry",
            recovery_probability=0.90,
            scorer_confidence=0.90,
            amount_limit=50000.0,
        )
        assert res.decision == PolicyDecision.ESCALATE
        assert res.action == "escalate"
        assert PolicyReasonCode.AMOUNT_LIMIT_EXCEEDED in res.reason_codes

    def test_rule_10_all_checks_pass_approves(self):
        payment = {"status": "failed", "amount": 4999.0, "failure_code": "temporary_bank_error"}
        res = PolicyEngine.evaluate(
            payment=payment,
            proposed_action="retry",
            recovery_probability=0.89,
            scorer_confidence=0.91,
            previous_recovery_attempts=0,
        )
        assert res.decision == PolicyDecision.APPROVE
        assert res.action == "retry"
        assert PolicyReasonCode.POLICY_APPROVED in res.reason_codes
        assert len(res.checks) == 10
        assert all(c.passed for c in res.checks)


class TestPolicyBoundariesAndCombinations:
    """Test exact threshold boundaries and combination priority override rules."""

    def test_probability_boundary_0_59_vs_0_60(self):
        payment = {"status": "failed", "amount": 1000.0}

        # 0.59 -> Escalate
        res_low = PolicyEngine.evaluate(
            payment, proposed_action="retry", recovery_probability=0.59, scorer_confidence=0.80, prob_threshold=0.60
        )
        assert res_low.decision == PolicyDecision.ESCALATE

        # 0.60 -> Approve
        res_exact = PolicyEngine.evaluate(
            payment, proposed_action="retry", recovery_probability=0.60, scorer_confidence=0.80, prob_threshold=0.60
        )
        assert res_exact.decision == PolicyDecision.APPROVE

    def test_confidence_boundary_0_69_vs_0_70(self):
        payment = {"status": "failed", "amount": 1000.0}

        # 0.69 -> Escalate
        res_low = PolicyEngine.evaluate(
            payment, proposed_action="retry", recovery_probability=0.80, scorer_confidence=0.69, conf_threshold=0.70
        )
        assert res_low.decision == PolicyDecision.ESCALATE

        # 0.70 -> Approve
        res_exact = PolicyEngine.evaluate(
            payment, proposed_action="retry", recovery_probability=0.80, scorer_confidence=0.70, conf_threshold=0.70
        )
        assert res_exact.decision == PolicyDecision.APPROVE

    def test_amount_boundary_50000_vs_50000_01(self):
        # ₹50,000.00 -> Approve
        p_50k = {"status": "failed", "amount": 50000.00}
        res_50k = PolicyEngine.evaluate(
            p_50k, proposed_action="retry", recovery_probability=0.85, scorer_confidence=0.85, amount_limit=50000.0
        )
        assert res_50k.decision == PolicyDecision.APPROVE

        # ₹50,000.01 -> Escalate
        p_50k_plus = {"status": "failed", "amount": 50000.01}
        res_50k_plus = PolicyEngine.evaluate(
            p_50k_plus, proposed_action="retry", recovery_probability=0.85, scorer_confidence=0.85, amount_limit=50000.0
        )
        assert res_50k_plus.decision == PolicyDecision.ESCALATE

    def test_retry_count_boundary_1_vs_2(self):
        payment = {"status": "failed", "amount": 1000.0}

        # 1 attempt -> Approve
        res_1 = PolicyEngine.evaluate(
            payment, proposed_action="retry", recovery_probability=0.85, scorer_confidence=0.85, previous_recovery_attempts=1, max_retries=2
        )
        assert res_1.decision == PolicyDecision.APPROVE

        # 2 attempts -> Escalate
        res_2 = PolicyEngine.evaluate(
            payment, proposed_action="retry", recovery_probability=0.85, scorer_confidence=0.85, previous_recovery_attempts=2, max_retries=2
        )
        assert res_2.decision == PolicyDecision.ESCALATE

    def test_hard_safety_stops_override_favorable_ai_signals(self):
        """Hard safety rules (fraud, opt-out, paid) MUST override high probability and confidence."""
        # Risk flag + 99% probability -> STOP
        p_risk = {"status": "failed", "amount": 1000.0, "risk_flagged": True}
        res_risk = PolicyEngine.evaluate(p_risk, proposed_action="retry", recovery_probability=0.99, scorer_confidence=0.99)
        assert res_risk.decision == PolicyDecision.STOP

        # Opt-out + 99% probability -> STOP
        p_opt = {"status": "failed", "amount": 1000.0}
        c_opt = {"opted_out": True}
        res_opt = PolicyEngine.evaluate(p_opt, customer=c_opt, proposed_action="retry", recovery_probability=0.99, scorer_confidence=0.99)
        assert res_opt.decision == PolicyDecision.STOP

    def test_action_types_approval(self):
        payment = {"status": "failed", "amount": 2000.0}

        # retry
        assert PolicyEngine.evaluate(payment, proposed_action="retry", recovery_probability=0.85, scorer_confidence=0.85).decision == PolicyDecision.APPROVE
        # message
        assert PolicyEngine.evaluate(payment, proposed_action="message", recovery_probability=0.85, scorer_confidence=0.85).decision == PolicyDecision.APPROVE
        # escalate
        assert PolicyEngine.evaluate(payment, proposed_action="escalate", recovery_probability=0.85, scorer_confidence=0.85).decision == PolicyDecision.APPROVE
        # stop
        assert PolicyEngine.evaluate(payment, proposed_action="stop", recovery_probability=0.85, scorer_confidence=0.85).decision == PolicyDecision.APPROVE


class TestPolicyApiEndpoint:
    """Test POST /api/policy/evaluate endpoint."""

    def test_evaluate_policy_via_api_with_payment_data(self, client):
        payload = {
            "payment_data": {"status": "failed", "amount": 4999.0, "failure_code": "temporary_bank_error"},
            "proposed_action": "retry",
            "recovery_probability": 0.89,
            "scorer_confidence": 0.91,
            "previous_recovery_attempts": 0,
        }
        res = client.post("/api/policy/evaluate", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["decision"] == "APPROVE"
        assert data["action"] == "retry"
        assert len(data["checks"]) == 10

    def test_evaluate_policy_via_api_with_payment_id(self, client):
        payload = {
            "payment_id": 1,
            "proposed_action": "retry",
            "recovery_probability": 0.89,
            "scorer_confidence": 0.91,
        }
        res = client.post("/api/policy/evaluate", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["decision"] == "APPROVE"
