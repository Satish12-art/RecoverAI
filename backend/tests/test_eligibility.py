"""Unit tests for RecoverAI Eligibility Gate Service."""

import pytest
from app.services.eligibility import (
    EligibilityGate,
    EligibilityDecision,
    EligibilityReason,
)


class TestEligibilityGate:
    """Test deterministic eligibility gate rules."""

    def test_already_successful_payment_stopped(self):
        payment = {"status": "paid", "amount": 1000.0, "risk_flagged": False}
        res = EligibilityGate.evaluate(payment=payment)

        assert res.eligible is False
        assert res.decision == EligibilityDecision.STOP
        assert res.reason == EligibilityReason.ALREADY_SUCCESSFUL

    def test_captured_payment_stopped(self):
        payment = {"status": "captured", "amount": 2500.0}
        res = EligibilityGate.evaluate(payment=payment)

        assert res.eligible is False
        assert res.decision == EligibilityDecision.STOP
        assert res.reason == EligibilityReason.ALREADY_SUCCESSFUL

    def test_risk_flagged_payment_stopped(self):
        payment = {"status": "failed", "amount": 5000.0, "risk_flagged": True}
        res = EligibilityGate.evaluate(payment=payment)

        assert res.eligible is False
        assert res.decision == EligibilityDecision.STOP
        assert res.reason == EligibilityReason.RISK_FLAGGED

    def test_risk_failure_code_stopped(self):
        payment = {"status": "failed", "amount": 5000.0, "failure_code": "risk_flagged"}
        res = EligibilityGate.evaluate(payment=payment)

        assert res.eligible is False
        assert res.decision == EligibilityDecision.STOP
        assert res.reason == EligibilityReason.RISK_FLAGGED

    def test_opted_out_customer_stopped(self):
        payment = {"status": "failed", "amount": 3000.0, "failure_code": "temporary_bank_error"}
        customer = {"opted_out": True, "name": "Opted Out User"}
        res = EligibilityGate.evaluate(payment=payment, customer=customer)

        assert res.eligible is False
        assert res.decision == EligibilityDecision.STOP
        assert res.reason == EligibilityReason.CUSTOMER_OPTED_OUT

    def test_duplicate_event_ignored(self):
        payment = {"status": "failed", "amount": 2000.0, "failure_code": "network_error"}
        res = EligibilityGate.evaluate(payment=payment, is_duplicate=True)

        assert res.eligible is False
        assert res.decision == EligibilityDecision.IGNORE
        assert res.reason == EligibilityReason.DUPLICATE_EVENT

    def test_invalid_payment_state_stopped(self):
        payment = {"status": "refunded_cancelled", "amount": 1000.0}
        res = EligibilityGate.evaluate(payment=payment)

        assert res.eligible is False
        assert res.decision == EligibilityDecision.STOP
        assert res.reason == EligibilityReason.INVALID_PAYMENT_STATE

    def test_eligible_failed_payment_proceeds(self):
        payment = {
            "status": "failed",
            "amount": 4999.0,
            "failure_code": "temporary_bank_error",
            "risk_flagged": False,
        }
        customer = {"opted_out": False, "name": "Rahul Sharma"}
        res = EligibilityGate.evaluate(payment=payment, customer=customer)

        assert res.eligible is True
        assert res.decision == EligibilityDecision.PROCEED
        assert res.reason == EligibilityReason.ELIGIBLE

    def test_missing_customer_still_evaluates_payment_safely(self):
        payment = {
            "status": "failed",
            "amount": 2500.0,
            "failure_code": "insufficient_funds",
            "risk_flagged": False,
        }
        res = EligibilityGate.evaluate(payment=payment, customer=None)

        assert res.eligible is True
        assert res.decision == EligibilityDecision.PROCEED
