"""Unit tests for RecoverAI Deterministic Recovery Scorer."""

import pytest
from app.services.recovery_scorer import RecoveryScorer, RecoveryScore


class TestRecoveryScorer:
    """Test deterministic scoring, confidence, factors, and Expected Recovery Value."""

    def test_score_ranges_and_constraints(self):
        payment = {"amount": 4999.0, "failure_code": "temporary_bank_error", "payment_method": "upi"}
        customer = {
            "successful_payments": 15,
            "failed_payments": 1,
            "chargeback_count": 0,
            "customer_tenure_days": 300,
        }
        score = RecoveryScorer.calculate_score(payment, customer)

        assert 0.0 <= score.recovery_probability <= 1.0
        assert 0.0 <= score.scorer_confidence <= 1.0
        assert score.expected_recovery_value >= 0.0
        assert len(score.factors) > 0
        expected_calc = round(4999.0 * score.recovery_probability, 2)
        assert abs(score.expected_recovery_value - expected_calc) <= 0.01

    def test_probability_and_confidence_are_independent(self):
        # Case A: Rich history -> high confidence
        payment_a = {"amount": 2000.0, "failure_code": "insufficient_funds", "payment_method": "upi"}
        customer_a = {"successful_payments": 25, "failed_payments": 1, "customer_tenure_days": 500}
        score_a = RecoveryScorer.calculate_score(payment_a, customer_a)

        # Case B: Very little history -> low confidence, but same failure type
        payment_b = {"amount": 2000.0, "failure_code": "insufficient_funds", "payment_method": "upi"}
        customer_b = {"successful_payments": 0, "failed_payments": 1, "customer_tenure_days": 5}
        score_b = RecoveryScorer.calculate_score(payment_b, customer_b)

        assert score_a.scorer_confidence > score_b.scorer_confidence
        assert score_b.recovery_probability != score_b.scorer_confidence
        # Case A confidence reflects history richness (~1.0), whereas probability is lower (~0.60)
        assert score_a.scorer_confidence != score_a.recovery_probability

    def test_risk_flagged_scores_zero(self):
        payment = {"amount": 5000.0, "risk_flagged": True, "failure_code": "risk_flagged"}
        score = RecoveryScorer.calculate_score(payment)

        assert score.recovery_probability == 0.0
        assert score.expected_recovery_value == 0.0
        assert score.scorer_confidence >= 0.90
        assert any(f.feature == "risk_flagged" for f in score.factors)

    def test_opted_out_customer_scores_zero(self):
        payment = {"amount": 3500.0, "failure_code": "temporary_bank_error"}
        customer = {"opted_out": True}
        score = RecoveryScorer.calculate_score(payment, customer)

        assert score.recovery_probability == 0.0
        assert score.expected_recovery_value == 0.0

    def test_determinism_for_identical_input(self):
        payment = {"amount": 8999.0, "failure_code": "expired_card", "payment_method": "card"}
        customer = {"successful_payments": 10, "failed_payments": 2, "customer_tenure_days": 180}

        score1 = RecoveryScorer.calculate_score(payment, customer)
        score2 = RecoveryScorer.calculate_score(payment, customer)

        assert score1.recovery_probability == score2.recovery_probability
        assert score1.scorer_confidence == score2.scorer_confidence
        assert score1.expected_recovery_value == score2.expected_recovery_value

    def test_context_sensitivity(self):
        """Proof that different customer contexts change the recovery probability."""
        payment = {"amount": 5000.0, "failure_code": "insufficient_funds"}

        # Good customer
        good_cust = {"successful_payments": 20, "failed_payments": 1, "chargeback_count": 0, "customer_tenure_days": 300}
        # Poor customer with chargebacks
        poor_cust = {"successful_payments": 2, "failed_payments": 5, "chargeback_count": 2, "customer_tenure_days": 20}

        good_score = RecoveryScorer.calculate_score(payment, good_cust)
        poor_score = RecoveryScorer.calculate_score(payment, poor_cust)

        assert good_score.recovery_probability > poor_score.recovery_probability

    def test_amount_edge_cases(self):
        # ₹0 amount
        score_zero = RecoveryScorer.calculate_score({"amount": 0.0, "failure_code": "network_error"})
        assert score_zero.expected_recovery_value == 0.0

        # ₹50,000 boundary
        score_50k = RecoveryScorer.calculate_score({"amount": 50000.0, "failure_code": "temporary_bank_error"})
        assert score_50k.expected_recovery_value == round(50000.0 * score_50k.recovery_probability, 2)

        # ₹50,000.01 boundary (triggers high amount penalty)
        score_50k_plus = RecoveryScorer.calculate_score({"amount": 50000.01, "failure_code": "temporary_bank_error"})
        assert score_50k_plus.recovery_probability <= score_50k.recovery_probability

    def test_previous_recovery_attempts_penalty(self):
        payment = {"amount": 2000.0, "failure_code": "temporary_bank_error"}
        cust = {"successful_payments": 10, "failed_payments": 0}

        score_0 = RecoveryScorer.calculate_score(payment, cust, previous_recovery_attempts=0)
        score_1 = RecoveryScorer.calculate_score(payment, cust, previous_recovery_attempts=1)
        score_2 = RecoveryScorer.calculate_score(payment, cust, previous_recovery_attempts=2)

        assert score_0.recovery_probability > score_1.recovery_probability > score_2.recovery_probability
